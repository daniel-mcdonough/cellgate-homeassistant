"""Base entity for Cellgate integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CellgateDataUpdateCoordinator


class CellgateEntity(CoordinatorEntity[CellgateDataUpdateCoordinator]):
    """Base class for Cellgate entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CellgateDataUpdateCoordinator,
        port_data: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._device_id = port_data["device_id"]
        self._port_id = port_data["port_id"]
        self._key = f"{self._device_id}_{self._port_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info to group entities under one HA device per Cellgate device."""
        port_data = self.coordinator.data[self._key]
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"{port_data['map_location_name']} {port_data['device_description']}",
            manufacturer="Cellgate",
            model=port_data["hardware_type"],
        )
