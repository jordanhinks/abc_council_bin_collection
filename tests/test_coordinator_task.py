import asyncio
import pytest
from types import SimpleNamespace
from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator


class FakeResponse:
    def __init__(self, text):
        self._text = text

    async def text(self):
        return self._text

    def raise_for_status(self):
        return None


class DummySession:
    async def get(self, url):
        return FakeResponse('<div></div>')


@pytest.mark.asyncio
async def test_background_event_task_cancellation(monkeypatch):
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    # Provide hass with async_create_task and a stub for async_add_executor_job
    hass = SimpleNamespace()
    hass.async_create_task = lambda coro: asyncio.create_task(coro)
    async def fake_executor(func, arg):
        return func(arg)
    hass.async_add_executor_job = fake_executor
    coord.hass = hass
    coord.address = "123"
    coord.url = "http://example.invalid"
    coord.create_calendar_events = True
    coord.calendar_entity = "calendar.home"
    coord.event_summaries = {"Domestic Collections": "Domestic"}

    # Provide storage with store and methods
    class FakeStore:
        def __init__(self):
            self._data = None
        async def async_load(self):
            return {"events": {}}
        async def async_save(self, data):
            self._data = data

    from custom_components.abc_council_bin_collection.storage import BinCollectionStorage
    storage = BinCollectionStorage(hass)
    storage.store = FakeStore()
    coord.storage = storage

    # Patch session getter
    monkeypatch.setattr('custom_components.abc_council_bin_collection.coordinator.async_get_clientsession', lambda hass: DummySession())

    # Trigger update which schedules background task
    data = await coord._async_update_data()
    # There should be a task scheduled
    assert coord._events_task is not None

    # Now call async_stop and ensure cancellation completes
    await coord.async_stop()
    assert coord._events_task is None
