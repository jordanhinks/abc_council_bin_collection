"""
Manages the persistent storage of created calendar events for the 
Bin Collection integration using Home Assistant's storage helper.

Events are stored as a mapping from date strings to a list of event summaries 
for that specific date.
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
        """
        Initializes the storage manager.

        Sets up the Home Assistant storage object with version 1 and the key 
        "bin_collection_events", and initializes the internal data cache.

        Parameters
        ----------
        hass : HomeAssistant
            The Home Assistant core object instance.
        """

        self.store = storage.Store(hass, 1, "bin_collection_events")
        
        # Storing events as a mapping from date strings to a list of event summaries
        self.data: Dict[str, List[str]] = {}

    # async def load_data(self) -> None:
    async def load_data(self) -> Dict[str, List[str]]:
        """
        Asynchronously loads stored event data from disk, performs schema migration, 
        and cleans up outdated entries.

        Data is loaded, and any event date older than 
        `EVENT_CLEANUP_THRESHOLD_DAYS` is pruned before the cleaned data is 
        re-saved and returned.

        Returns
        -------
        Dict[str, List[str]]
            A copy of the dictionary containing the stored events (date -> list of summaries).
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
        Asynchronously persists the current in-memory event data (`self.data`) 
        to Home Assistant's permanent storage.

        The data is saved wrapped under the "events" key.

        Returns
        -------
        None
        """

        _LOGGER.debug("Saving bin collection data to storage: %s", self.data)
        # Save under an "events" key to preserve potential previous schema
        await self.store.async_save({"events": self.data})

    def is_event_stored(self, date: str, summary: str) -> bool:
        """
        Determines if a specific event (date and summary combination) is 
        already present in the in-memory cache.

        Parameters
        ----------
        date : str
            The date string of the event (YYYY-MM-DD).
        summary : str
            The event summary, usually representing the bin type.

        Returns
        -------
        bool
            True if the event is stored, False otherwise.
        """

        stored_events: Any = self.data.get(date, [])

        return isinstance(stored_events, list) and summary in stored_events

    async def update_events(self, events: Dict[str, List[str]]) -> None:
        """
        Replaces the entire in-memory events cache with the provided mapping 
        and immediately saves the new state to persistent storage.

        Parameters
        ----------
        events : Dict[str, List[str]]
            The complete, new set of bin collection events to store.

        Returns
        -------
        None
        """
        
        # Ensure we store copies
        self.data = {k: list(v) for k, v in events.items()}
        # Clean up and persist
        # Reuse save_data which will wrap under 'events' key
        await self.save_data()

    async def store_event(self, date: str, summary: str) -> None:
        """
        Asynchronously records a new, unique event entry (date/summary pair) 
        into the in-memory cache and persists the updated cache to disk.

        If a list of events does not exist for the given date, one is created. 
        Duplicate summaries for the same date are prevented.

        Parameters
        ----------
        date : str
            The date string for the collection event (YYYY-MM-DD).
        summary : str
            The unique summary/bin type to record for that date.

        Returns
        -------
        None
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
        """
        Clears all stored bin collection event data from both the in-memory 
        cache and persistent storage.

        Returns
        -------
        None
        """
        
        if not self.data:
            _LOGGER.debug("Attempted to clear bin events, but no data was found!")

            return

        _LOGGER.debug("Stored bin collection data before clearing: %s", self.data)
        self.data.clear()
        await self.save_data()
        _LOGGER.debug("Stored bin collection data after clearing: %s", self.data)