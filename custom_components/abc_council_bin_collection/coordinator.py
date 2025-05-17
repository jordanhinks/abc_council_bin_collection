from __future__ import annotations

import logging
import asyncio
import async_timeout

from .const import EVENT_CREATION_DELAY, EVENT_CREATION_TIMEOUT
from .storage import BinCollectionStorage
from datetime import datetime, timedelta
from typing import Any, Dict, List
from bs4 import BeautifulSoup
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

class BinCollectionDataUpdateCoordinator(DataUpdateCoordinator):
    """
    Manages fetching bin collection data and optionally creates calendar events

    This coordinator is responsible for:
      - Fetching and parsing HTML data from the bin collection website
      - Managing persistent storage through BinCollectionStorage
      - Creating calendar events if enabled
    """

    # DEBUG only - used for reducing calendar create event calls to avoid 403 errors
    # VALID_DATES: set[str] = {"2025-05-20", "2025-05-27"}  # List of allowed dates

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

        Args:
            hass: Home Assistant instance.
            address: The bin collection address (numeric).
            update_interval: Update interval as a timedelta object.
            create_calendar_events: Whether to create calendar events.
            calendar_entity: The entity ID of the target calendar.
            event_summaries: A mapping of bin types to event summary names.
        """
        self.hass = hass
        self.address = address
        self.url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={self.address}"
        self.create_calendar_events = create_calendar_events
        self.calendar_entity = calendar_entity
        self.event_summaries = event_summaries

        # Initialize persistent storage.
        self.storage: BinCollectionStorage = BinCollectionStorage(hass)

        super().__init__(hass, _LOGGER, name="Bin Collection Data", update_interval=update_interval)

    # DEBUG only - used for reducing calendar create event calls to avoid 403 errors
    # def should_create_event(self, date_str: str) -> bool:
    #     """Return True if provided date equals dates in VALID_DATES"""
    #     return date_str in self.VALID_DATES

    async def _async_update_data(self) -> Dict[str, List[str]]:
        """
        Fetch HTML data from the remote URL, process and parse bin collection dates,
        and create calendar events (if enabled)

        Returns:
            A dictionary mapping collection types to lists of dates
        """

        await self.load_stored_events()

        html: str = ""
        # Tries 3 times before failure
        for attempt in range(3):
            try:
                async with async_timeout.timeout(EVENT_CREATION_DELAY):
                    session = async_get_clientsession(self.hass)
                    response = await session.get(self.url)
                    response.raise_for_status()
                    html = await response.text()
                break
            except Exception as err:
                _LOGGER.error("Error fetching data (attempt %d): %s", attempt + 1, err)
                if attempt == 2:
                    # Returning empty dict ensures we always return a dict
                    return {}

        data = await self.hass.async_add_executor_job(self._parse_html, html)

        # Create calendar events if enabled
        if self.create_calendar_events:
            if not self.calendar_entity:
                _LOGGER.error("Calendar event creation is enabled but calendar_entity is empty. Skipping event creation.")
            else:
                _LOGGER.info("Delaying calendar event creation by %s seconds...", EVENT_CREATION_DELAY)
                await asyncio.sleep(EVENT_CREATION_DELAY)
                await self._create_calendar_events(data)

        return data if data else {}

    def _parse_html(self, html: str) -> Dict[str, List[str]]:
        """
        Parse the HTML content to extract bin collection dates.

        Args:
            html: The HTML content as a string.

        Returns:
            A dictionary with keys as bin collection types and values as lists of dates (in ISO format).
        """

        result: Dict[str, List[str]] = {}
        soup = BeautifulSoup(html, "html.parser")

        for class_name, default_title in BIN_TYPES.items():
            target_divs = soup.find_all("div", class_=class_name)
            dates_list: List[str] = []

            for target_div in target_divs:
                sibling_div = target_div.find_parent().find_next_sibling("div")
                if sibling_div:
                    for h4 in sibling_div.find_all("h4"):
                        date_text = h4.text.strip()
                        try:
                            date_obj = datetime.strptime(date_text, "%d/%m/%Y")
                            formatted_date = date_obj.strftime("%Y-%m-%d")  # ISO format
                            dates_list.append(formatted_date)
                        except ValueError:
                            _LOGGER.warning("Skipping invalid date format: %s", date_text)
                else:
                    _LOGGER.warning("No sibling div found for bin type '%s'.", default_title)

            result[default_title] = dates_list if dates_list else ["No collection scheduled"]

        return result

    async def load_stored_events(self) -> None:
        """Load persistent bin collection events into memory"""
        await self.storage.load_data()
        # Optionally log loaded events for debugging:
        _LOGGER.debug("Loaded stored events: %s", self.storage.data)

    async def _create_calendar_events(self, data: Dict[str, List[str]]) -> None:
        """
        Create calendar events based on parsed data. Only creates events if they are not persistently stored.

        Args:
            data: A dictionary mapping bin types to lists of dates.
        """

        for bin_type, dates in data.items():
            # Use user-defined summary if available.
            summary_name = self.event_summaries.get(bin_type, bin_type)

            for date in dates:
                # DEBUG only - used for reducing calendar create event calls to avoid 403 errors
                # Only allow creation for allowed dates.
                # if not self.should_create_event(date):
                #     continue

                if date in self.storage.data and bin_type in self.storage.data[date]:
                    _LOGGER.info("Skipping event creation for %s on %s — already stored.", summary_name, date)
                    continue

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
