"""
Coordinator platform for the ABC Council Bin Collection integration.

This fetches and parsing data, and creates the calendar events.
"""

from __future__ import annotations

import logging
import asyncio
import re

from .const import EVENT_CREATION_DELAY, EVENT_CREATION_TIMEOUT
from .storage import BinCollectionStorage
from datetime import datetime, timedelta
from typing import Any, Dict, List
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Define types for clarity.
BIN_TYPES: Dict[str, str] = {
    "bg-black": "Domestic Collections",
    "bg-green": "Recycling Collections",
    "bg-brown": "Garden/Food Collections",
}

# Require Python 3.11+; use stdlib asyncio.timeout for timeouts (no external dependency)

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
    # Group 1: The date (DD/MM/YYYY)
    DATE_EXTRACT_PATTERN = re.compile(
        r'<h4><i class="fa fa-calendar".*?></i>\s*(\d{2}/\d{2}/\d{4})\s*</h4>',
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
    ) -> None:
        """
        Initialise the coordinator
        """
        self.hass = hass
        self.address = address
        self.url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={self.address}"
        self.create_calendar_events = create_calendar_events
        self.calendar_entity = calendar_entity
        self.event_summaries = event_summaries

        # Initialize persistent storage
        self.storage: BinCollectionStorage = BinCollectionStorage(hass)

        # Background task handle for calendar event creation
        self._events_task: asyncio.Task | None = None

        super().__init__(hass, _LOGGER, name="Bin Collection Data", update_interval=update_interval)

    async def _async_update_data(self) -> Dict[str, List[str]]:
        """
        Fetch HTML data from the remote URL, process and parse bin collection dates,
        and create calendar events (if enabled)
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
            except Exception as err:
                _LOGGER.error("Error fetching data (attempt %d): %s", attempt + 1, err)
                if attempt == 2:
                    return {}

        data = await self.hass.async_add_executor_job(self._parse_html, html)

        # Create calendar events if enabled — schedule as a background task so
        # coordinator refreshes are not blocked and cancellation is manageable.
        if self.create_calendar_events:
            if not self.calendar_entity:
                _LOGGER.error("Calendar event creation is enabled but calendar_entity is empty. Skipping event creation.")
            else:
                _LOGGER.info("Scheduling background calendar event creation (delay %s seconds)...", EVENT_CREATION_DELAY)
                # Schedule the background runner; store the Task so it can be cancelled later
                try:
                    self._events_task = self.hass.async_create_task(self._run_create_events_task(data))
                except Exception:
                    # Fallback in environments where async_create_task returns None or is not present
                    task = asyncio.create_task(self._run_create_events_task(data))
                    self._events_task = task

        return data if data else {}

    def _parse_html(self, html: str) -> Dict[str, List[str]]:
        """
        Parse the HTML content to extract bin collection dates using a two-stage RegEx process.

        Args:
            html: The HTML content as a string.

        Returns:
            A dictionary with keys as bin collection types and values as lists of dates (in ISO format).
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
                date_text = date_match.group(1).strip()
                
                try:
                    date_obj = datetime.strptime(date_text, "%d/%m/%Y")

                    # Format to ISO 8601 (YYYY-MM-DD)
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                    dates_list.append(formatted_date)
                except ValueError:
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
        """Load persistent bin collection events into memory"""
        loaded = await self.storage.load_data()
        # loaded is a copy of stored events
        _LOGGER.debug("Loaded stored events: %s", loaded)

    async def _run_create_events_task(self, data: Dict[str, List[str]]) -> None:
        """
        Background runner that delays then creates calendar events.
        Keeps `self._events_task` populated while running and clears it on exit.
        """
        try:
            await asyncio.sleep(EVENT_CREATION_DELAY)
            await self._create_calendar_events(data)
        except asyncio.CancelledError:
            _LOGGER.debug("Background calendar event creation task was cancelled")
            raise
        except Exception as ex:
            _LOGGER.error("Background calendar event creation failed: %s", ex)
        finally:
            # Clear the stored task handle so callers can see it finished
            try:
                self._events_task = None
            except Exception:
                pass

    async def _create_calendar_events(self, data: Dict[str, List[str]]) -> None:
        """
        Create calendar events based on parsed data. Only creates events if they are not persistently stored.
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
                except Exception as ex:
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
                except Exception as ex:
                    _LOGGER.error("Failed to create calendar event for %s: %s", date, ex)

    async def async_stop(self) -> None:
        """
        Stop the coordinator and cancel any background event creation task.
        """
        # Cancel background events task if running
        if getattr(self, "_events_task", None):
            try:
                self._events_task.cancel()
            except Exception:
                pass

            try:
                await self._events_task
            except asyncio.CancelledError:
                _LOGGER.debug("Background events task cancelled during async_stop")
            except Exception as ex:
                _LOGGER.debug("Error awaiting background events task during async_stop: %s", ex)

            # Ensure it's cleared
            try:
                self._events_task = None
            except Exception:
                pass

        # Call base class stop if available
        parent_stop = getattr(super(), "async_stop", None)
        if callable(parent_stop):
            res = parent_stop()
            if asyncio.iscoroutine(res):
                await res