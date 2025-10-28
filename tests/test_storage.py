import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from custom_components.abc_council_bin_collection.storage import BinCollectionStorage
from custom_components.abc_council_bin_collection.const import EVENT_CLEANUP_THRESHOLD_DAYS


class FakeStore:
    def __init__(self):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.mark.asyncio
async def test_load_and_save(tmp_path):
    hass = SimpleNamespace()
    storage = BinCollectionStorage(hass)
    # Inject fake store
    fake = FakeStore()
    storage.store = fake

    # Initially empty
    loaded = await storage.load_data()
    assert loaded == {}

    # Update events and ensure persisted — use recent dates within cleanup window
    today = datetime.now(timezone.utc).date()
    d1 = (today + timedelta(days=1)).isoformat()
    d2 = (today + timedelta(days=5)).isoformat()
    # Use the storage API: store_event expects date -> summary
    await storage.store_event(d1, "Domestic Collections")
    await storage.store_event(d2, "Domestic Collections")

    assert fake._data is not None

    # Load should work and reflect cleaned data: storage maps date -> [summaries]
    await storage.load_data()
    assert d1 in storage.data
    assert d2 in storage.data
    assert "Domestic Collections" in storage.data[d1]


@pytest.mark.asyncio
async def test_cleanup_old_events():
    hass = SimpleNamespace()
    storage = BinCollectionStorage(hass)
    fake = FakeStore()
    storage.store = fake

    old_date = (datetime.now(timezone.utc) - timedelta(days=EVENT_CLEANUP_THRESHOLD_DAYS + 10)).date().isoformat()
    recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()

    # update_events expects date -> [summaries]
    events = {old_date: ["Domestic Collections"], recent_date: ["Domestic Collections"]}
    await storage.update_events(events)

    # Stored data should only contain recent_date after cleanup
    loaded = await storage.load_data()
    assert recent_date in loaded
    assert old_date not in loaded
