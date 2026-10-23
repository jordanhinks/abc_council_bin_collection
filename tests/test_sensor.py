import pytest
from unittest.mock import MagicMock
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.abc_council_bin_collection.sensor import BinCollectionSensor
from custom_components.abc_council_bin_collection.const import DOMAIN

def test_sensor_inherits_coordinator_entity():
    """Verify that the sensor uses the Platinum standard CoordinatorEntity."""
    mock_coordinator = MagicMock()
    mock_coordinator.address = "12345"
    mock_coordinator.config_entry = MagicMock(entry_id="entry1")

    sensor = BinCollectionSensor(mock_coordinator, "Domestic Collections")

    # Check inheritance
    assert isinstance(sensor, CoordinatorEntity)

    # Check properties
    assert sensor._attr_unique_id == "entry1_domestic_collections"
    assert sensor._attr_translation_key == "domestic_collections"

def test_sensor_state_when_no_data():
    """Test the sensor handles missing data correctly."""
    mock_coordinator = MagicMock()
    mock_coordinator.address = "12345"
    mock_coordinator.data = {}  # Empty data
    
    sensor = BinCollectionSensor(mock_coordinator, "Recycling Collections")
    assert sensor.state is None

def test_sensor_state_with_valid_data():
    """Test the sensor returns the next valid collection date."""
    mock_coordinator = MagicMock()
    mock_coordinator.address = "12345"
    mock_coordinator.data = {
        "Recycling Collections": ["2026-10-15", "2026-10-29"]
    }
    
    sensor = BinCollectionSensor(mock_coordinator, "Recycling Collections")
    assert sensor.state == "2026-10-15"
    assert sensor.extra_state_attributes["all_dates"] == ["2026-10-15", "2026-10-29"]

@pytest.mark.asyncio
async def test_async_setup_entry():
    from custom_components.abc_council_bin_collection.sensor import async_setup_entry
    mock_hass = MagicMock()
    mock_coordinator = MagicMock()
    mock_entry = MagicMock(entry_id="entry_id_123")
    mock_hass.data = {DOMAIN: {"entry_id_123": mock_coordinator}}
    
    add_entities_mock = MagicMock()
    
    await async_setup_entry(mock_hass, mock_entry, add_entities_mock)
    
    add_entities_mock.assert_called_once()
    sensors = add_entities_mock.call_args[0][0]
    assert len(sensors) > 0
    assert sensors[0]._sensor_name in ["Domestic Collections", "Recycling Collections", "Garden/Food Collections"]

def test_sensor_state_no_collection():
    """Test the sensor state when dates list is empty or 'No collection scheduled'."""
    mock_coordinator = MagicMock()
    mock_coordinator.address = "12345"
    mock_coordinator.config_entry = MagicMock(entry_id="entry1")
    
    # Test with empty dates list
    mock_coordinator.data = {"Recycling Collections": []}
    sensor = BinCollectionSensor(mock_coordinator, "Recycling Collections")
    assert sensor.state is None
    
    # Test with 'No collection scheduled'
    mock_coordinator.data = {"Recycling Collections": ["No collection scheduled"]}
    sensor = BinCollectionSensor(mock_coordinator, "Recycling Collections")
    assert sensor.state is None

def test_sensor_device_info():
    """Test the sensor device info."""
    mock_coordinator = MagicMock()
    mock_coordinator.address = "12345"
    mock_coordinator.config_entry = MagicMock(entry_id="entry_device_1")
    
    sensor = BinCollectionSensor(mock_coordinator, "Recycling Collections")
    info = sensor.device_info
    
    assert info["identifiers"] == {(DOMAIN, "entry_device_1")}
    assert "name" in info
    assert "manufacturer" in info
    assert "model" in info
