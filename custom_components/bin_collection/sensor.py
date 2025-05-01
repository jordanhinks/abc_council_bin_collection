import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_SENSOR_NAMES
from .coordinator import BinCollectionDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform for Bin Collection integration."""
    coordinator: BinCollectionDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    sensors = []
    # Create a sensor for each default sensor name.
    for sensor_name in DEFAULT_SENSOR_NAMES:
        sensors.append(BinCollectionSensor(coordinator, sensor_name))
    async_add_entities(sensors, True)

class BinCollectionSensor(SensorEntity):
    """Sensor representing bin collection dates for a specific bin type."""

    def __init__(self, coordinator: BinCollectionDataUpdateCoordinator, sensor_name: str):
        self.coordinator = coordinator
        self._sensor_name = sensor_name
        self._attr_name = f"{sensor_name} Collection"
        self._attr_unique_id = f"{coordinator.address}_{sensor_name.replace(' ', '_')}"
        self._attr_state = "Unknown"

    async def async_added_to_hass(self):
        """Register for coordinator updates."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def state(self):
        """Return the next bin collection date for this sensor."""
        dates = self.coordinator.data.get(self._sensor_name, [])
        if dates:
            return dates[0]
        return "No Date"

    @property
    def extra_state_attributes(self):
        """Return additional attributes with all dates."""
        return {"all_dates": self.coordinator.data.get(self._sensor_name, [])}
