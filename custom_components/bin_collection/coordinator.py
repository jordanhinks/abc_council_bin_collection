from .const import EVENT_CREATION_DELAY
import asyncio
from datetime import datetime, timedelta
import logging
import re
import async_timeout
from bs4 import BeautifulSoup

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

BIN_TYPES = {
    "bg-black": "Domestic Collections",
    "bg-green": "Recycling Collections",
    "bg-brown": "Garden/Food Collections",
}

class BinCollectionDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching bin collection data and optionally creates calendar events."""

    def __init__(self, hass, address, update_interval, create_calendar_events, calendar_entity, event_summaries):
        """Initialize the coordinator."""
        self.hass = hass
        self.address = address
        self.url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={self.address}"
        self.create_calendar_events = create_calendar_events
        self.calendar_entity = calendar_entity
        
        self.event_summaries = event_summaries  
        self._created_events = set()
        super().__init__(hass, _LOGGER, name="Bin Collection Data", update_interval=update_interval)

    async def _async_update_data(self):
        """Fetch HTML data, parse it, and, if configured, create calendar events."""
        for attempt in range(3):
            try:
                async with async_timeout.timeout(30):
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

        if self.create_calendar_events:
            if not self.calendar_entity:
                _LOGGER.error("Calendar event creation is enabled but calendar_entity is empty. Skipping calendar event creation.")
            else:
                _LOGGER.info("Delaying calendar event creation by %s seconds...", EVENT_CREATION_DELAY)
                await asyncio.sleep(EVENT_CREATION_DELAY)
                await self._create_calendar_events(data)

        return data

    def _parse_html(self, html):
        """Extract bin collection dates for each bin type from the HTML."""
        result = {}
        soup = BeautifulSoup(html, "html.parser")

        for class_name, default_title in BIN_TYPES.items():
            target_divs = soup.find_all("div", class_=class_name)
            dates_list = []

            for target_div in target_divs:
                sibling_div = target_div.find_parent().find_next_sibling("div")
                if sibling_div:
                    for h4 in sibling_div.find_all("h4"):
                        date_text = h4.text.strip()
                        try:
                            date_obj = datetime.strptime(date_text, "%d/%m/%Y")
                            formatted_date = date_obj.strftime("%Y-%m-%d")  # ISO 8601 format
                            dates_list.append(formatted_date)
                        except ValueError:
                            _LOGGER.warning("Error parsing date: %s", date_text)
                            dates_list.append(f"Error parsing date: {date_text}")
                else:
                    dates_list.append(f"No sibling div found for class '{class_name}'.")
            
            result[default_title] = dates_list

        _LOGGER.debug("Parsed bin collection data: %s", result)
        return result

    async def async_create_event(self):
        """Create an event for May 3, 2025."""
        event_date = date(2025, 5, 3)
        end_date = date(2025, 5, 4)  # Google Calendar requires end date to be the next day

        summary = "Generated Event"

        _LOGGER.info(f"Waiting for calendar.create_event service to become available...")
        
        # Wait until the calendar.create_event service exists (up to 10 seconds)
        for _ in range(10):
            if "calendar.create_event" in self.hass.services.async_services():
                break
            await asyncio.sleep(1)

        if "calendar.create_event" not in self.hass.services.async_services():
            _LOGGER.error("calendar.create_event service is still unavailable, aborting event creation.")
            return

        _LOGGER.info(f"Creating event '{summary}' on {event_date} in {self._calendar_name}")

        event_data = {
            "entity_id": f"calendar.{self._calendar_name}",
            "summary": summary,
            "start_date": event_date,
            "end_date": end_date  # Fix: End date is the next day
        }

        _LOGGER.debug(f"Calling calendar.create_event with: {event_data}")
        await self.hass.services.async_call("calendar", "create_event", event_data)

        _LOGGER.info(f"Event '{summary}' successfully created from {event_date} to {end_date}.")
