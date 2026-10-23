"""
Config flow for the ABC Council Bin Collection integration.

Handles user input for setting up integration, including sanitation
and validation of the address.

Provides option flow for changing data interval along with toggling
calendar event creation.
"""

import logging
import re
import voluptuous as vol
import asyncio
import aiohttp

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, MIN_UPDATE_INTERVAL
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class BinCollectionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._scraped_addresses: Dict[str, str] = {}
        self._reconfigure: bool = False

    async def _async_fetch_addresses(self, postcode: str) -> bool:
        """Fetch addresses for a given postcode."""
        try:
            # Format postcode to remove spaces and lowercase
            formatted_postcode = postcode.replace(" ", "").lower()
            url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-address/?postcode={formatted_postcode}"
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(30.0):
                response = await session.get(url)
                response.raise_for_status()
                html = await response.text()

                # Extract addresses from dropdown
                matches = re.findall(r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', html)
                if matches:
                    self._scraped_addresses = {match[0]: match[1].strip() for match in matches}
                else:
                    self._scraped_addresses = {}
                return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            _LOGGER.error("Cannot connect to API for postcode lookup: %s", ex)
            return False

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        errors: Dict[str, str] = {}
        self._reconfigure = False

        if user_input is not None:
            address_input = user_input.get("user_address", "")
            sanitized_address = self._sanitize_address(address_input)

            # Check if input is a postcode (not a direct URL and not purely digits)
            is_url = address_input.lower().startswith("http://") or address_input.lower().startswith("https://")
            
            if not sanitized_address.isdigit() and not is_url and sanitized_address:
                # Treat as postcode
                success = await self._async_fetch_addresses(sanitized_address)
                if success and self._scraped_addresses:
                    return await self.async_step_select_address()
                elif success:
                    errors["base"] = "no_addresses_found"
                else:
                    errors["base"] = "cannot_connect"
            else:
                # Treat as direct Address ID / URL
                if not sanitized_address or not sanitized_address.isdigit():
                    errors["base"] = "invalid_address"
                    _LOGGER.error("Invalid address input: %s", address_input)
                else:
                    # Validate connection to the API before creating entry
                    try:
                        url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={sanitized_address}"
                        session = async_get_clientsession(self.hass)
                        async with asyncio.timeout(30.0):
                            response = await session.get(url)
                            response.raise_for_status()
                    except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
                        _LOGGER.error("Cannot connect to API for validation: %s", ex)
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(sanitized_address)
                        self._abort_if_unique_id_configured()

                        _LOGGER.debug("Creating entry with sanitized address: %s", sanitized_address)
                        return self.async_create_entry(
                            title="ABC Council Bin Collection",
                            data={"address": sanitized_address},
                            options={}  # Ensure options are initialized.
                        )

        data_schema = vol.Schema({vol.Required("user_address"): str})
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"url": "https://www.armaghbanbridgecraigavon.gov.uk/resident/when-is-my-bin-day/"}
        )

    async def async_step_select_address(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the step to select an address from the scraped dropdown."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            selected_id = user_input["address_id"]
            
            if self._reconfigure:
                return await self._async_handle_reconfigure_creation(selected_id)
            else:
                try:
                    url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={selected_id}"
                    session = async_get_clientsession(self.hass)
                    async with asyncio.timeout(30.0):
                        response = await session.get(url)
                        response.raise_for_status()
                except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
                    _LOGGER.error("Cannot connect to API for validation: %s", ex)
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(selected_id)
                    self._abort_if_unique_id_configured()

                    _LOGGER.debug("Creating entry with selected address: %s", selected_id)
                    return self.async_create_entry(
                        title="ABC Council Bin Collection",
                        data={"address": selected_id},
                        options={}
                    )

        # Create a dropdown from self._scraped_addresses
        address_options = {id: address for id, address in self._scraped_addresses.items()}
        data_schema = vol.Schema({
            vol.Required("address_id"): vol.In(address_options)
        })

        return self.async_show_form(
            step_id="select_address",
            data_schema=data_schema,
            errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a reconfiguration flow initialized by the user."""
        
        errors: Dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._reconfigure = True

        if user_input is not None:
            address_input = user_input.get("user_address", "")
            sanitized_address = self._sanitize_address(address_input)

            is_url = address_input.lower().startswith("http://") or address_input.lower().startswith("https://")
            
            if not sanitized_address.isdigit() and not is_url and sanitized_address:
                # Treat as postcode
                success = await self._async_fetch_addresses(sanitized_address)
                if success and self._scraped_addresses:
                    return await self.async_step_select_address()
                elif success:
                    errors["base"] = "no_addresses_found"
                else:
                    errors["base"] = "cannot_connect"
            else:
                if not sanitized_address or not sanitized_address.isdigit():
                    errors["base"] = "invalid_address"
                else:
                    return await self._async_handle_reconfigure_creation(sanitized_address)

        current_address = entry.data.get("address", "") if entry else ""
        data_schema = vol.Schema({vol.Required("user_address", default=current_address): str})
        
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"url": "https://www.armaghbanbridgecraigavon.gov.uk/resident/when-is-my-bin-day/"}
        )

    async def _async_handle_reconfigure_creation(self, address_id: str) -> Dict[str, Any]:
        """Finalize the reconfigure process."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors = {}
        try:
            url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={address_id}"
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(30.0):
                response = await session.get(url)
                response.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            errors["base"] = "cannot_connect"
            # Return to step_select_address or reconfigure form depending on what was called
            if self._scraped_addresses:
                address_options = {id: address for id, address in self._scraped_addresses.items()}
                data_schema = vol.Schema({vol.Required("address_id"): vol.In(address_options)})
                return self.async_show_form(step_id="select_address", data_schema=data_schema, errors=errors)
            else:
                data_schema = vol.Schema({vol.Required("user_address", default=address_id): str})
                return self.async_show_form(step_id="reconfigure", data_schema=data_schema, errors=errors)
        else:
            # Prevent duplicate entries by checking if another service already uses this address
            for existing_entry in self._async_current_entries():
                if existing_entry.unique_id == address_id and existing_entry.entry_id != entry.entry_id:
                    return self.async_abort(reason="already_configured")

            return self.async_update_reload_and_abort(
                entry,
                unique_id=address_id,
                data={**entry.data, "address": address_id},
                reason="reconfigure_successful",
            )

    def _sanitize_address(self, address_input: str) -> str:
        """
        Sanitises and extracts the the "address" parameter if complete URL provided.
        """

        address_input = address_input.strip()
        lower = address_input.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            try:
                parsed_url = urlparse(address_input)
                qs = parse_qs(parsed_url.query)
                extracted = qs.get("address", [None])[0]
                return extracted.strip() if extracted else ""
            except (ValueError, TypeError, AttributeError) as ex:
                _LOGGER.error("Error parsing URL '%s': %s", address_input, ex)
                return ""
        return address_input

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """
        Get the options flow for the Bin Collection integration.
        """

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
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init", data_schema=self._get_options_schema()
        )

    def _get_options_schema(self) -> vol.Schema:
        """
        Options schema.
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