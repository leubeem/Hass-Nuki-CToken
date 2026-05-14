"""Sensor entities for Nuki ctoken integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOG_ACTION_NAMES, LOG_TRIGGER_NAMES
from .coordinator import NukiCoordinator
from .entity import NukiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NukiCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NukiEntity] = [
        NukiStateSensor(coordinator, entry),
        NukiFirmwareSensor(coordinator, entry),
        NukiLastActivitySensor(coordinator, entry),
    ]
    # Battery charge state is not always available (depends on firmware/hardware)
    last_known = (coordinator.data or {}).get("lastKnownState", {})
    if last_known.get("batteryChargeState") is not None:
        entities.append(NukiBatterySensor(coordinator, entry))
    async_add_entities(entities)


class NukiStateSensor(NukiEntity, SensorEntity):
    """Current lock state as a human-readable string (e.g. 'locked', 'unlatched')."""

    _attr_translation_key = "state"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_state"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("lastKnownState", {}).get("stateName")


class NukiBatterySensor(NukiEntity, SensorEntity):
    """Battery charge level in percent."""

    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_battery"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("lastKnownState", {}).get("batteryChargeState")


class NukiFirmwareSensor(NukiEntity, SensorEntity):
    """Firmware version of the Nuki device."""

    _attr_translation_key = "firmware"
    _attr_icon = "mdi:chip"
    _attr_entity_registry_enabled_default = False  # diagnostic, hidden by default

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_firmware"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("firmwareVersion")


class NukiLastActivitySensor(NukiEntity, SensorEntity):
    """Timestamp of the last recorded activity; attributes hold a recent activity list."""

    _attr_translation_key = "last_activity"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_activity"

    @property
    def native_value(self) -> datetime | None:
        data = self.coordinator.data
        if not data:
            return None
        logs: list[dict[str, Any]] = data.get("_log", [])
        ts = logs[0].get("date") if logs else data.get("lastKnownState", {}).get("timestamp")
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        logs: list[dict[str, Any]] = data.get("_log", [])
        return {
            "recent_activity": [
                {
                    "timestamp": entry.get("date"),
                    "action": LOG_ACTION_NAMES.get(entry.get("action", -1), str(entry.get("action"))),
                    "trigger": LOG_TRIGGER_NAMES.get(entry.get("trigger", -1), str(entry.get("trigger"))),
                    "user": entry.get("authName") or None,
                    "state": entry.get("stateName"),
                }
                for entry in logs
            ]
        }
