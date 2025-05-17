"""
Sensor platform for the ABC Council Bin Collection integration.

This module defines sensor entities that report the next bin collection date 
for a specific bin type. The data is provided by a DataUpdateCoordinator.
"""

import logging

from .const import DOMAIN, DEFAULT_SENSOR_NAMES, DEVICE_NAME, DEVICE_MANUFACTURER, DEVICE_MODEL
from .coordinator import BinCollectionDataUpdateCoordinator
from typing import Any, Dict, List, Optional
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Any) -> None:
    """Setup sensor entities platform"""

    coordinator: BinCollectionDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    sensors: List[BinCollectionSensor] = []
    
    # Create a sensor for each default sensor name
    for sensor_name in DEFAULT_SENSOR_NAMES:
        sensors.append(BinCollectionSensor(coordinator, sensor_name))
    
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("Sensors for ABC Council Bin Collection successfully registered")

class BinCollectionSensor(SensorEntity):
    """Sensor representing the bin collection dates for each bin type"""

    def __init__(self, coordinator: BinCollectionDataUpdateCoordinator, sensor_name: str) -> None:
        """
        Initialise the sensor

        Args:
            coordinator (BinCollectionDataUpdateCoordinator): Coordinator instance.
            sensor_name (str): The name of the sensor (bin type).
        """

        self.coordinator = coordinator
        self._sensor_name = sensor_name

        # Normalize the sensor name so that it is user friendly.
        normalized_name = sensor_name if sensor_name.endswith(" Collections") else f"{sensor_name} Collection"
        self._attr_name = normalized_name
        self._attr_unique_id = f"{coordinator.address}_{slugify(normalized_name)}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_state = "unknown"

    async def async_added_to_hass(self) -> None:
        """Register for coordinator updates"""

        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def state(self) -> str:
        """
        Return sensor state

        Retrieves the next bin collection date for this sensor type.
        If no date is available, returns a default message.
        """

        if not self.coordinator.data:
            _LOGGER.warning(
                "Sensor %s could not retrieve data – coordinator data is missing or not updated.", self._sensor_name)
            return "unavailable" #translation
        dates: List[str] = self.coordinator.data.get(self._sensor_name, [])
        return dates[0] if dates else "No collection scheduled" #translation

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """
        Return additional attributes including all collection dates

        These attributes can be used to display historical data or debugging info.
        """

        return {"all_dates": self.coordinator.data.get(self._sensor_name, [])}

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """
        Return device info for the sensor for grouping in the device registry

        This helps Home Assistant to know that this sensor is part of the bin collection integration.
        """
        
        return {
            "identifiers": {(DOMAIN, self.coordinator.address)},
            "name": DEVICE_NAME,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }
