"""
Sensor platform for the ABC Council Bin Collection integration.

This module defines sensor entities that report the next bin collection date 
for a specific bin type. The data is provided by a DataUpdateCoordinator.
"""

import logging

from datetime import datetime

from .const import DOMAIN, DEFAULT_SENSOR_NAMES, DEVICE_NAME, DEVICE_MANUFACTURER, DEVICE_MODEL
from .coordinator import BinCollectionDataUpdateCoordinator
from typing import Any, Dict, List, Optional
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Any) -> None:
    """
    Sets up the sensor entities platform for the Bin Collection integration.

    Retrieves the shared DataUpdateCoordinator, and creates a `BinCollectionSensor`
    entity for each default bin type defined in `DEFAULT_SENSOR_NAMES`, as well as 
    a meta-sensor for the next upcoming collection.

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
    sensors: List[CoordinatorEntity] = []
    
    # Create a sensor for each default sensor name
    for sensor_name in DEFAULT_SENSOR_NAMES:
        sensors.append(BinCollectionSensor(coordinator, sensor_name))
        
    # Add the "Next Collection" meta-sensor
    sensors.append(BinCollectionNextSensor(coordinator))
    
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("Sensors for ABC Council Bin Collection successfully registered")

class BinCollectionSensor(CoordinatorEntity, SensorEntity):
    """
    Represents a sensor entity that reports the next collection date 
    for a specific bin type (e.g., 'Recycling').

    The sensor state uses the `DATE` device class, reporting the next 
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
        super().__init__(coordinator)
        self._sensor_name = sensor_name

        # Normalize the sensor name so that it is user friendly.
        normalized_name = sensor_name if sensor_name.endswith(" Collections") else f"{sensor_name} Collection"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{slugify(normalized_name)}"
        
        self._attr_has_entity_name = True
        self._attr_translation_key = sensor_name.lower().replace(" ", "_").replace("/", "_")
        self._attr_device_class = SensorDeviceClass.DATE

    @property
    def state(self) -> Optional[str]:
        """
        Returns the primary state of the sensor.

        The state is the **next scheduled collection date** (the first item)
        found for this sensor's bin type in the coordinator's data. If no 
        date is available, it returns None.
        """

        if not self.coordinator.data:
            _LOGGER.warning(
                "Sensor %s could not retrieve data – coordinator data is missing or not updated.", self._sensor_name)
            return None
        dates: List[str] = self.coordinator.data.get(self._sensor_name, [])
        if not dates or dates[0] == "No collection scheduled":
            return None
        return dates[0]

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """
        Returns additional attributes for the sensor.

        Includes the full list of all parsed collection dates for this bin type 
        under the key 'all_dates', and a calculation of 'days_until_collection'.
        """
        dates = self.coordinator.data.get(self._sensor_name, [])
        attrs = {"all_dates": dates}
        
        if dates and dates[0] != "No collection scheduled":
            try:
                collection_date = datetime.strptime(dates[0], "%Y-%m-%d").date()
                today = datetime.now().date()
                days_until = (collection_date - today).days
                attrs["days_until_collection"] = days_until
            except ValueError:
                pass
                
        return attrs

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """
        Returns device information to link this sensor entity to the primary 
        integration device in Home Assistant's device registry.
        """
        
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": DEVICE_NAME,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

class BinCollectionNextSensor(CoordinatorEntity, SensorEntity):
    """
    Represents a meta-sensor entity that reports the next upcoming bin collection,
    regardless of the bin type. 
    
    The state is a string combining all bin types being collected on that nearest date.
    Attributes include the date itself and days_until_collection.
    """

    def __init__(self, coordinator: BinCollectionDataUpdateCoordinator) -> None:
        """Initialize the next collection sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_next_collection"
        self._attr_has_entity_name = True
        self._attr_translation_key = "next_collection"
        self._attr_icon = "mdi:calendar-star"

    @property
    def state(self) -> Optional[str]:
        """
        Returns the primary state of the sensor: the types of bins being collected next.
        """
        if not self.coordinator.data:
            return None
            
        next_date, bins = self._get_next_collection()
        if not bins:
            return "No upcoming collections"
        return ", ".join(bins)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """
        Returns the date of the next collection and days remaining.
        """
        attrs = {}
        if not self.coordinator.data:
            return attrs
            
        next_date, bins = self._get_next_collection()
        if next_date:
            attrs["collection_date"] = next_date.strftime("%Y-%m-%d")
            today = datetime.now().date()
            days_until = (next_date - today).days
            attrs["days_until_collection"] = days_until
            attrs["bin_types"] = bins
        return attrs

    def _get_next_collection(self) -> tuple[Optional[datetime.date], List[str]]:
        """Find the nearest upcoming collection date and the bins collected on it."""
        today = datetime.now().date()
        future_collections = []

        for bin_type, dates in self.coordinator.data.items():
            for date_str in dates:
                if date_str != "No collection scheduled":
                    try:
                        d = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if d >= today:
                            # Use summary or normalized name if preferred, here we just strip " Collections" to be tidy
                            clean_name = bin_type.replace(" Collections", "").replace(" Collection", "")
                            future_collections.append((d, clean_name))
                    except ValueError:
                        pass

        if not future_collections:
            return None, []

        # Find the minimum date
        next_date = min(future_collections, key=lambda x: x[0])[0]

        # Get all bins collected on that date
        bins = [bin_type for d, bin_type in future_collections if d == next_date]
        return next_date, sorted(bins)

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """
        Returns device information to link this sensor entity to the primary 
        integration device in Home Assistant's device registry.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": DEVICE_NAME,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }
