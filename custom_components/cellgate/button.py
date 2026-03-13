"""Cellgate button entities for gate open."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CellgateApiError
from .coordinator import CellgateDataUpdateCoordinator
from .entity import CellgateEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cellgate button entities."""
    coordinator: CellgateDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        CellgateGateButton(coordinator, port_data)
        for port_data in coordinator.data.values()
    )


class CellgateGateButton(CellgateEntity, ButtonEntity):
    """Button to open a Cellgate gate/door."""

    _attr_icon = "mdi:gate"

    def __init__(
        self,
        coordinator: CellgateDataUpdateCoordinator,
        port_data: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, port_data)
        self._attr_unique_id = f"{self._device_id}_{self._port_id}"
        self._attr_name = port_data["port_description"]

    async def async_press(self) -> None:
        """Open the gate."""
        try:
            await self.coordinator.async_open_gate(self._device_id, self._port_id)
        except CellgateApiError as err:
            raise HomeAssistantError(f"Failed to open gate: {err}") from err
