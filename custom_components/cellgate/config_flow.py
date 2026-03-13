"""Config flow for Cellgate integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CellgateApiClient, CellgateAuthError, CellgateConnectionError
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


class CellgateConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cellgate."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = CellgateApiClient(
                session=session,
                username=user_input["username"],
                password=user_input["password"],
            )
            try:
                await client.authenticate()
                locations = await client.get_map_locations()
            except CellgateAuthError:
                errors["base"] = "invalid_auth"
            except (CellgateConnectionError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                if not locations:
                    errors["base"] = "no_devices"
                else:
                    await self.async_set_unique_id(user_input["username"])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input["username"],
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(
                self.context["entry_id"]
            )
            session = async_get_clientsession(self.hass)
            client = CellgateApiClient(
                session=session,
                username=entry.data["username"],
                password=user_input["password"],
            )
            try:
                await client.authenticate()
            except CellgateAuthError:
                errors["base"] = "invalid_auth"
            except (CellgateConnectionError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, "password": user_input["password"]},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            errors=errors,
        )
