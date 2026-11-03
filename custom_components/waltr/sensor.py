"""Sensors for Waltr tanks, motors, borewells and valves."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfRatio,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    KIND_BOREWELL,
    KIND_MOTOR,
    KIND_TANK,
    KIND_VALVE,
    PUMP_STATUS,
    TDS_UNAVAILABLE,
    VALVE_STATUS,
)
from .coordinator import WaltrConfigEntry
from .entity import WaltrEntity


@dataclass(frozen=True, kw_only=True)
class WaltrSensorDescription(SensorEntityDescription):
    """value_fn gets (device, daily) and returns the state."""

    value_fn: Callable[[dict[str, Any], Any], Any]
    exists_fn: Callable[[dict[str, Any]], bool] = lambda _: True


def _get(data: dict[str, Any], *path: str) -> Any:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _kl_to_litres(value: Any) -> float | None:
    return None if value is None else round(float(value) * 1000, 1)


def _timestamp(value: Any) -> datetime | None:
    return dt_util.parse_datetime(value) if isinstance(value, str) else None


def _tds(device: dict[str, Any], _daily: Any) -> int | None:
    value = device.get("tds")
    return None if value in (None, TDS_UNAVAILABLE) else value


def _records(daily: Any) -> list[dict[str, Any]]:
    return [r for r in daily if isinstance(r, dict)] if isinstance(daily, list) else []


def _energy_today(_device: dict[str, Any], daily: Any) -> float | None:
    values = [r["kwh"] for r in _records(daily) if isinstance(r.get("kwh"), (int, float))]
    return round(sum(values), 3) if values else None


def _last_command_by(_device: dict[str, Any], daily: Any) -> str | None:
    records = _records(daily)
    if not records:
        return None
    by = records[-1].get("by")
    return by or "device panel"


BATTERY = (
    WaltrSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, _: _get(d, "battery", "pc"),
        exists_fn=lambda d: "battery" in d,
    ),
    WaltrSensorDescription(
        key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d, _: _get(d, "battery", "vb"),
        exists_fn=lambda d: "battery" in d,
    ),
)

LAST_UPDATED = WaltrSensorDescription(
    key="last_updated",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    value_fn=lambda d, _: _timestamp(d.get("last_updated_at")),
)

TANK_SENSORS = (
    WaltrSensorDescription(
        key="water_level_percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, _: _get(d, "current_water_level", "water_level_in_percentage"),
    ),
    WaltrSensorDescription(
        key="water_volume",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, _: _kl_to_litres(_get(d, "current_water_level", "water_level_in_KL")),
    ),
    WaltrSensorDescription(
        key="water_height",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d, _: _get(d, "current_water_level", "water_level"),
    ),
    WaltrSensorDescription(
        key="capacity",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, _: d.get("total_volume"),
    ),
    WaltrSensorDescription(
        key="tds",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_tds,
        exists_fn=lambda d: bool(d.get("is_tds_available")),
    ),
    WaltrSensorDescription(
        key="inflow_today",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda _, daily: _kl_to_litres(_get(daily, "summary", "inflow")),
    ),
    WaltrSensorDescription(
        key="outflow_today",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda _, daily: _kl_to_litres(_get(daily, "summary", "outflow")),
    ),
    WaltrSensorDescription(
        key="tanker_today",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda _, daily: _kl_to_litres(_get(daily, "summary", "tanker_volume")),
        exists_fn=lambda d: bool(d.get("has_tanker")),
    ),
    *BATTERY,
    LAST_UPDATED,
)

PUMP_SENSORS = (
    WaltrSensorDescription(
        key="pump_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(PUMP_STATUS.values()),
        value_fn=lambda d, _: PUMP_STATUS.get(d.get("status")),
    ),
    WaltrSensorDescription(
        key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_energy_today,
        exists_fn=lambda d: bool(d.get("is_three_phase")),
    ),
    WaltrSensorDescription(
        key="last_command_by",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_last_command_by,
    ),
    LAST_UPDATED,
)

VALVE_SENSORS = (
    WaltrSensorDescription(
        key="valve_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(VALVE_STATUS.values()),
        value_fn=lambda d, _: VALVE_STATUS.get(d.get("status")),
    ),
    *BATTERY,
    LAST_UPDATED,
)

SENSORS = {
    KIND_TANK: TANK_SENSORS,
    KIND_MOTOR: PUMP_SENSORS,
    KIND_BOREWELL: PUMP_SENSORS,
    KIND_VALVE: VALVE_SENSORS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaltrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WaltrSensor(coordinator, kind, device_id, description)
        for kind, descriptions in SENSORS.items()
        for device_id, device in coordinator.data.devices[kind].items()
        for description in descriptions
        if description.exists_fn(device)
    )


class WaltrSensor(WaltrEntity, SensorEntity):
    entity_description: WaltrSensorDescription

    def __init__(self, coordinator, kind, device_id, description) -> None:
        super().__init__(coordinator, kind, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.device_data, self.daily)
