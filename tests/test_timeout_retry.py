import asyncio
import pytest
from types import SimpleNamespace

from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator


class FakeResponse:
    def __init__(self, text, status=200):
        self._text = text
        self.status = status

    async def text(self):
        return self._text

    def raise_for_status(self):
        if self.status >= 400:
            raise Exception("HTTP Error")


class FailOnceSession:
    def __init__(self, succeed_text):
        self._calls = 0
        self._succeed_text = succeed_text

    async def get(self, url):
        self._calls += 1
        if self._calls == 1:
            # Simulate network error on first attempt
            raise Exception("network error")
        return FakeResponse(self._succeed_text)


class AlwaysFailSession:
    async def get(self, url):
        raise Exception("permanent failure")


@pytest.mark.asyncio
async def test_retry_succeeds(monkeypatch):
    # Build a minimal coordinator instance without full HA context
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    async def fake_executor(func, arg):
        # run the CPU-bound parser synchronously but return via awaitable
        return func(arg)

    coord.hass = SimpleNamespace(async_add_executor_job=fake_executor)
    coord.address = "12345"
    coord.url = "http://example.invalid"
    coord.create_calendar_events = False
    coord.calendar_entity = ""
    coord.event_summaries = {}
    async def _async_load():
        return {}

    coord.storage = SimpleNamespace(load_data=_async_load)

    # Monkeypatch the HTTP session getter to return a session that fails once
    # Create a single session instance so the first call fails and the second succeeds
    session = FailOnceSession("<html></html>")
    monkeypatch.setattr(
        'custom_components.abc_council_bin_collection.coordinator.async_get_clientsession',
        lambda hass: session
    )

    # Should not raise and should return a parsed result (empty html -> default entries)
    result = await coord._async_update_data()
    assert isinstance(result, dict)
    assert "Domestic Collections" in result


@pytest.mark.asyncio
async def test_retry_exhausts(monkeypatch):
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    async def fake_executor(func, arg):
        return func(arg)

    coord.hass = SimpleNamespace(async_add_executor_job=fake_executor)
    coord.address = "12345"
    coord.url = "http://example.invalid"
    coord.create_calendar_events = False
    coord.calendar_entity = ""
    coord.event_summaries = {}
    async def _async_load():
        return {}

    coord.storage = SimpleNamespace(load_data=_async_load)

    monkeypatch.setattr(
        'custom_components.abc_council_bin_collection.coordinator.async_get_clientsession',
        lambda hass: AlwaysFailSession()
    )

    result = await coord._async_update_data()
    assert result == {}
