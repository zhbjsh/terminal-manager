from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field, replace
from typing import TYPE_CHECKING, Any

from .event import Event
from .helpers import name_to_key

if TYPE_CHECKING:
    from . import Manager
    from .command import Command

TRUE_STRINGS = ["true", "enabled", "on", "active", "1"]
FALSE_STRINGS = ["false", "disabled", "off", "inactive", "0"]


@dataclass
class Sensor:
    name: str | None = None
    key: str | None = None
    _: KW_ONLY
    dynamic: bool = False
    separator: str | None = None
    unit: str | None = None
    renderer: Callable[[str], str] | None = None
    command_set: Command | None = None
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        self.id = None
        self.key = self.key or name_to_key(self.name)
        self.value: Any | None = None
        self.last_known_value: Any | None = None
        self.child_sensors: list[Sensor] = []
        self.on_update = Event()
        self.on_child_added = Event()
        self.on_child_removed = Event()

    @property
    def controllable(self) -> bool:
        return self.command_set is not None

    @property
    def child_sensors_by_key(self) -> dict[str, Sensor]:
        return {child.key: child for child in self.child_sensors}

    def _get_control_command(self, _: Any) -> Command | None:
        return self.command_set

    def _add_child(self, child: Sensor) -> None:
        self.child_sensors.append(child)
        self.on_child_added.notify(self, child)

    def _remove_child(self, child: Sensor) -> None:
        self.child_sensors.remove(child)
        self.on_child_removed.notify(self, child)

    def _render(self, data: str) -> str:
        if self.renderer:
            data = self.renderer(data)

        return data.strip()

    def _convert(self, value_string: str) -> Any:
        return value_string

    def _validate(self, value: Any) -> None:
        ...

    def _update_value(self, manager: Manager, data: str | None) -> None:
        if data is None:
            self.value = None
            manager.logger.debug("%s: %s => %s", manager.name, self.key, self.value)
            return

        try:
            value_string = self._render(data)
            value = self._convert(value_string)
            self._validate(value)
        except Exception as exc:  # pylint: disable=broad-except
            self.value = None
            manager.logger.debug(
                "%s: %s => %s (%s)", manager.name, self.key, self.value, exc
            )
            return

        self.value = self.last_known_value = value
        manager.logger.debug("%s: %s => %s", manager.name, self.key, self.value)

    def _update_child_sensors(self, manager: Manager, data: list[str] | None) -> None:
        if data is None:
            for child in self.child_sensors:
                child.update(manager, None)
            return

        dynamic_data_list = [
            DynamicData(self.name, self.key, *fields)
            for fields in (line.split(self.separator, 2) for line in data)
            if len(fields) >= 2
        ]

        dynamic_data_by_key = {
            dynamic_data.key: dynamic_data for dynamic_data in dynamic_data_list
        }

        for key, dynamic_data in dynamic_data_by_key.items():
            if key not in self.child_sensors_by_key:
                child = replace(
                    self,
                    name=dynamic_data.name,
                    key=dynamic_data.key,
                    dynamic=False,
                    separator=None,
                )
                child.id = dynamic_data.id
                self._add_child(child)

        for child in self.child_sensors:
            if child.key in dynamic_data_by_key:
                dynamic_data = dynamic_data_by_key[child.key]
                child.update(manager, dynamic_data.data)
            else:
                self._remove_child(child)

    def update(self, manager: Manager, data: Any) -> None:
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


class DynamicData:
    def __init__(
        self,
        parent_name: str | None,
        parent_key: str,
        id_field: str,
        data_field: str,
        name_field: str | None = None,
    ) -> None:
        self.id = id_field.strip()
        name = name_field.strip() if name_field else self.id
        self.key = f"{parent_key}_{name_to_key(name)}"
        self.name = f"{parent_name} {name}" if parent_name else name
        self.data = data_field
