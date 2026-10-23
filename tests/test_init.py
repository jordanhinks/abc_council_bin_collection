"""Tests for __init__.py"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import timedelta

from custom_components.abc_council_bin_collection.const import DOMAIN
from custom_components.abc_council_bin_collection import (
    async_setup_entry,
    async_reload_entry,
    async_unload_entry,
    async_remove_entry,
)

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {"address": "12345"}
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()
    return entry

@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_config_entry):
    with patch("custom_components.abc_council_bin_collection.BinCollectionDataUpdateCoordinator") as mock_coordinator_cls:
        mock_coordinator = mock_coordinator_cls.return_value
        mock_coordinator.load_stored_events = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        
        result = await async_setup_entry(mock_hass, mock_config_entry)
        
        assert result is True
        assert mock_hass.data[DOMAIN][mock_config_entry.entry_id] == mock_coordinator
        mock_coordinator.load_stored_events.assert_called_once()
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(mock_config_entry, ["sensor", "button"])
        mock_config_entry.async_on_unload.assert_called_once()

@pytest.mark.asyncio
async def test_async_setup_entry_missing_address(mock_hass, mock_config_entry):
    mock_config_entry.data = {}
    result = await async_setup_entry(mock_hass, mock_config_entry)
    assert result is False

@pytest.mark.asyncio
async def test_async_setup_entry_coordinator_exception(mock_hass, mock_config_entry):
    with patch("custom_components.abc_council_bin_collection.BinCollectionDataUpdateCoordinator") as mock_coordinator_cls:
        mock_coordinator = mock_coordinator_cls.return_value
        mock_coordinator.load_stored_events = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(side_effect=Exception("Test Error"))
        
        with pytest.raises(Exception, match="Test Error"):
            await async_setup_entry(mock_hass, mock_config_entry)

@pytest.mark.asyncio
async def test_async_reload_entry(mock_hass, mock_config_entry):
    mock_coordinator = MagicMock()
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    
    mock_config_entry.options = {
        "update_interval": 12,
        "create_calendar_events": True,
        "calendar_entity": "calendar.test",
        "summary_domestic": "Dom",
    }
    
    await async_reload_entry(mock_hass, mock_config_entry)
    
    assert mock_coordinator.address == "12345"
    assert mock_coordinator.url == "https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address=12345"
    assert mock_coordinator.update_interval == timedelta(hours=12)
    assert mock_coordinator.create_calendar_events is True
    assert mock_coordinator.calendar_entity == "calendar.test"
    assert mock_coordinator.event_summaries["Domestic Collections"] == "Dom"
    
    mock_coordinator.async_request_refresh.assert_called_once()

@pytest.mark.asyncio
async def test_async_reload_entry_no_coordinator(mock_hass, mock_config_entry):
    # Should not raise exception
    from custom_components.abc_council_bin_collection.const import DOMAIN
    mock_hass.data = {DOMAIN: {}}
    await async_reload_entry(mock_hass, mock_config_entry)

@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    result = await async_unload_entry(mock_hass, mock_config_entry)
    assert result is True
    mock_hass.config_entries.async_unload_platforms.assert_called_once_with(mock_config_entry, ["sensor", "button"])

@pytest.mark.asyncio
async def test_async_unload_entry_failed(mock_hass, mock_config_entry):
    mock_hass.config_entries.async_unload_platforms.return_value = False
    result = await async_unload_entry(mock_hass, mock_config_entry)
    assert result is False

@pytest.mark.asyncio
async def test_async_remove_entry_success(mock_hass, mock_config_entry):
    mock_coordinator = MagicMock()
    mock_coordinator.storage = MagicMock()
    mock_coordinator.storage.clear_data = AsyncMock()
    
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    
    await async_remove_entry(mock_hass, mock_config_entry)
    
    mock_coordinator.storage.clear_data.assert_called_once()
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_remove_entry_oserror(mock_hass, mock_config_entry):
    mock_coordinator = MagicMock()
    mock_coordinator.storage = MagicMock()
    mock_coordinator.storage.clear_data = AsyncMock(side_effect=OSError("Test error"))
    
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    
    await async_remove_entry(mock_hass, mock_config_entry)
    
    mock_coordinator.storage.clear_data.assert_called_once()
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_remove_entry_no_coordinator_or_storage(mock_hass, mock_config_entry):
    mock_hass.data[DOMAIN] = {}
    await async_remove_entry(mock_hass, mock_config_entry)
    
    mock_coordinator = MagicMock()
    del mock_coordinator.storage
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    await async_remove_entry(mock_hass, mock_config_entry)
