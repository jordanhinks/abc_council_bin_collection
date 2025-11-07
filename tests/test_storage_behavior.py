import pytest
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

    date = "2025-12-01"
    await storage.store_event(date, "Domestic Collections")
    await storage.store_event(date, "Domestic Collections")

    # ensure only one entry persisted
    await storage.load_data()
    assert date in storage.data
    assert storage.data[date].count("Domestic Collections") == 1


@pytest.mark.asyncio
async def test_clear_data():
    hass = SimpleNamespace()
    storage = BinCollectionStorage(hass)
    fake = FakeStore()
    storage.store = fake

    await storage.store_event("2025-12-01", "Domestic Collections")
    await storage.clear_data()
    await storage.load_data()
    assert storage.data == {}
