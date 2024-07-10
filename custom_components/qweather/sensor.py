from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Generic, TypeVar

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import CONF_NAME, EntityCategory, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import Coordinators, QWeatherConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: QWeatherConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinators: Coordinators = config_entry.runtime_data
    async_add_entities(
        [
            QSensor(
                coordinators.minutely_precipitation,
                SensorEntityDescription(
                    key="minutely_precipitation_summary",
                    entity_category=EntityCategory.DIAGNOSTIC,
                    icon="mdi:weather-pouring",
                    translation_key="minutely_precipitation_summary",
                ),
                config_entry,
                lambda data: data.get("summary") if data else None,
            )
        ]
    )


_DataT = TypeVar("_DataT")


class QSensor(CoordinatorEntity, SensorEntity, Generic[_DataT]):
    _attr_has_entity_name: bool = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[_DataT],
        description: SensorEntityDescription,
        config_entry: QWeatherConfigEntry,
        value_func: Callable[[_DataT], StateType | date | datetime | Decimal],
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.value_func = value_func

        self._attr_unique_id = f"{config_entry.unique_id}_{description.key}"
        self.entity_id = (
            f"{Platform.SENSOR}.{config_entry.data[CONF_NAME]}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.unique_id)}
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
