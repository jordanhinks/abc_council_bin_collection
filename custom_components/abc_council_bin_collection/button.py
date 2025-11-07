"""
Button platform for the ABC Council Bin Collection integration.

This module provides the 'Clear Bin Events' button entity, which, when 
activated, clears all persistent bin collection events stored by the integration.
"""

import logging

from .const import DOMAIN, DEVICE_NAME, DEVICE_MANUFACTURER, DEVICE_MODEL
from .storage import BinCollectionStorage
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """
    Sets up the Clear Bin Events button entity from a configuration entry.

    The function retrieves the coordinator from Home Assistant data, and uses its 
    storage, entry ID, and address to initialize and register the button entity.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant core object.
    entry : ConfigEntry
        The configuration entry object for the integration.
    async_add_entities : AddEntitiesCallback
        Callback function to add new entities to Home Assistant.
    """

    _LOGGER.debug("Setting up Clear Bin Events button entity...")

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not coordinator:
        _LOGGER.error("Coordinator not found for entry_id: %s", entry.entry_id)
        return

    async_add_entities([ClearBinEventsButton(coordinator.storage, entry.entry_id, coordinator.address)])
    _LOGGER.debug("Clear Bin Events button entity successfully registered.")

class ClearBinEventsButton(ButtonEntity):
    """
    Represents a button entity used to clear all persistently stored 
    bin collection events for this integration instance.
    """

    def __init__(self, storage: BinCollectionStorage, entry_id: str, address: str) -> None:
        """
        Initializes the Clear Bin Events button entity.

        Parameters
        ----------
        storage : BinCollectionStorage
            The storage object used to clear the persistent event data.
        entry_id : str
            The unique ID of the configuration entry for device identification.
        address : str
            The address string used for generating the device identifier.
        """

        self._storage = storage
        self._entry_id = entry_id
        self._address = address
        self._attr_name = "Clear Bin Events" #translation
        self._attr_icon = "mdi:trash-can"
        self._attr_unique_id = f"clear_bin_events_{entry_id}"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._address)},
            "name": DEVICE_NAME,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

    async def async_press(self) -> None:
        """
        Performs the action of clearing all stored bin collection events 
        when the button is pressed.

        Calls the `clear_data` method on the storage object and logs the 
        success or any exception encountered.
        """

        try:
            _LOGGER.info("Clearing all stored bin collection events...")
            await self._storage.clear_data()
            _LOGGER.info("Bin collection events successfully cleared.")
        except Exception as err:
            _LOGGER.exception("Failed to clear bin collection events: %s", err)
