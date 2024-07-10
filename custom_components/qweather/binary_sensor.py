from collections.abc import Callable, MutableMapping
import logging
from typing import Any, Generic, TypeVar

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import CONF_NAME, EntityCategory, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import Coordinators, QWeatherConfigEntry
from .const import DOMAIN, WeatherWarning

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: QWeatherConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinators: Coordinators = config_entry.runtime_data
    async_add_entities(
        [
            QWeatherWarningBinarySensor(coordinators.warning_now, config_entry),
        ]
    )


_DataT = TypeVar("_DataT")


class QBinarySensor(CoordinatorEntity, BinarySensorEntity, Generic[_DataT]):
    _attr_has_entity_name: bool = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[_DataT],
        description: BinarySensorEntityDescription,
        config_entry: QWeatherConfigEntry,
        value_func: Callable[[_DataT], bool | None],
    ):
        super().__init__(coordinator)
        self.entity_description = description
        self.value_func = value_func
        self._attr_unique_id = f"{config_entry.unique_id}_{description.key}"
        self.entity_id = (
            f"{Platform.BINARY_SENSOR}.{config_entry.data[CONF_NAME]}.{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.unique_id)}
        )
        self._async_update_attrs(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._async_update_attrs(self.coordinator.data)
        super()._handle_coordinator_update()

    @callback
    def _async_update_attrs(self, data: _DataT):
        self._attr_is_on = self.value_func(data)


class QWeatherWarningBinarySensor(QBinarySensor):
    _attr_extra_state_attributes: MutableMapping[str, Any]

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[WeatherWarning],
        config_entry: QWeatherConfigEntry,
    ):
        super().__init__(
            coordinator,
            BinarySensorEntityDescription(
                key="weather_warning",
                entity_category=EntityCategory.DIAGNOSTIC,
                device_class=BinarySensorDeviceClass.SAFETY,
                translation_key="weather_warning",
            ),
            config_entry,
            bool,
        )

    @callback
    def _async_update_attrs(self, data: list[WeatherWarning]):
        super()._async_update_attrs(data)
        self._attr_extra_state_attributes = {
            "warning": [
                {
                    "title": warning.get("title"),
                    "text": warning.get("text"),
                }
                for warning in data
            ],
        }
