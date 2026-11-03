"""Config flow: the user pastes their Waltr API token."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import WaltrApi, WaltrAuthError, WaltrError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TOKEN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class WaltrConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, token: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
        api = WaltrApi(async_get_clientsession(self.hass), token.strip())
        try:
            locations = await api.locations()
        except WaltrAuthError:
            return [], {"base": "invalid_auth"}
        except WaltrError as err:
            _LOGGER.debug("Waltr check failed: %s", err)
            return [], {"base": "cannot_connect"}
        if not locations:
            return [], {"base": "no_locations"}
        return locations, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_API_TOKEN].strip()
            locations, errors = await self._validate(token)
            if not errors:
                ids = sorted(str(loc["id"]) for loc in locations)
                await self.async_set_unique_id("-".join(ids))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=locations[0].get("name") or "Waltr",
                    data={CONF_API_TOKEN: token},
                )
        return self.async_show_form(step_id="user", data_schema=TOKEN_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_API_TOKEN].strip()
            _, errors = await self._validate(token)
            if not errors:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data={CONF_API_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=TOKEN_SCHEMA, errors=errors
        )
