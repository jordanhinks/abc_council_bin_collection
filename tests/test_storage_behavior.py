import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from custom_components.abc_council_bin_collection.storage import BinCollectionStorage


class FakeStore:
    def __init__(self):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.mark.asyncio
async def test_store_event_idempotent():
    hass = SimpleNamespace()
    storage = BinCollectionStorage(hass)
    fake = FakeStore()
    storage.store = fake

    # Use a future date so it doesn't get cleaned up by load_data()
    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
    await storage.store_event(future_date, "Domestic Collections")
    await storage.store_event(future_date, "Domestic Collections")

    # ensure only one entry persisted
    await storage.load_data()
    assert future_date in storage.data
    assert storage.data[future_date].count("Domestic Collections") == 1


@pytest.mark.asyncio
async def test_clear_data():
    hass = SimpleNamespace()
    storage = BinCollectionStorage(hass)
    fake = FakeStore()
    storage.store = fake

    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
    await storage.store_event(future_date, "Domestic Collections")
    await storage.clear_data()
    await storage.load_data()
    assert storage.data == {}
