"""Nuki Bridge integration using encrypted ctoken authentication."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ._crypto import secretbox_encrypt
from .const import (
    ACTION_MAP,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_ENTRY_ID,
    CONF_HOST,
    CONF_NUKI_ID,
    CONF_PORT,
    CONF_SOURCE,
    CONF_TOKEN,
    DOMAIN,
    PLATFORMS,
    REQUEST_TIMEOUT,
    SERVICE_NAMES,
)
from .coordinator import NukiCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Optional(CONF_SOURCE): str,
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_ctoken(token: str) -> dict[str, str]:
    """Build Nuki encrypted token parameters."""
    timestamp = _utc_now()
    random_number = secrets.randbelow(65536)
    plaintext = f"{timestamp},{random_number}".encode("utf-8")

    key = hashlib.sha256(token.encode("utf-8")).digest()
    nonce = secrets.token_bytes(24)
    encrypted = secretbox_encrypt(plaintext, nonce, key)

    return {
        "ctoken": encrypted.hex(),
        "nonce": nonce.hex(),
    }


class NukiCtokenClient:
    """Async HTTP client for the local Nuki Bridge API."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self.host: str = data[CONF_HOST]
        self.port: int = data[CONF_PORT]
        self.token: str = data[CONF_TOKEN]
        self.nuki_id: int = data[CONF_NUKI_ID]
        self.device_type: int = data[CONF_DEVICE_TYPE]
        self.device_name: str = data.get(CONF_DEVICE_NAME, str(data[CONF_NUKI_ID]))

    async def request(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Call a Bridge API endpoint with ctoken authentication."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}:{self.port}/{endpoint.lstrip('/')}"
        request_params = dict(params or {})
        request_params.update(build_ctoken(self.token))

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await session.get(url, params=request_params)
                text = await response.text()
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(
                f"Could not reach Nuki Bridge at {self.host}:{self.port}: {err}"
            ) from err

        if response.status >= 400:
            raise HomeAssistantError(f"Nuki Bridge returned HTTP {response.status}: {text}")

        try:
            return await response.json(content_type=None)
        except Exception:
            return text

    async def lock_action(self, action_name: str) -> Any:
        """Execute a lockAction on the Bridge."""
        if action_name not in ACTION_MAP:
            raise ServiceValidationError(f"Unknown Nuki action: {action_name}")
        return await self.request(
            "lockAction",
            {
                "nukiId": self.nuki_id,
                "deviceType": self.device_type,
                "action": ACTION_MAP[action_name],
                "nowait": 1,
            },
        )

    async def list_devices(self) -> Any:
        """Call /list on the Bridge."""
        return await self.request("list")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nuki ctoken from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = NukiCtokenClient(hass, dict(entry.data))
    coordinator = NukiCoordinator(hass, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(str(err)) from err

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.data[DOMAIN].get("_services_registered"):
        await _async_register_services(hass)
        hass.data[DOMAIN]["_services_registered"] = True

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register service actions."""

    async def _handler(call: ServiceCall) -> None:
        await _async_handle_service_call(hass, call)

    for service_name in SERVICE_NAMES:
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(DOMAIN, service_name, _handler, schema=SERVICE_SCHEMA)


async def _async_handle_service_call(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle a lock/unlock/open service call."""
    action_name = call.service
    coordinator = _get_coordinator_for_call(hass, call)
    client = coordinator.client

    actor = await _async_describe_actor(hass, call)
    timestamp = _utc_now()

    response = await client.lock_action(action_name)

    # Refresh coordinator so entity state updates immediately
    await coordinator.async_request_refresh()

    event_data = {
        "timestamp": timestamp,
        "action": action_name,
        "device_name": client.device_name,
        "nuki_id": client.nuki_id,
        "entry_id": _entry_id_for_coordinator(hass, coordinator),
        "source": call.data.get(CONF_SOURCE),
        "user_id": actor.get("user_id"),
        "user_name": actor.get("user_name"),
        "automation_entity_id": actor.get("automation_entity_id"),
        "automation_name": actor.get("automation_name"),
        "context_id": call.context.id,
        "context_parent_id": call.context.parent_id,
        "nuki_response": response,
    }

    _LOGGER.info(
        "Nuki action executed timestamp=%s action=%s device=%s nuki_id=%s "
        "user_id=%s user_name=%s automation_entity_id=%s automation_name=%s "
        "source=%s context_id=%s parent_id=%s response=%s",
        timestamp, action_name, client.device_name, client.nuki_id,
        actor.get("user_id"), actor.get("user_name"),
        actor.get("automation_entity_id"), actor.get("automation_name"),
        call.data.get(CONF_SOURCE), call.context.id, call.context.parent_id,
        response,
    )

    hass.bus.async_fire(f"{DOMAIN}_action", event_data)


def _get_coordinator_for_call(hass: HomeAssistant, call: ServiceCall) -> NukiCoordinator:
    """Return the coordinator for this service call."""
    data = hass.data.get(DOMAIN, {})
    coordinators = {k: v for k, v in data.items() if isinstance(v, NukiCoordinator)}

    if not coordinators:
        raise ServiceValidationError("No Nuki ctoken config entry is loaded.")

    entry_id = call.data.get(CONF_ENTRY_ID)
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise ServiceValidationError(
                f"No loaded Nuki ctoken entry found for entry_id={entry_id}"
            )
        return coordinator

    if len(coordinators) > 1:
        raise ServiceValidationError(
            "Multiple Nuki ctoken entries are loaded. Add entry_id to the service call data."
        )

    return next(iter(coordinators.values()))


def _entry_id_for_coordinator(hass: HomeAssistant, coordinator: NukiCoordinator) -> str | None:
    for entry_id, value in hass.data.get(DOMAIN, {}).items():
        if value is coordinator:
            return entry_id
    return None


async def _async_describe_actor(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Best-effort user and automation attribution from the HA context."""
    user_id = call.context.user_id
    user_name = None

    if user_id:
        try:
            user = await hass.auth.async_get_user(user_id)
            if user is not None:
                user_name = user.name
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not resolve HA user for user_id=%s", user_id)

    automation_entity_id = None
    automation_name = None
    parent_id = call.context.parent_id

    if parent_id:
        try:
            for state in hass.states.async_all("automation"):
                state_context = getattr(state, "context", None)
                if state_context is None:
                    continue
                if state_context.id == parent_id or state_context.parent_id == parent_id:
                    automation_entity_id = state.entity_id
                    automation_name = state.name
                    break
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not resolve automation for parent context %s", parent_id)

    return {
        "user_id": user_id,
        "user_name": user_name,
        "automation_entity_id": automation_entity_id,
        "automation_name": automation_name,
    }
