"""Waltr V valve controllers (Waltr Premium)."""

from __future__ import annotations

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import KIND_VALVE
from .coordinator import WaltrConfigEntry
from .entity import WaltrControlEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaltrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WaltrValve(coordinator, KIND_VALVE, device_id)
        for device_id in coordinator.data.devices[KIND_VALVE]
    )


class WaltrValve(WaltrControlEntity, ValveEntity):
    """Open or close a valve. The controller can take up to 5 minutes to act."""

    _attr_device_class = ValveDeviceClass.WATER
    _attr_reports_position = False
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def __init__(self, coordinator, kind, device_id) -> None:
        super().__init__(coordinator, kind, device_id, "valve")

    @property
    def is_closed(self) -> bool | None:
        status = self.device_data.get("status")
        return {0: True, 1: False}.get(status)

    async def async_open_valve(self) -> None:
        await self._send(self.coordinator.api.control_valve(self.device_id, True))

    async def async_close_valve(self) -> None:
        await self._send(self.coordinator.api.control_valve(self.device_id, False))
