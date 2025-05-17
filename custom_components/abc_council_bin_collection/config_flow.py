"""
Config flow for the ABC Council Bin Collection integration.

Handles the user input for setting up the integration, including sanitation 
and validation of the address. Also provides an options flow for changing
data interval along with enabling/disabling calendar event creation feature.
"""
import logging
import voluptuous as vol

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, MIN_UPDATE_INTERVAL
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs
from homeassistant import config_entries
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)


class BinCollectionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles config flow"""
    
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle the initial step where the user provides the address.
        
        If the provided address is a URL, it sanitizes and extracts the numeric address.
        Returns a form for the user until valid data is entered.
        """

        errors: Dict[str, str] = {}

        if user_input is not None:
            address_input = user_input.get("user_address", "")
            sanitized_address = self._sanitize_address(address_input)
            
            # Validate the sanitized address: must be non-empty and numeric.
            if not sanitized_address or not sanitized_address.isdigit():
                errors["base"] = "invalid_address"
                _LOGGER.error("Invalid address input: %s", address_input)
            else:
                _LOGGER.debug("Creating entry with sanitized address: %s", sanitized_address)
                return self.async_create_entry(
                    title="ABC Council Bin Collection",
                    data={"address": sanitized_address},
                    options={}  # Ensure options are initialized.
                )

        data_schema = vol.Schema({vol.Required("user_address"): str})
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    def _sanitize_address(self, address_input: str) -> str:
        """
        Extract and sanitize the numeric address if a full URL is provided.
        
        If the address starts with 'http(s)://', it attempts to extract the 'address'
        parameter from the URL's query string.
        """

        address_input = address_input.strip()
        lower = address_input.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            try:
                parsed_url = urlparse(address_input)
                qs = parse_qs(parsed_url.query)
                extracted = qs.get("address", [None])[0]
                return extracted.strip() if extracted else ""
            except Exception as ex:
                _LOGGER.error("Error parsing URL '%s': %s", address_input, ex)
                return ""
        return address_input

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for the Bin Collection integration"""

        return BinCollectionOptionsFlowHandler(config_entry)


class BinCollectionOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the Bin Collection integration"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options configuration flow"""

        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manage the options flow for the integration.
        """

        if user_input is not None:
            # Normalize the calendar entity: support inputs like "my_calendar" or "calendar.my_calendar".
            if "calendar_entity" in user_input:
                value = user_input["calendar_entity"].strip()
                if value and not value.startswith("calendar."):
                    value = f"calendar.{value}"
                user_input["calendar_entity"] = value

            _LOGGER.debug("User options received: %s", user_input)
            result = self.async_create_entry(title="", data=user_input)

            # Reload the integration on any options update to apply changes.
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return result

        return self.async_show_form(
            step_id="init", data_schema=self._get_options_schema()
        )

    def _get_options_schema(self) -> vol.Schema:
        """
        Define the options schema.
        """

        return vol.Schema({
            vol.Required(
                "update_interval",
                default=self._config_entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL)),
            vol.Required(
                "create_calendar_events",
                default=self._config_entry.options.get("create_calendar_events", False),
            ): bool,
            vol.Optional(
                "calendar_entity",
                default=self._config_entry.options.get("calendar_entity", "").strip(),
            ): str,
            vol.Optional(
                "summary_domestic",
                default=self._config_entry.options.get("summary_domestic", "Domestic Collections"),
            ): str,
            vol.Optional(
                "summary_recycling",
                default=self._config_entry.options.get("summary_recycling", "Recycling Collections"),
            ): str,
            vol.Optional(
                "summary_garden_food",
                default=self._config_entry.options.get("summary_garden_food", "Garden/Food Collections"),
            ): str,
        })