"""Tests for button.py"""
from unittest.mock import AsyncMock, MagicMock
import pytest

from custom_components.abc_council_bin_collection.const import DOMAIN, DEVICE_NAME
from custom_components.abc_council_bin_collection.button import async_setup_entry, ClearBinEventsButton

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    return entry

@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_config_entry):
    mock_coordinator = MagicMock()
    mock_coordinator.storage = MagicMock()
    mock_coordinator.address = "12345"
    mock_hass.data[DOMAIN][mock_config_entry.entry_id] = mock_coordinator
    
    mock_async_add_entities = MagicMock()
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    mock_async_add_entities.assert_called_once()
    entities = mock_async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], ClearBinEventsButton)
    assert entities[0]._storage == mock_coordinator.storage
    assert entities[0]._entry_id == "test_entry_id"
    assert entities[0]._address == "12345"

@pytest.mark.asyncio
async def test_async_setup_entry_no_coordinator(mock_hass, mock_config_entry):
    mock_async_add_entities = MagicMock()
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    mock_async_add_entities.assert_not_called()

def test_button_properties():
    mock_storage = MagicMock()
    button = ClearBinEventsButton(mock_storage, "test_entry_id", "12345")
    
    assert button.device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert button.device_info["name"] == DEVICE_NAME

@pytest.mark.asyncio
async def test_button_async_press_success():
    mock_storage = MagicMock()
    mock_storage.clear_data = AsyncMock()
    
    button = ClearBinEventsButton(mock_storage, "test_entry_id", "12345")
    await button.async_press()
    
    mock_storage.clear_data.assert_called_once()

@pytest.mark.asyncio
async def test_button_async_press_oserror():
    mock_storage = MagicMock()
    mock_storage.clear_data = AsyncMock(side_effect=OSError("Test error"))
    
    button = ClearBinEventsButton(mock_storage, "test_entry_id", "12345")
    await button.async_press()
    
    mock_storage.clear_data.assert_called_once()
