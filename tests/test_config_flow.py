import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from custom_components.abc_council_bin_collection.config_flow import BinCollectionConfigFlow

class MockResponse:
    def raise_for_status(self):
        pass

class MockFailedResponse:
    def raise_for_status(self):
        raise Exception("HTTP Error or Timeout")

class MockSession:
    async def get(self, url):
        return MockResponse()

class MockFailedSession:
    async def get(self, url):
        return MockFailedResponse()

@pytest.mark.asyncio
async def test_step_user_success(monkeypatch):
    flow = BinCollectionConfigFlow()
    flow.hass = SimpleNamespace()
    
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockSession()
    )
    
    # Mock the return value of async_create_entry to avoid executing HA core internals
    flow.async_create_entry = MagicMock(return_value={
        "type": "create_entry", 
        "title": "ABC Council Bin Collection", 
        "data": {"address": "12345"}
    })
    
    result = await flow.async_step_user({"user_address": "12345"})
    
    assert result["type"] == "create_entry"
    assert result["data"]["address"] == "12345"
    flow.async_create_entry.assert_called_once()


@pytest.mark.asyncio
async def test_step_user_cannot_connect(monkeypatch):
    flow = BinCollectionConfigFlow()
    flow.hass = SimpleNamespace()
    
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockFailedSession()
    )
    
    # Mock async_show_form to avoid HA core dependencies
    flow.async_show_form = MagicMock(return_value={
        "type": "form", 
        "errors": {"base": "cannot_connect"}
    })
    
    result = await flow.async_step_user({"user_address": "12345"})
    
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"
    flow.async_show_form.assert_called_once()
