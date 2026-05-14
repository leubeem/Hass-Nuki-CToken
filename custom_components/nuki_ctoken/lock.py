"""Lock entity for Nuki ctoken integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_TYPE_OPENER,
    DOMAIN,
    OP_STATE_ONLINE,
    OP_STATE_OPEN,
    OP_STATE_OPENING,
    OP_STATE_RTO_ACTIVE,
    SL_STATE_LOCKING,
    SL_STATE_LOCKED,
    SL_STATE_MOTOR_BLOCKED,
    SL_STATE_UNLATCHING,
    SL_STATE_UNLOCKING,
)
from .coordinator import NukiCoordinator
from .entity import NukiEntity

_SL_UNLOCKED = {3, 5}       # unlatched / unlatched lock'n'go
_SL_UNLOCKING = {SL_STATE_UNLOCKING, SL_STATE_UNLATCHING}
_OP_UNLOCKED = {OP_STATE_RTO_ACTIVE, OP_STATE_OPEN}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NukiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NukiLock(coordinator, entry)])


class NukiLock(NukiEntity, LockEntity):
    """Represents a Nuki Smart Lock or Opener as a HA lock entity."""

    _attr_name = None  # entity name = device name
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_lock"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _state_code(self) -> int | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("lastKnownState", {}).get("state")

    def _is_opener(self) -> bool:
        return self.coordinator.client.device_type == DEVICE_TYPE_OPENER

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def is_locked(self) -> bool | None:
        state = self._state_code
        if state is None:
            return None
        if self._is_opener():
            return state == OP_STATE_ONLINE
        return state == SL_STATE_LOCKED

    @property
    def is_locking(self) -> bool | None:
        state = self._state_code
        if state is None:
            return None
        if self._is_opener():
            return False
        return state == SL_STATE_LOCKING

    @property
    def is_unlocking(self) -> bool | None:
        state = self._state_code
        if state is None:
            return None
        if self._is_opener():
            return state == OP_STATE_OPENING
        return state in _SL_UNLOCKING

    @property
    def is_jammed(self) -> bool | None:
        state = self._state_code
        if state is None:
            return None
        return state == SL_STATE_MOTOR_BLOCKED

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def async_lock(self, **kwargs: Any) -> None:
        await self.coordinator.client.lock_action("lock")
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs: Any) -> None:
        await self.coordinator.client.lock_action("unlock")
        await self.coordinator.async_request_refresh()

    async def async_open(self, **kwargs: Any) -> None:
        await self.coordinator.client.lock_action("open")
        await self.coordinator.async_request_refresh()
