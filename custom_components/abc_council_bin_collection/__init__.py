import logging

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .coordinator import BinCollectionDataUpdateCoordinator
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button"]

def _extract_options(entry: ConfigEntry) -> tuple[str, timedelta, dict]:
    """Extract and validate options from the config entry"""

    address = entry.data.get("address")
    options = entry.options if entry.options else {}
    update_interval = timedelta(hours=options.get("update_interval", DEFAULT_UPDATE_INTERVAL))
    event_summaries = {
        "Domestic Collections": options.get("summary_domestic", "Domestic Collections"),
        "Recycling Collections": options.get("summary_recycling", "Recycling Collections"),
        "Garden/Food Collections": options.get("summary_garden_food", "Garden/Food Collections"),
    }

    return address, update_interval, event_summaries

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the ABC Council Bin Collection integration from a config entry"""

    _LOGGER.info("ABC Council Bin Collection integration starting: %s", entry.entry_id)

    # Ensure DOMAIN storage is initialized
    hass.data.setdefault(DOMAIN, {})

    address, update_interval, event_summaries = _extract_options(entry)
    if not address:
        _LOGGER.error("Missing address in entry data - reinstall integration.")
        return False

    _LOGGER.debug("Setting up integration with address: %s, update_interval: %s, options: %s", address, update_interval, entry.options)

    try:
        # Initialize coordinator
        coordinator = BinCollectionDataUpdateCoordinator(
            hass=hass,
            address=address,
            update_interval=update_interval,
            create_calendar_events=entry.options.get("create_calendar_events", False),
            calendar_entity=entry.options.get("calendar_entity", "").strip(),
            event_summaries=event_summaries,
        )
        await coordinator.load_stored_events()
        coordinator.data = await coordinator._async_update_data()
    except Exception as err:
        _LOGGER.exception("Error setting up coordinator: %s", err)
        return False

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("ABC Council Bin Collection integration setup successfully: %s", entry.entry_id)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry"""

    _LOGGER.info("ABC Council Bin Collection unloading: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        _LOGGER.info("ABC Council Bin Collection unloaded successfully: %s", entry.entry_id)
    else:
        _LOGGER.warning("ABC Council Bin Collection failed to unload: %s", entry.entry_id)

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry and clear stored persistent data"""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator and hasattr(coordinator, "storage"):
        _LOGGER.debug("Storage found for integration %s, clearing data...", entry.entry_id)
        try:
            await coordinator.storage.clear_data()
        except Exception as err:
            _LOGGER.exception("Error clearing storage for integration %s: %s", entry.entry_id, err)
    else:
        _LOGGER.info("Storage instance not found for entry %s, possibly removed too early or none exist, this is ok.", entry.entry_id)
    
    hass.data[DOMAIN].pop(entry.entry_id, None)

    _LOGGER.info("ABC Council Bin Collection successfully removed entry %s from hass.data", entry.entry_id)