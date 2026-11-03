"""Binary sensors: online, running, fault."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    KIND_BOREWELL,
    KIND_MOTOR,
    KIND_TANK,
    KIND_VALVE,
    STATUS_MALFUNCTION,
    STATUS_OFFLINE,
)
from .coordinator import WaltrConfigEntry
from .entity import WaltrEntity


@dataclass(frozen=True, kw_only=True)
class WaltrBinaryDescription(BinarySensorEntityDescription):
    is_on_fn: Callable[[dict[str, Any]], bool | None]


# Tanks report 0=offline / 1=online; controllers use 2 for offline.
TANK_ONLINE = WaltrBinaryDescription(
    key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
    is_on_fn=lambda d: d.get("status") == 1,
)
CONTROLLER_ONLINE = WaltrBinaryDescription(
    key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
    is_on_fn=lambda d: d.get("status") != STATUS_OFFLINE,
)
FAULT = WaltrBinaryDescription(
    key="fault",
    device_class=BinarySensorDeviceClass.PROBLEM,
    is_on_fn=lambda d: d.get("status") == STATUS_MALFUNCTION,
)
RUNNING = WaltrBinaryDescription(
    key="running",
    device_class=BinarySensorDeviceClass.RUNNING,
    is_on_fn=lambda d: d.get("status") == 1,
)
AUTOMATED = WaltrBinaryDescription(
    key="automated",
    entity_category=EntityCategory.DIAGNOSTIC,
    is_on_fn=lambda d: bool(d.get("automated")),
)

BINARY_SENSORS = {
    KIND_TANK: (TANK_ONLINE,),
    KIND_MOTOR: (RUNNING, CONTROLLER_ONLINE, FAULT, AUTOMATED),
    KIND_BOREWELL: (RUNNING, CONTROLLER_ONLINE, FAULT),
    KIND_VALVE: (CONTROLLER_ONLINE, FAULT, AUTOMATED),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaltrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WaltrBinarySensor(coordinator, kind, device_id, description)
        for kind, descriptions in BINARY_SENSORS.items()
        for device_id in coordinator.data.devices[kind]
        for description in descriptions
    )


class WaltrBinarySensor(WaltrEntity, BinarySensorEntity):
    entity_description: WaltrBinaryDescription

    def __init__(self, coordinator, kind, device_id, description) -> None:
        super().__init__(coordinator, kind, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.device_data)
