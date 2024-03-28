import logging
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .core.q_client import QWeatherClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client: QWeatherClient = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            QSensor(
                client.minutely_precipitation_coordinator,
                SensorEntityDescription(
                    key="minutely_precipitation_summary",
                    entity_category=EntityCategory.DIAGNOSTIC,
                    icon="mdi:weather-pouring",
                    translation_key="minutely_precipitation_summary",
                ),
                config_entry.unique_id,
                lambda data: data.get("summary") if data else None,
            )
        ]
    )


_DataT = TypeVar("_DataT")


class QSensor(CoordinatorEntity, SensorEntity, Generic[_DataT]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[_DataT],
        description: SensorEntityDescription,
        config_entry_unique_id: str,
        value_func: Callable[[_DataT], StateType | date | datetime | Decimal],
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.value_func = value_func
        self._attr_unique_id = f"{config_entry_unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry_unique_id)},
        )

        self._async_update_attrs(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._async_update_attrs(self.coordinator.data)
        super()._handle_coordinator_update()

    @callback
    def _async_update_attrs(self, data: _DataT):
        self._attr_native_value = self.value_func(data)
