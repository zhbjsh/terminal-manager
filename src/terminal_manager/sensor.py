from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field, replace
import re
from typing import TYPE_CHECKING, Any, Self

from .errors import InvalidSensorError
from .event import Event
from .helpers import name_to_key

if TYPE_CHECKING:
    from .collection import Collection
    from .command import Command, DynamicData
    from .manager import Manager

TRUE_STRINGS = ["true", "enabled", "on", "active", "1"]
FALSE_STRINGS = ["false", "disabled", "off", "inactive", "0"]


@dataclass
class Sensor:
    name: str | None = None
    key: str | None = None
    _: KW_ONLY
    dynamic: bool = False
    unit: str | None = None
    renderer: Callable[[str], str] | None = None
    command_set: Command | None = None
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        self.id = None
        self.name = self.name.strip() if self.name else None
        self.key = self.key.strip() if self.key else name_to_key(self.name)
        self.value: Any | None = None
        self.last_known_value: Any | None = None
        self.child_sensors: list[Sensor] = []
        self.on_update = Event()
        self.on_child_add = Event()
        self.on_child_remove = Event()
        self._linked_sensors = set()

    @property
    def controllable(self) -> bool:
        return self.command_set is not None

    @property
    def child_sensors_by_key(self) -> dict[str, Self]:
        return {child.key: child for child in self.child_sensors}

    @property
    def linked_sensors(self) -> set[str]:
        return self._linked_sensors

    def _get_control_command(self, _: Any) -> Command | None:
        return self.command_set

    def _make_child(self, dynamic_data: DynamicData) -> Self:
        child = replace(
            self,
            name=dynamic_data.name,
            key=dynamic_data.key,
            dynamic=False,
        )
        child.id = dynamic_data.id
        return child

    def _add_child(self, child: Sensor) -> None:
        self.child_sensors.append(child)
        self.on_child_add.notify(self, child)

    def _remove_child(self, child: Sensor) -> None:
        self.child_sensors.remove(child)
        self.on_child_remove.notify(self, child)

    def _render(self, data: str) -> str:
        if self.renderer:
            data = self.renderer(data)

        return data.strip()

    def _convert(self, value_string: str) -> Any:
        return value_string

    def _validate(self, value: Any) -> None: ...

    def _update_value(self, manager: Manager, data: str | None) -> None:
        if data is None:
            self.value = None
            manager.logger.debug("%s: %s => %s", manager.name, self.key, self.value)
            return

        try:
            value_string = self._render(data)
            value = self._convert(value_string)
            self._validate(value)
        except Exception as exc:  # noqa: BLE001
            self.value = None
            manager.logger.debug(
                "%s: %s => %s (%s)", manager.name, self.key, self.value, exc
            )
            return

        self.value = self.last_known_value = value
        manager.logger.debug("%s: %s => %s", manager.name, self.key, self.value)

    def _update_child_sensors(
        self,
        manager: Manager,
        data: list[DynamicData] | None,
    ) -> None:
        if data is None:
            for child in self.child_sensors:
                child.update(manager, None)
            return

        dynamic_data_by_key = {dynamic_data.key: dynamic_data for dynamic_data in data}

        for dynamic_data in data:
            if dynamic_data.key not in self.child_sensors_by_key:
                child = self._make_child(dynamic_data)
                self._add_child(child)

        for child in self.child_sensors:
            if child.key in dynamic_data_by_key:
                dynamic_data = dynamic_data_by_key[child.key]
                child.update(manager, dynamic_data.data)
            else:
                self._remove_child(child)

    def check(self, collection: Collection) -> None:
        """Check configuration.

        Raises:
            InvalidSensorError

        """
        for key in self.linked_sensors:
            if not collection.sensors_by_key.get(key):
                raise InvalidSensorError(self.key, f"'{key}' not found")

    def update(self, manager: Manager, data: str | list[DynamicData] | None) -> None:
        """Update and notify `on_update` subscribers."""
        if self.dynamic:
            self.value = self.last_known_value = None
            self._update_child_sensors(manager, data)
        else:
            self.child_sensors = []
            self._update_value(manager, data)

        self.on_update.notify(self)

    async def async_set(self, manager: Manager, value: Any) -> None:
        """Set a value.

        Raises:
            TypeError
            ValueError
            CommandError

        """
        self._validate(value)
        command = self._get_control_command(value)

        if command is None or value == self.value:
            return

        await manager.async_execute_command(
            command, variables={"id": self.id, "value": value}
        )


