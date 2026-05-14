"""Binary sensor entities for Nuki ctoken integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DOOR_STATE_OPEN
from .coordinator import NukiCoordinator
from .entity import NukiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NukiCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NukiEntity] = [NukiBatteryCriticalSensor(coordinator, entry)]
    last_known = (coordinator.data or {}).get("lastKnownState", {})
    if last_known.get("doorsensorState") is not None:
        entities.append(NukiDoorSensor(coordinator, entry))
    async_add_entities(entities)


class NukiBatteryCriticalSensor(NukiEntity, BinarySensorEntity):
    """True when the lock battery is critically low."""

    _attr_translation_key = "battery_critical"
    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_battery_critical"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("lastKnownState", {}).get("batteryCritical", False)


class NukiDoorSensor(NukiEntity, BinarySensorEntity):
    """True when the door is open (requires Nuki door sensor accessory)."""

    _attr_translation_key = "door"
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_door"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        state = data.get("lastKnownState", {}).get("doorsensorState")
        if state is None:
            return None
        return state == DOOR_STATE_OPEN
