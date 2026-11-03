"""Run-time setting used when a timer-based pump is switched on."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RUN_MINUTES, KIND_BOREWELL, KIND_MOTOR
from .coordinator import WaltrConfigEntry
from .entity import WaltrEntity


def is_timer_based(kind: str, device: dict) -> bool:
    """Borewells always run on a timer; motors unless they are event based."""
    return kind == KIND_BOREWELL or not device.get("is_event_based")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaltrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WaltrRunTime(coordinator, kind, device_id)
        for kind in (KIND_MOTOR, KIND_BOREWELL)
        for device_id, device in coordinator.data.devices[kind].items()
        if is_timer_based(kind, device)
    )


class WaltrRunTime(WaltrEntity, RestoreNumber):
    """How long the pump runs when its switch is turned on. Stored in HA only."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 720
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator, kind, device_id) -> None:
        super().__init__(coordinator, kind, device_id, "run_time")
        self._attr_native_value = DEFAULT_RUN_MINUTES

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) and last.native_value:
            self._attr_native_value = last.native_value
        self.coordinator.run_minutes[self.device_id] = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.coordinator.run_minutes[self.device_id] = value
        self.async_write_ha_state()
