import voluptuous as vol
from urllib.parse import urlparse, parse_qs
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
import logging

_LOGGER = logging.getLogger(__name__)

class BinCollectionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Bin Collection integration."""
    
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user provides the address."""
        errors = {}

        if user_input is not None:
            address_input = user_input.get("user_address", "")
            sanitized_address = self._sanitize_address(address_input)
            
            if not sanitized_address or not sanitized_address.isdigit():
                errors["user_address"] = "invalid_address"
                _LOGGER.error("Invalid address input: %s", address_input)
            else:
                _LOGGER.debug("Creating entry with address: %s", sanitized_address)
                return self.async_create_entry(
                    title="Bin Collection",
                    data={"address": sanitized_address},
                    options={}  # Ensure options are initialized
                )

        data_schema = vol.Schema({vol.Required("user_address"): str})
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    def _sanitize_address(self, address_input: str) -> str:
        """Extract the numeric address if a full URL is provided."""
        lower = address_input.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            parsed_url = urlparse(address_input)
            qs = parse_qs(parsed_url.query)
            extracted = qs.get("address", [None])[0]
            return extracted.strip() if extracted else ""
        return address_input.strip()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for the Bin Collection integration."""
        return BinCollectionOptionsFlowHandler(config_entry)

class BinCollectionOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the Bin Collection integration."""

    def __init__(self, config_entry):
        # Save the configuration entry under a non-conflicting name.
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options flow."""
        if user_input is not None:
            # Normalize the calendar entity so that both "my_calendar" and
            # "calendar.my_calendar" are stored as "calendar.my_calendar"
            if "calendar_entity" in user_input:
                value = user_input["calendar_entity"].strip()
                if value and not value.startswith("calendar."):
                    value = f"calendar.{value}"
                user_input["calendar_entity"] = value

            _LOGGER.debug("User input received: %s", user_input)
            result = self.async_create_entry(title="", data=user_input)
            # Reload the integration upon saving options.
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return result

        return self.async_show_form(step_id="init", data_schema=self._get_options_schema())

    def _get_options_schema(self):
        """Define the schema for options."""
        return vol.Schema({
            vol.Required(
                "update_interval", 
                default=self._config_entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
            ): int,
            vol.Required(
                "create_calendar_events", 
                default=self._config_entry.options.get("create_calendar_events", False)
            ): bool,
            vol.Optional(
                "calendar_entity", 
                default=self._config_entry.options.get("calendar_entity", "").strip()
            ): str,
            vol.Optional(
                "summary_domestic", 
                default=self._config_entry.options.get("summary_domestic", "Domestic Collections")
            ): str,
            vol.Optional(
                "summary_recycling", 
                default=self._config_entry.options.get("summary_recycling", "Recycling Collections")
            ): str,
            vol.Optional(
                "summary_garden_food", 
                default=self._config_entry.options.get("summary_garden_food", "Garden/Food Collections")
            ): str,
        })
