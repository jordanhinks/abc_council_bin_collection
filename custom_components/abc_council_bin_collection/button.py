"""
Button platform for ABC Council Bin Collection integration.

Provides a button entity that, when pressed, clears persistent bin collection events.
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
    """Set up the Clear Bin Events button entity."""
    _LOGGER.debug("Setting up Clear Bin Events button entity...")

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not coordinator:
        _LOGGER.error("Coordinator not found for entry_id: %s", entry.entry_id)
        return

    async_add_entities([ClearBinEventsButton(coordinator.storage, entry.entry_id, coordinator.address)])
    _LOGGER.debug("Clear Bin Events button entity successfully registered.")

class ClearBinEventsButton(ButtonEntity):
    """Clear events button entity"""

    def __init__(self, storage: BinCollectionStorage, entry_id: str, address: str) -> None:
        """Initialize the button entity"""

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
        """Action to occur upon button trigger"""

        try:
            _LOGGER.info("Clearing all stored bin collection events...")
            await self._storage.clear_data()
            _LOGGER.info("Bin collection events successfully cleared.")
        except Exception as err:
            _LOGGER.exception("Failed to clear bin collection events: %s", err)
