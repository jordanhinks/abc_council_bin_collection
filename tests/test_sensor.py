import pytest
from unittest.mock import MagicMock
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.abc_council_bin_collection.sensor import BinCollectionSensor
from custom_components.abc_council_bin_collection.const import DOMAIN

def test_sensor_inherits_coordinator_entity():
    """Verify that the sensor uses the Platinum standard CoordinatorEntity."""
    mock_coordinator = MagicMock()
    mock_coordinator.address = "12345"
    
    sensor = BinCollectionSensor(mock_coordinator, "Domestic Collections")
    
    # Check inheritance
    assert isinstance(sensor, CoordinatorEntity)
    
    # Check properties
    assert sensor._attr_unique_id == "12345_domestic_collection"
    assert sensor._attr_name == "Domestic Collections"

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
