from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import BinCollectionDataUpdateCoordinator
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up bin_collection from a config entry."""
    if not entry.data.get("address"):
        _LOGGER.error("Missing address in entry data!")
        return False  # Prevent setup if no valid address is found

    address = entry.data["address"]
    
    options = {**entry.options} if entry.options else {}

    update_interval_hours = options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
    update_interval = timedelta(hours=update_interval_hours)

    create_calendar_events = options.get("create_calendar_events", False)
    calendar_entity = options.get("calendar_entity", "").strip()

    # This dictionary is used ONLY for calendar event creation.
    event_summaries = {
        "Domestic Collections": options.get("summary_domestic", "Domestic Collections"),
        "Recycling Collections": options.get("summary_recycling", "Recycling Collections"),
        "Garden/Food Collections": options.get("summary_garden_food", "Garden/Food Collections"),
    }

    _LOGGER.debug("Setting up Bin Collection with:")
    _LOGGER.debug("Address: %s", address)
    _LOGGER.debug("Update Interval: %s hours", update_interval_hours)
    _LOGGER.debug("Options: %s", options)

    coordinator = BinCollectionDataUpdateCoordinator(
        hass,
        address=address,
        update_interval=update_interval,
        create_calendar_events=create_calendar_events,
        calendar_entity=calendar_entity,
        event_summaries=event_summaries,
    )

    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry: %s", entry.entry_id)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
