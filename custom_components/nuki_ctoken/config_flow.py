"""Config flow for Nuki ctoken."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigConfigFlowResult

from . import NukiCtokenClient
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_HOST,
    CONF_NUKI_ID,
    CONF_PORT,
    CONF_TOKEN,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NukiCtokenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nuki ctoken."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int | None = None
        self._token: str | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for bridge host and token, then discover devices via /list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = int(user_input[CONF_PORT])
            self._token = user_input[CONF_TOKEN].strip()

            try:
                self._devices = await self._async_fetch_devices(self._host, self._port, self._token)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Nuki ctoken setup failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                elif len(self._devices) == 1:
                    return await self._async_create_entry_for_device(self._devices[0])
                else:
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user choose a Nuki device from /list."""
        errors: dict[str, str] = {}
        choices = {str(device[CONF_NUKI_ID]): _device_label(device) for device in self._devices}

        if user_input is not None:
            selected_id = int(user_input[CONF_NUKI_ID])
            device = next((item for item in self._devices if item[CONF_NUKI_ID] == selected_id), None)
            if device is None:
                errors["base"] = "unknown_device"
            else:
                return await self._async_create_entry_for_device(device)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_NUKI_ID): vol.In(choices)}),
            errors=errors,
        )

    async def _async_fetch_devices(self, host: str, port: int, token: str) -> list[dict[str, Any]]:
        """Fetch and normalize devices from Nuki Bridge /list."""
        client = NukiCtokenClient(
            self.hass,
            {
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_TOKEN: token,
                CONF_NUKI_ID: 0,
                CONF_DEVICE_TYPE: 0,
                CONF_DEVICE_NAME: "setup",
            },
        )
        raw = await client.list_devices()

        if not isinstance(raw, list):
            raise ValueError(f"Unexpected /list response: {raw!r}")

        devices: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            nuki_id = item.get("nukiId")
            device_type = item.get("deviceType")
            if nuki_id is None or device_type is None:
                continue
            name = item.get("name") or item.get("deviceName") or f"Nuki {nuki_id}"
            devices.append(
                {
                    CONF_NUKI_ID: int(nuki_id),
                    CONF_DEVICE_TYPE: int(device_type),
                    CONF_DEVICE_NAME: str(name),
                }
            )

        return devices

    async def _async_create_entry_for_device(self, device: dict[str, Any]) -> ConfigFlowResult:
        """Create a config entry for the selected device."""
        assert self._host is not None
        assert self._port is not None
        assert self._token is not None

        await self.async_set_unique_id(f"{self._host}:{self._port}:{device[CONF_NUKI_ID]}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=_device_label(device),
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_TOKEN: self._token,
                CONF_NUKI_ID: device[CONF_NUKI_ID],
                CONF_DEVICE_TYPE: device[CONF_DEVICE_TYPE],
                CONF_DEVICE_NAME: device[CONF_DEVICE_NAME],
            },
        )


def _device_label(device: dict[str, Any]) -> str:
    return f"{device.get(CONF_DEVICE_NAME, 'Nuki')} ({device[CONF_NUKI_ID]})"
