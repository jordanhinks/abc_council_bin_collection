"""Diagnostics support for ABC Council Bin Collection."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BinCollectionDataUpdateCoordinator

# Fields to redact from the downloaded diagnostics report to protect user privacy
TO_REDACT = {"address", "user_address", "unique_id"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: BinCollectionDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Build the diagnostic data payload
    diagnostics_data = {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": coordinator.data,
        "options_state": {
            "update_interval": str(coordinator.update_interval),
            "create_calendar_events": coordinator.create_calendar_events,
            "calendar_entity": coordinator.calendar_entity,
            "event_summaries": coordinator.event_summaries,
        },
    }

    return diagnostics_data
