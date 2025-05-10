from .const import EVENT_CREATION_DELAY
import asyncio
from datetime import datetime, timedelta
import logging
import async_timeout
from bs4 import BeautifulSoup
from .storage import BinCollectionStorage

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

        # Set up persistent storage
        self.storage = BinCollectionStorage(hass)
        self.stored_events = {}  # Cached stored events

        super().__init__(hass, _LOGGER, name="Bin Collection Data", update_interval=update_interval)

    async def _async_update_data(self):
        """Fetch HTML data, parse it, and, if configured, create calendar events."""
        await self.load_stored_events()  # Load stored events before creating new ones

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
                _LOGGER.error("Calendar event creation is enabled but calendar_entity is empty. Skipping event creation.")
            else:
                _LOGGER.info("Delaying calendar event creation by %s seconds...", EVENT_CREATION_DELAY)
                await asyncio.sleep(EVENT_CREATION_DELAY)
                await self._create_calendar_events(data)

        return data

    async def load_stored_events(self):
        """Load existing stored events into memory."""
        stored_data = await self.storage.load_data()
        if stored_data is not None:
            self.stored_events = stored_data

    async def _create_calendar_events(self, data):
        """Create calendar events only if they aren't already stored."""
        for bin_type, dates in data.items():
            for date in dates:
                if date in self.stored_events:
                    _LOGGER.info(f"Skipping event creation for {date} as it's already stored.")
                    continue  # Prevent duplicate event creation

                event_data = {
                    "entity_id": self.calendar_entity,
                    "summary": bin_type,
                    "start_date": date,
                    "end_date": date
                }

                await self.hass.services.async_call("calendar", "create_event", event_data)
                _LOGGER.info(f"Created event '{bin_type}' for {date}")

                # Store event persistently to prevent future duplicates
                self.stored_events[date] = bin_type
                await self.storage.save_data()