@dataclass
class TextSensor(Sensor):
    _: KW_ONLY
    minimum: int | None = None
    maximum: int | None = None
    pattern: str | None = None
    options: list[Any] | None = None

    def _convert(self, value_string: str) -> str:
        if value_string == "":
            raise ValueError("String is empty")

        return value_string

    def _validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{value} is {type(value)} and not {str}")

        if self.minimum and len(value) < self.minimum:
            raise ValueError(f"{value} is shorter then {self.minimum}")

        if self.maximum and len(value) > self.maximum:
            raise ValueError(f"{value} is longer then {self.maximum}")

        if self.pattern and not re.fullmatch(self.pattern, value):
            raise ValueError(f"{value} doesn't match {self.pattern}")

        if self.options and value not in self.options:
            raise ValueError(f"{value} is not in {self.options}")


@dataclass
class NumberSensor(Sensor):
    _: KW_ONLY
    float: bool = False
    minimum: int | float | None = None
    maximum: int | float | None = None

    def _convert(self, value_string: str) -> int | float:
        if self.float:
            return float(value_string)

        return int(float(value_string))

    def _validate(self, value: Any) -> None:
        if self.float and not isinstance(value, float):
            raise TypeError(f"{value} is {type(value)} and not {float}")

        if not self.float and not isinstance(value, int):
            raise TypeError(f"{value} is {type(value)} and not {int}")

        if self.minimum and value < self.minimum:
            raise ValueError(f"{value} is smaller then {self.minimum}")

        if self.maximum and value > self.maximum:
            raise ValueError(f"{value} is bigger then {self.maximum}")


@dataclass
class BinarySensor(Sensor):
    _: KW_ONLY
    command_on: Command | None = None
    command_off: Command | None = None
    payload_on: str | None = None
    payload_off: str | None = None

    @property
    def controllable(self) -> bool:
        if self.command_on and self.command_off:
            return True

        return super().controllable

    def _get_control_command(self, value: Any) -> Command | None:
        if self.command_on and value is True:
            return self.command_on

        if self.command_off and value is False:
            return self.command_off

        return self.command_set

    def _convert(self, value_string: str) -> bool:
        if self.payload_on:
            if value_string == self.payload_on:
                return True
            if not self.payload_off:
                return False

        if self.payload_off:
            if value_string == self.payload_off:
                return False
            if not self.payload_on:
                return True

        if value_string.lower() in TRUE_STRINGS:
            return True

        if value_string.lower() in FALSE_STRINGS:
            return False

        raise ValueError(f"Can't generate bool from {value_string}")

    def _validate(self, value: Any) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"{value} is {type(value)} and not {bool}")


@dataclass
class VersionSensor(Sensor):
    _: KW_ONLY
    latest: str | None = None

    @property
    def linked_sensors(self) -> set[str]:
        if key := self.latest:
            return {*self._linked_sensors, key}

        return self._linked_sensors

    def _convert(self, value_string: str) -> str:
        if value_string == "":
            raise ValueError("String is empty")

        return value_string

    def _validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{value} is {type(value)} and not {str}")

    def _make_child(self, dynamic_data: DynamicData) -> Self:
        child = super()._make_child(dynamic_data)

        if key := self.latest:
            child.latest = f"{key}_{name_to_key(child.id)}"

        return child

    def check(self, collection: Collection) -> None:
        super().check(collection)

        if not (key := self.latest):
            return

        sensor = collection.sensors_by_key[key]

        if not isinstance(sensor, VersionSensor):
            raise InvalidSensorError(self.key, f"'{key}' is not a version sensor")

        if sensor.latest:
            raise InvalidSensorError(self.key, f"'{key}' has 'latest' attribute")

        if sensor.command_set:
            raise InvalidSensorError(self.key, f"'{key}' has 'command_set' attribute")
