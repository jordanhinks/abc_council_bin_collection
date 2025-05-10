import homeassistant.helpers.storage as storage

class BinCollectionStorage:
    """Handles persistent storage for bin collection events."""
    
    def __init__(self, hass):
        self.store = storage.Store(hass, 1, "bin_collection_events")
        self.data = {}

    async def load_data(self):
        """Load stored event dates."""
        stored_data = await self.store.async_load()
        if stored_data is not None:
            self.data = stored_data

    async def save_data(self):
        """Persist stored event dates."""
        await self.store.async_save(self.data)

    def is_event_stored(self, date):
        """Check if an event is already stored."""
        return date in self.data

    async def store_event(self, date, summary):
        """Store a new event date."""
        self.data[date] = summary
        await self.save_data()
