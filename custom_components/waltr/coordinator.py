"""Polls Waltr for every device and its daily totals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WaltrApi, WaltrAuthError, WaltrError
from .const import (
    DAILY_INTERVAL,
    DOMAIN,
    KIND_BOREWELL,
    KIND_MOTOR,
    KIND_TANK,
    KINDS,
    SCAN_INTERVAL,
    WALTR_TZ,
)

_LOGGER = logging.getLogger(__name__)

type WaltrConfigEntry = ConfigEntry[WaltrCoordinator]


@dataclass
class WaltrData:
    """Everything the entities read, keyed by device UUID."""

    devices: dict[str, dict[str, dict[str, Any]]] = field(
        default_factory=lambda: {kind: {} for kind in KINDS}
    )
    locations: dict[int, str] = field(default_factory=dict)
    daily: dict[str, Any] = field(default_factory=dict)


class WaltrCoordinator(DataUpdateCoordinator[WaltrData]):
    """One coordinator per Waltr account."""

    config_entry: WaltrConfigEntry

    def __init__(self, hass: HomeAssistant, entry: WaltrConfigEntry, api: WaltrApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        # Pump run time in minutes per device, set by the run-time number entity.
        self.run_minutes: dict[str, float] = {}
        self._daily_at: datetime | None = None
        self._daily_date: str | None = None

    async def _async_update_data(self) -> WaltrData:
        try:
            return await self._fetch()
        except WaltrAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WaltrError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch(self) -> WaltrData:
        data = WaltrData()
        for loc in await self.api.locations():
            data.locations[loc["id"]] = loc.get("name") or str(loc["id"])
            for sub in loc.get("under") or []:
                data.locations[sub["id"]] = sub.get("name") or str(sub["id"])

        # Devices can sit on a location or one of its sub-locations; the same
        # device may be listed on both, so key by UUID.
        for location_id in data.locations:
            for kind in KINDS:
                for device in await self.api.devices(location_id, kind):
                    data.devices[kind].setdefault(device["id"], device)

        today = dt_util.now(WALTR_TZ).date().isoformat()
        now = dt_util.utcnow()
        if (
            self._daily_at is None
            or self._daily_date != today
            or now - self._daily_at >= DAILY_INTERVAL
        ):
            data.daily = await self._fetch_daily(data, today)
            self._daily_at, self._daily_date = now, today
        elif self.data is not None:
            data.daily = self.data.daily
        return data

    async def _fetch_daily(self, data: WaltrData, today: str) -> dict[str, Any]:
        daily: dict[str, Any] = {}
        for kind in (KIND_TANK, KIND_MOTOR, KIND_BOREWELL):
            for device_id in data.devices[kind]:
                try:
                    daily[device_id] = await self.api.daily(kind, device_id, today)
                except WaltrAuthError:
                    raise
                except WaltrError as err:
                    # Daily history is a nice-to-have; keep the live readings.
                    _LOGGER.debug("Daily data for %s %s failed: %s", kind, device_id, err)
        return daily

    def device(self, kind: str, device_id: str) -> dict[str, Any] | None:
        return self.data.devices[kind].get(device_id)

    def refresh_soon(self) -> None:
        """Controllers take a while to report a new state; poll again shortly."""
        self.hass.loop.call_later(
            10, lambda: self.hass.async_create_task(self.async_request_refresh())
        )
