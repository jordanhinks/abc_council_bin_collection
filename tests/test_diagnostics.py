"""Tests for diagnostics.py"""
from unittest.mock import MagicMock, patch
import pytest

from custom_components.abc_council_bin_collection.const import DOMAIN
from custom_components.abc_council_bin_collection.diagnostics import async_get_config_entry_diagnostics, TO_REDACT

@pytest.fixture
def mock_hass():
    return MagicMock()

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.as_dict.return_value = {"data": {"address": "12345"}, "unique_id": "12345"}
    return entry

@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics(mock_hass, mock_config_entry):
    mock_coordinator = MagicMock()
    mock_coordinator.data = {"test": "data"}
    mock_coordinator.update_interval = "12:00:00"
    mock_coordinator.create_calendar_events = True
    mock_coordinator.calendar_entity = "calendar.test"
    mock_coordinator.event_summaries = {"Domestic Collections": "Bin"}
    
    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    
    with patch("custom_components.abc_council_bin_collection.diagnostics.async_redact_data") as mock_redact:
        mock_redact.return_value = {"data": {"address": "***"}, "unique_id": "***"}
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        mock_redact.assert_called_once_with(mock_config_entry.as_dict(), TO_REDACT)
        
        assert result["config_entry"] == {"data": {"address": "***"}, "unique_id": "***"}
        assert result["coordinator_data"] == {"test": "data"}
        assert result["options_state"]["update_interval"] == "12:00:00"
        assert result["options_state"]["create_calendar_events"] is True
        assert result["options_state"]["calendar_entity"] == "calendar.test"
        assert result["options_state"]["event_summaries"] == {"Domestic Collections": "Bin"}
