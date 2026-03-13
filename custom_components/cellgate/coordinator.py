"""Cellgate data update coordinator."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CellgateApiClient, CellgateApiError, CellgateAuthError, CellgateConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CellgateDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches device/port data from Cellgate API."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        session = async_get_clientsession(hass)
        self.api = CellgateApiClient(
            session=session,
            username=entry.data["username"],
            password=entry.data["password"],
        )
        # Populated during first refresh: list of (device_id, property_location_id) tuples
        self._device_locations: list[tuple[str, str, str]] = []

    async def _async_setup(self) -> None:
        """Discover all devices and ports on first load."""
        try:
            await self.api.authenticate()
            locations = await self.api.get_map_locations()
        except CellgateAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CellgateConnectionError as err:
            raise UpdateFailed(str(err)) from err

        self._device_locations = []
        for location in locations:
            location_name = location.get("Description", "")
            for device in location.get("DeviceList", []):
                device_id = str(device.get("DeviceId", ""))
                # Note: API misspells "PropertyLocationId" as "ProertyLocaitonId"
                prop_loc_id = str(
                    device.get("ProertyLocaitonId", "")
                    or device.get("PropertyLocationId", "")
                )
                if device_id and prop_loc_id:
                    self._device_locations.append(
                        (device_id, prop_loc_id, location_name)
                    )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest device/port data."""
        if not self._device_locations:
            await self._async_setup()

        result: dict[str, Any] = {}
        for device_id, prop_loc_id, location_name in self._device_locations:
            try:
                devices = await self.api.get_devices_list(device_id, prop_loc_id)
            except CellgateAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except (CellgateConnectionError, CellgateApiError) as err:
                raise UpdateFailed(str(err)) from err

            device_desc = devices.get("description", "")
            hardware_type = devices.get("hardwareType", "")

            for port in devices.get("ports", []):
                port_id = str(port["id"])
                key = f"{device_id}_{port_id}"
                result[key] = {
                    "device_id": device_id,
                    "port_id": port_id,
                    "property_location_id": prop_loc_id,
                    "device_description": device_desc,
                    "port_description": port.get("description", ""),
                    "device_type": port.get("deviceType", ""),
                    "hardware_type": hardware_type,
                    "is_online": port.get("isOnline") == 1,
                    "last_state": port.get("lastState", "0"),
                    "map_location_name": location_name,
                }
        return result

    async def async_open_gate(self, device_id: str, port_id: str) -> None:
        """Send gate open command."""
        await self.api.open_gate(device_id, port_id)
