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
        self.calendar_entity = calendar_entity  # already normalized in __init__.py
        # event_summaries is used ONLY for calendar event creation.
        self.event_summaries = event_summaries  
        self._created_events = set()
        super().__init__(hass, _LOGGER, name="Bin Collection Data", update_interval=update_interval)

    async def _async_update_data(self):
        """Fetch HTML data, parse it, and, if configured, create calendar events."""
        for attempt in range(3):  # Retry mechanism
            try:
                async with async_timeout.timeout(30):
                    session = async_get_clientsession(self.hass)
                    response = await session.get(self.url)
                    response.raise_for_status()
                    html = await response.text()
                break  # Exit loop on success
            except Exception as err:
                _LOGGER.error("Error fetching data (attempt %d): %s", attempt + 1, err)
                if attempt == 2:
                    return {}  # Return empty data on failure
        
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
                            day_week = date_obj.strftime("%A")
                            dates_list.append(f"{date_text} ({day_week})")
                        except ValueError:
                            _LOGGER.warning("Error parsing date: %s", date_text)
                            dates_list.append(f"Error parsing date: {date_text}")
                else:
                    dates_list.append(f"No sibling div found for class '{class_name}'.")
            # Use the default title from BIN_TYPES as the key.
            result[default_title] = dates_list

        _LOGGER.debug("Parsed bin collection data: %s", result)
        return result

    async def _create_calendar_events(self, data: dict):
        """Create an all-day calendar event for each bin type and date."""
        for bin_type, date_list in data.items():
            for item in date_list:
                match = re.search(r"(\d{2}/\d{2}/\d{4})", item)
                if match:
                    date_str = match.group(1)
                    try:
                        dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    except Exception as ex:
                        _LOGGER.error("Error parsing date %s: %s", date_str, ex)
                        continue
                    
                    iso_start_date = dt.strftime("%Y-%m-%d")
                    iso_end_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
                    event_key = f"{bin_type}-{iso_start_date}"
                    
                    if event_key in self._created_events:
                        _LOGGER.debug("Skipping duplicate event creation for %s", event_key)
                        continue

                    # Use the event_summaries provided via options; fall back to the default bin type if not set.
                    summary_name = self.event_summaries.get(bin_type, bin_type)

                    service_data = {
                        "entity_id": self.calendar_entity,
                        "summary": summary_name,
                        "start_date": iso_start_date,
                        "end_date": iso_end_date,
                        "description": "Automatic bin collection event."
                    }

                    try:
                        await self.hass.services.async_call(
                            "calendar", "create_event", service_data, blocking=True
                        )
                        self._created_events.add(event_key)
                        _LOGGER.info("Created calendar event for: %s", event_key)
                    except Exception as ex:
                        _LOGGER.error("Failed to create calendar event for %s: %s", event_key, ex)
