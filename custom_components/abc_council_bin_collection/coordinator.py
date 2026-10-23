"""
Coordinator platform for the ABC Council Bin Collection integration.

This fetches and parsing data, and creates the calendar events.
"""

from __future__ import annotations

import logging
import asyncio
import re
import aiohttp

from dateutil.parser import parse, ParserError
from .const import DOMAIN, EVENT_CREATION_DELAY, EVENT_CREATION_TIMEOUT
from .storage import BinCollectionStorage
from datetime import datetime, timedelta
from typing import Any, Dict, List
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.issue_registry import async_create_issue, async_delete_issue, IssueSeverity
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound

from homeassistant.config_entries import ConfigEntry

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Define types for clarity.
BIN_TYPES: Dict[str, str] = {
    "bg-black": "Domestic Collections",
    "bg-green": "Recycling Collections",
    "bg-brown": "Garden/Food Collections",
}

class BinCollectionDataUpdateCoordinator(DataUpdateCoordinator):
    
    BIN_COLLECTION_BLOCK_PATTERN = re.compile(
        # Match the start of the heading div and capture the class name
        r'<div class="heading (bg-black|bg-green|bg-brown)">.*?</div>\s*<hr>\s*</div>\s*'
        # Match the div that contains the date entries
        r'<div class="col-sm-12 col-md-9">\s*'
        # Capture the entire HTML block containing the date <h4> tags (Group 2)
        r'(.*?)'
        # Non-greedy match for everything up to the next image/divider block
        r'</div>\s*<div class="col-sm-12 col-md-3">',
        re.DOTALL
    )
    
    # Pre-compile the simpler pattern for finding dates within the captured block (Group 2).
    # Group 1: The extracted date string (may contain HTML/spaces)
    DATE_EXTRACT_PATTERN = re.compile(
        r'<h4><i class="fa fa-calendar".*?></i>(.*?)</h4>',
        re.DOTALL
    )

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        update_interval: timedelta,
        create_calendar_events: bool,
        calendar_entity: str,
        event_summaries: Dict[str, str],
        config_entry: ConfigEntry | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Bin Collection Data coordinator.

        Parameters
        ----------
        hass : HomeAssistant
            The Home Assistant instance.
        address : str
            The address used to look up the bin collection schedule.
        update_interval : timedelta
            The frequency at which to update the bin collection data.
        create_calendar_events : bool
            Flag to enable or disable the creation of calendar events.
        calendar_entity : str
            The entity ID of the calendar to use for events.
        event_summaries : Dict[str, str]
            A dictionary mapping bin types to their corresponding calendar event summaries.
        config_entry : ConfigEntry | None
            The configuration entry for this integration.
        """

        self.hass = hass
        self.address = address
        self.url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={self.address}"
        self.create_calendar_events = create_calendar_events
        self.calendar_entity = calendar_entity
        self.event_summaries = event_summaries

        self._base_update_interval = update_interval
        self._consecutive_parse_failures = 0

        # Initialize persistent storage
        self.storage: BinCollectionStorage = BinCollectionStorage(hass)

        # Background task handle for calendar event creation
        self._events_task: asyncio.Task | None = None

        # Determine kwargs for DataUpdateCoordinator to support Home Assistant quality scale
        super_kwargs = {"name": "Bin Collection Data", "update_interval": update_interval}
        if config_entry:
            super_kwargs["config_entry"] = config_entry

        super().__init__(hass, _LOGGER, **super_kwargs)

    async def _async_update_data(self) -> Dict[str, List[str]]:
        """
        Asynchronously fetches and processes bin collection data from a remote URL.

        The function attempts to retrieve the HTML data up to 3 times. It then parses 
        the collection dates and creates calendar events if that feature is enabled.

        Returns
        -------
        Dict[str, List[str]]
            A dictionary containing the parsed bin collection data. Returns an empty 
            dictionary ({}) if the data fetch fails after all retries.
        """

        await self.load_stored_events()

        html: str = ""
        # Tries 3 times before failure
        for attempt in range(3):
            try:
                async with asyncio.timeout(EVENT_CREATION_DELAY):
                    session = async_get_clientsession(self.hass)
                    response = await session.get(self.url)
                    response.raise_for_status()
                    html = await response.text()
                break
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.error("Error fetching data (attempt %d): %s", attempt + 1, err)
                if attempt == 2:
                    raise UpdateFailed(f"Error communicating with API: {err}") from err

        data = await self.hass.async_add_executor_job(self._parse_html, html)

        # Check if the parsed data actually contains any scheduled dates
        has_dates = any(
            any(date_str != "No collection scheduled" for date_str in dates)
            for dates in data.values()
        )

        if not has_dates:
            self._consecutive_parse_failures = getattr(self, "_consecutive_parse_failures", 0) + 1
            if self._consecutive_parse_failures >= 3:
                async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"parse_failure_{self.address}",
                    is_fixable=False,
                    severity=IssueSeverity.ERROR,
                    translation_key="parse_failure",
                    translation_placeholders={
                        "github_url": "https://github.com/jordanhinks/abc_council_bin_collection/issues"
                    },
                )
        else:
            if getattr(self, "_consecutive_parse_failures", 0) > 0:
                self._consecutive_parse_failures = 0
                async_delete_issue(self.hass, DOMAIN, f"parse_failure_{self.address}")

            # Smart Interval Calculation
            today = datetime.now().date()
            future_dates = []
            for dates in data.values():
                for date_str in dates:
                    if date_str != "No collection scheduled":
                        try:
                            d = datetime.strptime(date_str, "%Y-%m-%d").date()
                            if d >= today:
                                future_dates.append(d)
                        except ValueError:
                            pass
            
            if future_dates:
                next_collection = min(future_dates)
                # Poll the day after the next collection to get the new dates
                days_until_poll = (next_collection - today).days + 1
                
                # Minimum interval of 12 hours to prevent tight loops, capped at the user's base interval
                smart_interval = max(timedelta(hours=12), timedelta(days=days_until_poll))
                base_interval = getattr(self, "_base_update_interval", self.update_interval)
                new_interval = min(smart_interval, base_interval)
                
                if self.update_interval != new_interval:
                    _LOGGER.debug("Smart update interval adjusting to %s (next collection: %s)", new_interval, next_collection)
                    self.update_interval = new_interval
            else:
                base_interval = getattr(self, "_base_update_interval", self.update_interval)
                if self.update_interval != base_interval:
                    _LOGGER.debug("Smart update interval reverting to base %s (no future collections found)", base_interval)
                    self.update_interval = base_interval

        # Create calendar events if enabled — schedule as a background task so
        # coordinator refreshes are not blocked and cancellation is manageable.
        if self.create_calendar_events:
            if not self.calendar_entity:
                _LOGGER.error("Calendar event creation is enabled but calendar_entity is empty. Skipping event creation.")
            else:
                _LOGGER.info("Scheduling background calendar event creation (delay %s seconds)...", EVENT_CREATION_DELAY)
                # Schedule the background runner; store the Task so it can be cancelled later
                coro = self._run_create_events_task(data)
                try:
                    self._events_task = self.hass.async_create_task(coro)
                except (AttributeError, RuntimeError):
                    # Fallback in environments where async_create_task returns None or is not present
                    self._events_task = asyncio.create_task(coro)

        return data if data else {}

    def _parse_html(self, html: str) -> Dict[str, List[str]]:
        """
        Parses the raw HTML content to extract and format bin collection dates.

        The process uses two regular expressions: the first extracts HTML blocks for 
        each bin type, and the second extracts the date strings within those blocks. 
        Dates are validated, converted from DD/MM/YYYY to ISO 8601 (YYYY-MM-DD), and 
        stored. Ensures all known bin types are present in the final result.

        Args:
            html: The raw HTML content string retrieved from the source URL.

        Returns:
            A dictionary where keys are bin type titles (str) and values are lists of 
            formatted collection dates (List[str] in ISO format).
        """

        result: Dict[str, List[str]] = {}
        
        for match in self.BIN_COLLECTION_BLOCK_PATTERN.finditer(html):
            class_name = match.group(1) 
            bin_type_title = BIN_TYPES.get(class_name)
            
            collection_block_html = match.group(2)
            
            if not bin_type_title:
                _LOGGER.warning("Unknown bin type class found: %s", class_name)
                continue
            
            dates_list: List[str] = []
            
            for date_match in self.DATE_EXTRACT_PATTERN.finditer(collection_block_html):
                # Clean up any extra whitespace or newlines in the extracted string
                date_text = re.sub(r'\s+', ' ', date_match.group(1)).strip()
                
                try:
                    now = datetime.now()
                    parsed_date = None

                    # 1. Try explicit ISO format (YYYY-MM-DD) to prevent dateutil dayfirst=True bug
                    iso_match = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', date_text)
                    if iso_match:
                        parsed_date = datetime(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

                    # 2. Try explicit UK format (DD/MM/YYYY or DD-MM-YYYY)
                    if not parsed_date:
                        uk_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', date_text)
                        if uk_match:
                            parsed_date = datetime(int(uk_match.group(3)), int(uk_match.group(2)), int(uk_match.group(1)))

                    # 3. Try explicit short UK format (DD/MM or DD-MM)
                    if not parsed_date:
                        uk_short_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})\b', date_text)
                        if uk_short_match:
                            parsed_date = datetime(now.year, int(uk_short_match.group(2)), int(uk_short_match.group(1)))

                    # 4. Fallback to dateutil for word-based dates (e.g., "4th November")
                    if not parsed_date:
                        parsed_date = parse(date_text, fuzzy=True, default=now, dayfirst=True)

                    # Handle year wrapping logic if the year was omitted and defaulted to the current year
                    if parsed_date.year == now.year:
                        if parsed_date.month == 1 and now.month == 12:
                            parsed_date = parsed_date.replace(year=now.year + 1)
                        elif parsed_date.month == 12 and now.month == 1:
                            parsed_date = parsed_date.replace(year=now.year - 1)

                    # Format to ISO 8601 (YYYY-MM-DD)
                    formatted_date = parsed_date.strftime("%Y-%m-%d")
                    dates_list.append(formatted_date)
                except (ValueError, ParserError):
                    _LOGGER.warning("Skipping invalid date format: %s", date_text)

            # Store the results
            if dates_list:
                result[bin_type_title] = dates_list
            else:
                # Add a default message if no dates were found for a known bin type
                result[bin_type_title] = ["No collection scheduled"]

        # Ensure all expected bin types are in the result, even if no dates were found (which prevents an error later)
        for _, default_title in BIN_TYPES.items():
            if default_title not in result:
                result[default_title] = ["No collection scheduled"]

        return result

    async def load_stored_events(self) -> None:
        """
        Asynchronously loads persistent calendar events from storage into the coordinator's memory.

        A debug log is created showing the data retrieved from storage.

        Returns
        -------
        None
            The method does not return a value but updates the coordinator's state.
        """

        loaded = await self.storage.load_data()
        # loaded is a copy of stored events
        _LOGGER.debug("Loaded stored events: %s", loaded)

    async def _run_create_events_task(self, data: Dict[str, List[str]]) -> None:
        """
        Manages the background task for delayed calendar event creation.

        This method first introduces a delay, then calls the event creation logic. 
        It handles cancellation and general exceptions gracefully. Importantly, it
        manages the `self._events_task` handle, clearing it upon completion or failure 
        to indicate the task is finished.

        Parameters
        ----------
        data : Dict[str, List[str]]
            The parsed bin collection data used to generate the calendar events.

        Returns
        -------
        None
        """

        try:
            await asyncio.sleep(EVENT_CREATION_DELAY)
            await self._create_calendar_events(data)
        except asyncio.CancelledError:
            _LOGGER.debug("Background calendar event creation task was cancelled")
            raise
        except (HomeAssistantError, ServiceNotFound, ValueError, TypeError, OSError) as ex:
            _LOGGER.error("Background calendar event creation failed: %s", ex)
        finally:
            # Clear the stored task handle so callers can see it finished
            self._events_task = None

    async def _create_calendar_events(self, data: Dict[str, List[str]]) -> None:
        """
        Creates single-day calendar events for each collection date found in the parsed data.

        Events are only created if they do not already exist in persistent storage. 
        It uses user-defined summaries (if provided), calls the Home Assistant 
        'calendar.create_event' service, stores the new event persistently, and applies 
        a short timeout between creations. Non-date placeholders are skipped.

        Parameters
        ----------
        data : Dict[str, List[str]]
            A dictionary containing bin types as keys and a list of ISO-formatted 
            collection dates as values.

        Returns
        -------
        None
        """

        for bin_type, dates in data.items():
            # Use user-defined summary if available.
            summary_name = self.event_summaries.get(bin_type, bin_type)

            for date in dates:
                # Skip placeholders or non-date entries that the parser may insert
                if not isinstance(date, str) or date == "No collection scheduled":
                    _LOGGER.debug("Skipping non-date entry for %s: %s", bin_type, date)
                    continue

                # Check via async storage API to avoid accessing internal attributes
                try:
                    already = self.storage.is_event_stored(date, bin_type)
                except (KeyError, TypeError, OSError) as ex:
                    _LOGGER.debug("Error checking stored event existence: %s", ex)
                    already = False

                if already:
                    _LOGGER.info("Skipping event creation for %s on %s — already stored.", summary_name, date)
                    continue

                # At this point we expect 'date' to be an ISO date string (YYYY-MM-DD)
                event_data = {
                    "entity_id": self.calendar_entity,
                    "summary": summary_name,
                    "start_date": date,
                    "end_date": (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "description": "Automatic bin collection event."
                }

                try:
                    await self.hass.services.async_call("calendar", "create_event", event_data)
                    _LOGGER.info("Created event '%s' for %s", summary_name, date)

                    # Store the event to prevent duplicate creation.
                    await self.storage.store_event(date, bin_type)

                    # Timeout till creating next event
                    await asyncio.sleep(EVENT_CREATION_TIMEOUT)
                except (HomeAssistantError, ServiceNotFound, ValueError, OSError) as ex:
                    _LOGGER.error("Failed to create calendar event for %s: %s", date, ex)

    async def async_stop(self) -> None:
        """
        Asynchronously halts the coordinator, ensuring a clean shutdown.

        This method checks for and cancels any currently running background calendar 
        event creation task (`_events_task`). It handles the cancellation and awaiting 
        of the task to prevent resource leaks before clearing the task handle. Finally, 
        it safely calls the base class's `async_stop` method if one exists.

        Returns
        -------
        None
        """
        
        if getattr(self, "_events_task", None):
            self._events_task.cancel()

            try:
                await self._events_task
            except asyncio.CancelledError:
                _LOGGER.debug("Background events task cancelled during async_stop")
            except (HomeAssistantError, ServiceNotFound, ValueError, TypeError, OSError) as ex:
                _LOGGER.debug("Error awaiting background events task during async_stop: %s", ex)

            # Ensure it's cleared
            self._events_task = None

        # Call base class stop if available
        parent_stop = getattr(super(), "async_stop", None)
        if callable(parent_stop):
            res = parent_stop()
            if asyncio.iscoroutine(res):
                await res