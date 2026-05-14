"""DataUpdateCoordinator for Nuki ctoken integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

if TYPE_CHECKING:
    from . import NukiCtokenClient

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class NukiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /list (and /log) for a single Nuki device.

    Uses the bridge-cached /list response — never talks directly to the lock,
    so battery is not affected by polling.
    """

    def __init__(self, hass: HomeAssistant, client: NukiCtokenClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{client.nuki_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            devices = await self.client.request("list")
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        if not isinstance(devices, list):
            raise UpdateFailed(f"Unexpected /list response: {devices!r}")

        device_data: dict[str, Any] | None = None
        for device in devices:
            if device.get("nukiId") == self.client.nuki_id:
                device_data = dict(device)
                break

        if device_data is None:
            raise UpdateFailed(
                f"Device {self.client.nuki_id} not found in bridge /list response"
            )

        # Activity log is stored on the bridge — safe to poll, no lock battery drain
        try:
            logs = await self.client.request(
                "log", {"nukiId": self.client.nuki_id, "count": 10}
            )
            device_data["_log"] = logs if isinstance(logs, list) else []
        except Exception:
            device_data["_log"] = []

        return device_data
