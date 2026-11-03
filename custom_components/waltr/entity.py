"""Base entity shared by every Waltr platform."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import WaltrCommandRefused, WaltrError, WaltrPremiumError
from .const import DOMAIN, MANUFACTURER, MODELS, STATUS_OFFLINE
from .coordinator import WaltrCoordinator


class WaltrEntity(CoordinatorEntity[WaltrCoordinator]):
    """An entity attached to one Waltr device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: WaltrCoordinator, kind: str, device_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self.kind = kind
        self.device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_translation_key = key
        info = self.device_data
        location = coordinator.data.locations.get(info.get("location_id"))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=info.get("name") or info.get("device_id"),
            manufacturer=MANUFACTURER,
            model=MODELS.get(info.get("device_type"), info.get("device_type")),
            serial_number=info.get("device_id"),
            sw_version=info.get("version"),
            suggested_area=location,
        )

    @property
    def device_data(self) -> dict[str, Any]:
        return self.coordinator.device(self.kind, self.device_id) or {}

    @property
    def daily(self) -> Any:
        return self.coordinator.data.daily.get(self.device_id)

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.device(self.kind, self.device_id))


class WaltrControlEntity(WaltrEntity):
    """Entities that send commands; unavailable while the controller is offline."""

    @property
    def available(self) -> bool:
        return super().available and self.device_data.get("status") != STATUS_OFFLINE

    async def _send(self, command) -> None:
        try:
            await command
        except WaltrPremiumError as err:
            raise HomeAssistantError(
                f"Waltr refused the command; controls need a Waltr Premium plan ({err})"
            ) from err
        except WaltrCommandRefused as err:
            raise HomeAssistantError(f"Waltr refused the command: {err}") from err
        except WaltrError as err:
            raise HomeAssistantError(f"Could not reach Waltr: {err}") from err
        self.coordinator.refresh_soon()
