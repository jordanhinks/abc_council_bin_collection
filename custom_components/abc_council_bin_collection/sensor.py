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
    """
    Sets up the sensor entities platform for the Bin Collection integration.

    Retrieves the shared DataUpdateCoordinator, and creates a `BinCollectionSensor`
    entity for each default bin type defined in `DEFAULT_SENSOR_NAMES`.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant core object.
    config_entry : ConfigEntry
        The configuration entry object for the integration.
    async_add_entities : AddEntitiesCallback
        Callback function to add new entities to Home Assistant.
    """

    coordinator: BinCollectionDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    sensors: List[BinCollectionSensor] = []
    
    # Create a sensor for each default sensor name
    for sensor_name in DEFAULT_SENSOR_NAMES:
        sensors.append(BinCollectionSensor(coordinator, sensor_name))
    
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("Sensors for ABC Council Bin Collection successfully registered")

class BinCollectionSensor(SensorEntity):
    """
    Represents a sensor entity that reports the next collection date 
    for a specific bin type (e.g., 'Recycling').

    The sensor state uses the `TIMESTAMP` device class, reporting the next 
    scheduled collection date.
    """

    def __init__(self, coordinator: BinCollectionDataUpdateCoordinator, sensor_name: str) -> None:
        """
        Initializes the Bin Collection Sensor entity.

        The unique ID and display name are generated based on the coordinator's address 
        and the provided sensor name (bin type).

        Parameters
        ----------
        coordinator : BinCollectionDataUpdateCoordinator
            The coordinator instance managing data fetching and updates.
        sensor_name : str
            The internal name used to look up the bin type in the coordinator's data.
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
        """
        Registers the entity for updates when it is added to Home Assistant.

        Registers a listener that calls `async_write_ha_state` whenever the 
        coordinator successfully updates its data, ensuring the sensor reflects 
        the latest collection date.

        Returns
        -------
        None
        """

        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def state(self) -> str:
        """
        Returns the primary state of the sensor.

        The state is the **next scheduled collection date** (the first item)
        found for this sensor's bin type in the coordinator's data. If no 
        date is available, it returns "No collection scheduled" or 
        "unavailable" if the coordinator data is missing.
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
        Returns additional attributes for the sensor.

        Includes the full list of all parsed collection dates for this bin type 
        under the key 'all_dates'.
        """

        return {"all_dates": self.coordinator.data.get(self._sensor_name, [])}

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """
        Returns device information to link this sensor entity to the primary 
        integration device in Home Assistant's device registry.
        """
        
        return {
            "identifiers": {(DOMAIN, self.coordinator.address)},
            "name": DEVICE_NAME,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }
