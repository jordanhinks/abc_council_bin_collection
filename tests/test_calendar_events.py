import asyncio
import pytest
from types import SimpleNamespace

from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator


class FakeStore:
    def __init__(self):
        self._saved = None

    async def async_load(self):
        return {"events": {}}

    async def async_save(self, data):
        self._saved = data


class FakeCalendarService:
    def __init__(self):
        self.calls = []

    async def async_call(self, domain, service, data):
        self.calls.append((domain, service, data))


@pytest.mark.asyncio
async def test_calendar_event_creation(monkeypatch):
    # Minimal coordinator
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    hass = SimpleNamespace()
    # Provide async_create_task and services
    calendar_service = FakeCalendarService()
    hass.services = SimpleNamespace(async_call=calendar_service.async_call)
    hass.async_create_task = lambda coro: asyncio.create_task(coro)
    coord.hass = hass
    coord.address = "12345"
    coord.url = "http://example.invalid"
    coord.create_calendar_events = True
    coord.calendar_entity = "calendar.home"
    coord.event_summaries = {"Domestic Collections": "Domestic"}

    # Inject storage with fake store
    fake_store = FakeStore()
    from custom_components.abc_council_bin_collection.storage import BinCollectionStorage
    storage = BinCollectionStorage(hass)
    storage.store = fake_store
    coord.storage = storage

    # Prepare data to create events for
    data = {"Domestic Collections": ["2025-01-01"]}

    # Run creation directly (background scheduling is separate)
    await coord._create_calendar_events(data)

    # Ensure the calendar service was called
    assert len(calendar_service.calls) == 1
    domain, service, payload = calendar_service.calls[0]
    assert domain == "calendar"
    assert service == "create_event"
    assert payload["entity_id"] == "calendar.home"
    assert payload["start_date"] == "2025-01-01"

    # Check storage saved the event
    assert fake_store._saved is not None
