"""Cellgate API client."""

from __future__ import annotations

import base64
import json
import time

import aiohttp

from .const import API_PREFIX, APP_TYPE, APP_VERSION, BASE_URL


class CellgateAuthError(Exception):
    """Authentication failed."""


class CellgateConnectionError(Exception):
    """Connection to Cellgate failed."""


class CellgateApiError(Exception):
    """API returned an error."""


class CellgateApiClient:
    """Client for the Cellgate REST API.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None
        self._token_expiry: float = 0
        self._auth_failed: bool = False

    async def authenticate(self) -> dict:
        """Login and obtain JWT token.
        """
        headers = {
            "AuthUsername": self._username,
            "AuthPassword": self._password,
            "DeviceToken": "",
            "AppVersion": APP_VERSION,
            "AppType": APP_TYPE,
            "VoipToken": "",
        }
        data = await self._request_cZf("Login", headers)
        if not data.get("isSuccess"):
            self._auth_failed = True
            raise CellgateAuthError(data.get("message", "Login failed"))
        self._auth_failed = False
        self._token = data["token"]
        self._token_expiry = self._decode_token_expiry(self._token)
        return data

    async def get_map_locations(self) -> list[dict]:
        """Get communities and devices.
        """
        await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self._token}",
            "AppVersion": APP_VERSION,
        }
        data = await self._request_cZf("GetMapLocationList", headers)
        if not data.get("isSuccess"):
            raise CellgateApiError(data.get("message", "Failed to get locations"))
        return data.get("data", {}).get("mapLocations", [])

    async def get_devices_list(
        self, device_id: str, property_location_id: str
    ) -> dict:
        """Get device details with ports.
        """
        body = {
            "DeviceID": device_id,
            "PropertyLocationID": property_location_id,
        }
        data = await self._request_EDf("DevicesList", body)
        if not data.get("isSuccess"):
            raise CellgateApiError(data.get("message", "Failed to get devices"))
        return data.get("data", {}).get("devices", {})

    async def open_gate(self, device_id: str, port_id: str) -> dict:
        """Open a gate (momentary).
        """
        body = {
            "GateCommand": "MOMENTARY_OPEN",
            "Hours": "0",
            "DeviceID": device_id,
            "PortID": port_id,
            "AccessCode": "1",
        }
        data = await self._request_EDf("GateCommand", body)
        if not data.get("isSuccess"):
            msg = (
                data.get("data", {}).get("result")
                or data.get("message")
                or "Gate command failed"
            )
            raise CellgateApiError(msg)
        return data

    async def _request_cZf(self, endpoint: str, headers: dict) -> dict:
        """cZf http request pattern: all fields as HTTP headers, no body.
        """
        url = f"{BASE_URL}/{API_PREFIX}/{endpoint}"
        try:
            async with self._session.post(url, headers=headers) as resp:
                if resp.status == 401:
                    raise CellgateAuthError("Unauthorized")
                resp.raise_for_status()
                return await resp.json()
        except CellgateAuthError:
            raise
        except aiohttp.ClientError as err:
            raise CellgateConnectionError(
                f"Connection error: {err}"
            ) from err

    async def _request_EDf(self, endpoint: str, body: dict) -> dict:
        """EDf http request pattern: Bearer auth header + form-urlencoded body.
        """
        await self._ensure_token()
        url = f"{BASE_URL}/{API_PREFIX}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            async with self._session.post(
                url, headers=headers, data=body
            ) as resp:
                if resp.status == 401:
                    self._token = None
                    raise CellgateAuthError("Token expired")
                resp.raise_for_status()
                return await resp.json()
        except CellgateAuthError:
            raise
        except aiohttp.ClientError as err:
            raise CellgateConnectionError(
                f"Connection error: {err}"
            ) from err

    async def _ensure_token(self) -> None:
        """Ensure we have a valid token, re-authenticating if needed.

        If a previous login attempt failed (bad credentials), we refuse
        to retry automatically. The reauth config flow must fix the
        credentials and call authenticate() directly to clear the flag.
        """
        if self._token and time.time() < self._token_expiry - 86400:
            return
        if self._auth_failed:
            raise CellgateAuthError(
                "Authentication previously failed — not retrying automatically"
            )
        await self.authenticate()

    @staticmethod
    def _decode_token_expiry(token: str) -> float:
        """Decode JWT exp claim without verifying signature."""
        try:
            payload_b64 = token.split(".")[1]
            # Add padding
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return float(payload.get("exp", 0))
        except (IndexError, ValueError, json.JSONDecodeError):
            return 0
