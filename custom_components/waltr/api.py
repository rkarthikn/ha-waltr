"""Small async client for the Waltr REST API (https://api.waltr.in/docs/api/)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

from .const import API_BASE, MIN_REQUEST_GAP


class WaltrError(Exception):
    """Generic API failure."""


class WaltrAuthError(WaltrError):
    """The token was rejected."""


class WaltrPremiumError(WaltrError):
    """The call needs a Waltr Premium plan."""


class WaltrCommandRefused(WaltrError):
    """Waltr refused a control command (tank full, offline, dry run ...)."""


class WaltrApi:
    """Thin wrapper around the endpoints this integration uses."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._headers = {
            "Authorization": f"TOKEN {token}",
            "Accept": "application/json",
        }
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> Any:
        async with self._lock:
            wait = MIN_REQUEST_GAP - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with self._session.request(
                    method,
                    f"{API_BASE}{path}",
                    headers=self._headers,
                    json=json,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    self._last_request = time.monotonic()
                    try:
                        body = await resp.json(content_type=None)
                    except ValueError:
                        body = None
                    if resp.status == 401:
                        raise WaltrAuthError("Token rejected")
                    if resp.status == 403:
                        raise WaltrPremiumError(_detail(body) or "Not allowed for this plan")
                    if resp.status in (400, 422):
                        raise WaltrCommandRefused(_detail(body) or f"HTTP {resp.status}")
                    if resp.status == 404:
                        return None
                    if resp.status >= 400:
                        raise WaltrError(f"HTTP {resp.status}: {_detail(body)}")
                    return body
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise WaltrError(f"Cannot reach Waltr: {err}") from err

    async def locations(self) -> list[dict[str, Any]]:
        """Locations owned by the user, with their sub-locations."""
        try:
            return _items(await self._request("GET", "/location"))
        except WaltrPremiumError as err:
            # Reading locations needs no plan, so a 403 here means a bad token.
            raise WaltrAuthError(str(err)) from err

    async def devices(self, location_id: int, kind: str) -> list[dict[str, Any]]:
        """Tanks, motors, borewells or valves in one location."""
        return _items(await self._request("GET", f"/location/{location_id}/{kind}"))

    async def daily(self, kind: str, device_id: str, date: str) -> Any:
        """One day's history for a device (date is YYYY-MM-DD, IST)."""
        return await self._request("GET", f"/daily/{kind}/{device_id}/{date}")

    async def control_borewell(self, device_id: str, timer: int) -> None:
        await self._request("POST", "/borewell/control", {"id": device_id, "timer": timer})

    async def control_motor(
        self, device_id: str, *, status: bool | None = None, timer: int | None = None
    ) -> None:
        payload: dict[str, Any] = {"id": device_id}
        if status is not None:
            payload["status"] = status
        if timer is not None:
            payload["timer"] = timer
        await self._request("POST", "/motor/control", payload)

    async def control_valve(self, device_id: str, status: bool) -> None:
        await self._request("POST", "/valve/control", {"id": device_id, "status": status})

    async def set_borewell_automated(self, device_id: str, automated: bool) -> None:
        await self._request(
            "PATCH", f"/borewell/config/{device_id}", {"automated": automated}
        )


def _items(body: Any) -> list[dict[str, Any]]:
    """Endpoints return either a bare list or {"data": [...]}."""
    if isinstance(body, dict):
        body = body.get("data", [])
    return [item for item in body or [] if isinstance(item, dict)]


def _detail(body: Any) -> str:
    if isinstance(body, dict):
        for key in ("detail", "message", "error"):
            if body.get(key):
                return str(body[key])
    return ""
