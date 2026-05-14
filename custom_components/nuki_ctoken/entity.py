"""Base entity for Nuki ctoken integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODEL_NAMES
from .coordinator import NukiCoordinator


class NukiEntity(CoordinatorEntity[NukiCoordinator]):
    """Base class for all Nuki ctoken entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NukiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.client.nuki_id))},
            name=self.coordinator.client.device_name,
            manufacturer="Nuki",
            model=MODEL_NAMES.get(self.coordinator.client.device_type, "Nuki Device"),
            sw_version=data.get("firmwareVersion"),
        )
