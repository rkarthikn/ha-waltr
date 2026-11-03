"""Pump switches and the borewell schedule switch (Waltr Premium)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RUN_MINUTES, KIND_BOREWELL, KIND_MOTOR
from .coordinator import WaltrConfigEntry
from .entity import WaltrControlEntity
from .number import is_timer_based


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaltrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = [
        WaltrPumpSwitch(coordinator, kind, device_id)
        for kind in (KIND_MOTOR, KIND_BOREWELL)
        for device_id in coordinator.data.devices[kind]
    ]
    entities += [
        WaltrScheduleSwitch(coordinator, KIND_BOREWELL, device_id)
        for device_id in coordinator.data.devices[KIND_BOREWELL]
    ]
    async_add_entities(entities)


class WaltrPumpSwitch(WaltrControlEntity, SwitchEntity):
    """Starts or stops a motor or borewell pump."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, kind, device_id) -> None:
        super().__init__(coordinator, kind, device_id, "pump")

    @property
    def is_on(self) -> bool:
        return self.device_data.get("status") == 1

    def _timer_seconds(self) -> int:
        minutes = self.coordinator.run_minutes.get(self.device_id, DEFAULT_RUN_MINUTES)
        return max(60, int(minutes * 60))

    async def async_turn_on(self, **kwargs: Any) -> None:
        api = self.coordinator.api
        if self.kind == KIND_BOREWELL:
            await self._send(api.control_borewell(self.device_id, self._timer_seconds()))
        elif is_timer_based(self.kind, self.device_data):
            await self._send(api.control_motor(self.device_id, timer=self._timer_seconds()))
        else:
            await self._send(api.control_motor(self.device_id, status=True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        api = self.coordinator.api
        if self.kind == KIND_BOREWELL:
            await self._send(api.control_borewell(self.device_id, 0))
        elif is_timer_based(self.kind, self.device_data):
            await self._send(api.control_motor(self.device_id, timer=0))
        else:
            await self._send(api.control_motor(self.device_id, status=False))


class WaltrScheduleSwitch(WaltrControlEntity, SwitchEntity):
    """Whether the borewell follows the schedule set in the Waltr app."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, kind, device_id) -> None:
        super().__init__(coordinator, kind, device_id, "schedule")

    @property
    def available(self) -> bool:
        # The schedule is a cloud setting; it can change while the pump is offline.
        return self.coordinator.last_update_success and bool(self.device_data)

    @property
    def is_on(self) -> bool:
        return bool(self.device_data.get("automated"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(self.coordinator.api.set_borewell_automated(self.device_id, True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(self.coordinator.api.set_borewell_automated(self.device_id, False))
