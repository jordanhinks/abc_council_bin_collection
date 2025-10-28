"""
Persistent storage module for the ABC Council Bin Collection integration.

Defines BinCollectionStorage class for storing the data persistently across
load, save and manage states.
"""

import logging
import homeassistant.helpers.storage as storage

from .const import EVENT_CLEANUP_THRESHOLD_DAYS
from datetime import datetime, timedelta
from typing import Any, Dict, List
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class BinCollectionStorage:
    def __init__(self, hass: HomeAssistant) -> None:
        self.store = storage.Store(hass, 1, "bin_collection_events")
        
        # Storing events as a mapping from date strings to a list of event summaries
        self.data: Dict[str, List[str]] = {}

    async def load_data(self) -> None:
        """
        Load stored event dates and clean out outdated entries

        Retrieves stored data from Home Assistant's storage and ensures that the data is 
        a valid dictionary. It then calculates a cutoff date based on EVENT_CLEANUP_THRESHOLD_DAYS,
        filtering out any events prior to that date and re-saving the cleaned data.
        """

        stored_data: Any = await self.store.async_load()
        _LOGGER.debug("Retrieved stored bin events from persistent storage: %s", stored_data)

        if stored_data:
            # Ensure stored data is a valid dictionary; if not, reset it
            if not isinstance(stored_data, dict):
                _LOGGER.warning("Invalid storage format detected, resetting data.")
                stored_data = {}

            # If the stored format nests events under an "events" key, use it
            if "events" in stored_data and isinstance(stored_data["events"], dict):
                self.data = stored_data["events"].copy()
            else:
                self.data = stored_data.copy() if isinstance(stored_data, dict) else {}

            # Calculate the cutoff date. Events older than this will be removed
            cutoff_date = (datetime.today() - timedelta(days=EVENT_CLEANUP_THRESHOLD_DAYS)).strftime("%Y-%m-%d")
            # Only keep event entries with keys (dates) more recent than the cutoff
            cleaned_data = {date: events for date, events in self.data.items() if date > cutoff_date}

            self.data = cleaned_data
            await self.save_data()

            _LOGGER.debug("Stored events after cleanup: %s", self.data)
        else:
            _LOGGER.debug("No stored bin collection events found.")

        # Always return a copy of the internal mapping for callers
        return {k: list(v) for k, v in self.data.items()}

    async def save_data(self) -> None:
        """
        Uses Home Assistant's storage helper to save the current state of self.data.
        """

        _LOGGER.debug("Saving bin collection data to storage: %s", self.data)
        # Save under an "events" key to preserve potential previous schema
        await self.store.async_save({"events": self.data})

    def is_event_stored(self, date: str, summary: str) -> bool:
        """
        Determine whether a specific event is already stored
        
        Args:
            date (str): The date of the event.
            summary (str): A brief description of the event (e.g., bin type).

        Returns:
            bool: True if the event is already in storage, False otherwise.
        """

        stored_events: Any = self.data.get(date, [])

        return isinstance(stored_events, list) and summary in stored_events

    async def update_events(self, events: Dict[str, List[str]]) -> None:
        """
        Replace in-memory events with provided mapping and persist.
        """
        # Ensure we store copies
        self.data = {k: list(v) for k, v in events.items()}
        # Clean up and persist
        # Reuse save_data which will wrap under 'events' key
        await self.save_data()

    async def store_event(self, date: str, summary: str) -> None:
        """
        Persist a new event into storage

        Args:
            date (str): The date of the event.
            summary (str): A description of the bin type or event summary.

        If no list exists for a given date, one is created. The summary is then appended
        only if it is not already present.
        """

        _LOGGER.debug("Adding event to storage: %s -> %s", date, summary)

        if not isinstance(self.data.get(date), list):
            # Ensure that the storage for this date is a list
            self.data[date] = []

        if summary not in self.data[date]:
            self.data[date].append(summary)

        await self.save_data()
        _LOGGER.debug("Stored bin collection data after saving: %s", self.data)

    async def clear_data(self) -> None:
        """Clear all stored bin collection events"""
        
        if not self.data:
            _LOGGER.debug("Attempted to clear bin events, but no data was found!")

            return

        _LOGGER.debug("Stored bin collection data before clearing: %s", self.data)
        self.data.clear()
        await self.save_data()
        _LOGGER.debug("Stored bin collection data after clearing: %s", self.data)