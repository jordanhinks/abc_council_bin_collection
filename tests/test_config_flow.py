import pytest
import aiohttp
from unittest.mock import patch, MagicMock, AsyncMock
from types import SimpleNamespace

from custom_components.abc_council_bin_collection.config_flow import BinCollectionConfigFlow, BinCollectionOptionsFlowHandler

class MockResponse:
    def raise_for_status(self):
        pass

class MockFailedResponse:
    def raise_for_status(self):
        raise aiohttp.ClientError("HTTP Error")

class MockSession:
    async def get(self, url):
        return MockResponse()

class MockFailedSession:
    async def get(self, url):
        return MockFailedResponse()

@pytest.fixture
def mock_flow():
    flow = BinCollectionConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"entry_id": "entry_1"}
    
    # Mock core HA ConfigFlow methods
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry", "title": "ABC", "data": {}})
    flow.async_show_form = MagicMock(return_value={"type": "form", "errors": {}})
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort", "reason": "reconfigure_successful"})
    flow.async_abort = MagicMock(return_value={"type": "abort", "reason": "already_configured"})
    
    return flow

@pytest.mark.asyncio
async def test_step_user_success(monkeypatch, mock_flow):
    """Test successful initial setup flow."""
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockSession()
    )
    
    result = await mock_flow.async_step_user({"user_address": "12345"})
    
    mock_flow.async_set_unique_id.assert_called_once_with("12345")
    mock_flow._abort_if_unique_id_configured.assert_called_once()
    mock_flow.async_create_entry.assert_called_once()
    
    assert result["type"] == "create_entry"

@pytest.mark.asyncio
async def test_step_user_cannot_connect(monkeypatch, mock_flow):
    """Test initial setup fails cleanly with a connection error."""
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockFailedSession()
    )
    
    result = await mock_flow.async_step_user({"user_address": "12345"})
    
    # Ensure it returns the form again with the cannot_connect error
    args, kwargs = mock_flow.async_show_form.call_args
    assert "cannot_connect" in kwargs.get("errors", {}).values()
    mock_flow.async_set_unique_id.assert_not_called()

@pytest.mark.asyncio
async def test_step_reconfigure_success(monkeypatch, mock_flow):
    """Test a successful reconfiguration where the address doesn't collide."""
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockSession()
    )
    
    # Mock the existing entry that is being reconfigured
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_1"
    mock_entry.data = {"address": "old_address"}
    mock_flow.hass.config_entries.async_get_entry.return_value = mock_entry
    
    # Mock active entries (no collisions, only this entry exists)
    mock_flow._async_current_entries = MagicMock(return_value=[mock_entry])
    
    result = await mock_flow.async_step_reconfigure({"user_address": "67890"})
    
    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    
    # Verify we updated both the data AND the unique_id in the registry
    mock_flow.async_update_reload_and_abort.assert_called_once_with(
        mock_entry,
        unique_id="67890",
        data={"address": "67890"},
        reason="reconfigure_successful",
    )

@pytest.mark.asyncio
async def test_step_reconfigure_duplicate(monkeypatch, mock_flow):
    """Test reconfiguration aborts if changing to an address owned by another service."""
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockSession()
    )
    
    # Mock the entry we are trying to reconfigure (entry_1)
    mock_entry_1 = MagicMock()
    mock_entry_1.entry_id = "entry_1"
    mock_entry_1.data = {"address": "12345"}
    mock_entry_1.unique_id = "12345"
    mock_flow.hass.config_entries.async_get_entry.return_value = mock_entry_1
    
    # Mock another entry that already owns the target address (entry_2)
    mock_entry_2 = MagicMock()
    mock_entry_2.entry_id = "entry_2"
    mock_entry_2.unique_id = "67890"
    
    # Both entries exist in Home Assistant
    mock_flow._async_current_entries = MagicMock(return_value=[mock_entry_1, mock_entry_2])
    
    # Attempt to reconfigure entry_1 to "67890" (which entry_2 owns)
    result = await mock_flow.async_step_reconfigure({"user_address": "67890"})
    
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    
    # Ensure it aborted natively and did NOT update the config entry
    mock_flow.async_abort.assert_called_once_with(reason="already_configured")
    mock_flow.async_update_reload_and_abort.assert_not_called()

def test_sanitize_address_exception():
    flow = BinCollectionConfigFlow()
    # Mocking urlparse to throw ValueError
    with patch("custom_components.abc_council_bin_collection.config_flow.urlparse", side_effect=ValueError("Test Error")):
        # Providing a valid URL structure so it enters the try block
        result = flow._sanitize_address("http://test.com")
        assert result == ""

