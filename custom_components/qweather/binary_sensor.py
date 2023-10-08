import logging
from collections.abc import Callable, MutableMapping
from typing import Any, Generic, TypeVar

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN, WeatherWarning
from .q_client import QWeatherClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client: QWeatherClient = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            QWeatherWarningBinarySensor(client, config_entry.unique_id),
        ]
    )


_DataT = TypeVar("_DataT")


class QBinarySensor(CoordinatorEntity, BinarySensorEntity, Generic[_DataT]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[_DataT],
        description: BinarySensorEntityDescription,
        config_entry_unique_id: str,
        value_func: Callable[[_DataT], bool | None],
    ):
        super().__init__(coordinator)
        self.entity_description = description
        self.value_func = value_func
        self._attr_unique_id = f"{config_entry_unique_id}_{description.key}"

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

    def __init__(self, client: QWeatherClient, config_entry_unique_id: str):
        super().__init__(
            client.warning_now_coordinator,
            BinarySensorEntityDescription(
                key="weather_warning",
                device_class=BinarySensorDeviceClass.SAFETY,
                translation_key="weather_warning",
            ),
            config_entry_unique_id,
            lambda data: True if data else False,
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
