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

from datetime import datetime, timedelta
import pytest
from homeassistant.components.sensor import SensorDeviceClass
from custom_components.abc_council_bin_collection.sensor import BinCollectionNextSensor, BinCollectionSensor

def test_sensor_days_until_collection():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    today = datetime.now().date()
    future = today + timedelta(days=2)
    mock_coordinator.data = {"Domestic Collections": [future.strftime("%Y-%m-%d")]}
    sensor = BinCollectionSensor(mock_coordinator, "Domestic Collections")
    attrs = sensor.extra_state_attributes
    assert attrs["days_until_collection"] == 2

def test_sensor_invalid_date_format():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    mock_coordinator.data = {"Domestic Collections": ["invalid-date"]}
    sensor = BinCollectionSensor(mock_coordinator, "Domestic Collections")
    attrs = sensor.extra_state_attributes
    assert "days_until_collection" not in attrs

def test_next_sensor_state_and_attrs():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    today = datetime.now().date()
    future1 = today + timedelta(days=2)
    future2 = today + timedelta(days=5)
    
    mock_coordinator.data = {
        "Domestic Collections": [future1.strftime("%Y-%m-%d")],
        "Recycling Collections": [future1.strftime("%Y-%m-%d")],
        "Garden/Food Collections": [future2.strftime("%Y-%m-%d")]
    }
    
    sensor = BinCollectionNextSensor(mock_coordinator)
    
    assert sensor.state == "Domestic, Recycling"
    attrs = sensor.extra_state_attributes
    assert attrs["days_until_collection"] == 2
    assert attrs["collection_date"] == future1.strftime("%Y-%m-%d")
    assert attrs["bin_types"] == ["Domestic", "Recycling"]

def test_next_sensor_no_upcoming():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    mock_coordinator.data = {
        "Domestic Collections": ["No collection scheduled"]
    }
    sensor = BinCollectionNextSensor(mock_coordinator)
    assert sensor.state == "No upcoming collections"
    assert sensor.extra_state_attributes == {}

def test_next_sensor_empty_data():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    mock_coordinator.data = {}
    sensor = BinCollectionNextSensor(mock_coordinator)
    assert sensor.state is None
    assert sensor.extra_state_attributes == {}

def test_next_sensor_invalid_date():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    mock_coordinator.data = {
        "Domestic Collections": ["invalid"]
    }
    sensor = BinCollectionNextSensor(mock_coordinator)
    assert sensor.state == "No upcoming collections"

def test_next_sensor_device_info():
    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "entry_id_1"
    mock_coordinator.address = "123"

    sensor = BinCollectionNextSensor(mock_coordinator)
    assert sensor.device_info["identifiers"] == {("abc_council_bin_collection", "entry_id_1")}