@pytest.mark.asyncio
async def test_options_flow_init_form():
    mock_entry = MagicMock()
    mock_entry.options = {}
    handler = BinCollectionConfigFlow.async_get_options_flow(mock_entry)
    
    handler.async_show_form = MagicMock(return_value={"type": "form"})
    result = await handler.async_step_init()
    
    assert result["type"] == "form"
    handler.async_show_form.assert_called_once()

@pytest.mark.asyncio
async def test_options_flow_init_create():
    mock_entry = MagicMock()
    mock_entry.options = {}
    handler = BinCollectionConfigFlow.async_get_options_flow(mock_entry)
    
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    
    user_input = {
        "update_interval": 24,
        "create_calendar_events": True,
        "calendar_entity": "test_calendar"
    }
    
    result = await handler.async_step_init(user_input)
    
    assert result["type"] == "create_entry"
    assert user_input["calendar_entity"] == "calendar.test_calendar"
    handler.async_create_entry.assert_called_once_with(title="", data=user_input)

@pytest.mark.asyncio
async def test_step_user_invalid_address(mock_flow):
    """Test user setup with invalid address."""
    result = await mock_flow.async_step_user({"user_address": "invalid"})
    args, kwargs = mock_flow.async_show_form.call_args
    assert "invalid_address" in kwargs.get("errors", {}).values()

@pytest.mark.asyncio
async def test_step_reconfigure_invalid_address(mock_flow):
    """Test reconfigure with invalid address."""
    mock_entry = MagicMock()
    mock_entry.data = {"address": "old_address"}
    mock_flow.hass.config_entries.async_get_entry.return_value = mock_entry
    result = await mock_flow.async_step_reconfigure({"user_address": "invalid"})
    args, kwargs = mock_flow.async_show_form.call_args
    assert "invalid_address" in kwargs.get("errors", {}).values()

@pytest.mark.asyncio
async def test_step_reconfigure_cannot_connect(monkeypatch, mock_flow):
    """Test reconfigure fails with connection error."""
    monkeypatch.setattr(
        "custom_components.abc_council_bin_collection.config_flow.async_get_clientsession",
        lambda hass: MockFailedSession()
    )
    mock_entry = MagicMock()
    mock_entry.data = {"address": "old_address"}
    mock_flow.hass.config_entries.async_get_entry.return_value = mock_entry
    result = await mock_flow.async_step_reconfigure({"user_address": "12345"})
    args, kwargs = mock_flow.async_show_form.call_args
    assert "cannot_connect" in kwargs.get("errors", {}).values()

@pytest.mark.asyncio
async def test_step_reconfigure_form(mock_flow):
    """Test reconfigure form generation without user input."""
    mock_entry = MagicMock()
    mock_entry.data = {"address": "old_address"}
    mock_flow.hass.config_entries.async_get_entry.return_value = mock_entry
    result = await mock_flow.async_step_reconfigure(None)
    assert result["type"] == "form"

def test_sanitize_address_valid_url():
    """Test sanitize address with a valid URL."""
    flow = BinCollectionConfigFlow()
    result = flow._sanitize_address("http://example.com/?address=12345")
    assert result == "12345"
    result = flow._sanitize_address("http://example.com/?address=")
    assert result == ""
    result = flow._sanitize_address("http://example.com/")
    assert result == ""

@pytest.mark.asyncio
async def test_options_flow_init_no_calendar_entity():
    """Test options flow without calendar_entity."""
    mock_entry = MagicMock()
    mock_entry.options = {}
    handler = BinCollectionConfigFlow.async_get_options_flow(mock_entry)
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    user_input = {
        "update_interval": 24,
        "create_calendar_events": False
    }
    result = await handler.async_step_init(user_input)
    assert result["type"] == "create_entry"

@pytest.mark.asyncio
async def test_options_flow_init_with_calendar_prefix():
    """Test options flow when calendar_entity already has prefix."""
    mock_entry = MagicMock()
    mock_entry.options = {}
    handler = BinCollectionConfigFlow.async_get_options_flow(mock_entry)
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    user_input = {
        "update_interval": 24,
        "create_calendar_events": True,
        "calendar_entity": "calendar.test_calendar"
    }
    result = await handler.async_step_init(user_input)
    assert result["type"] == "create_entry"
    assert user_input["calendar_entity"] == "calendar.test_calendar"

