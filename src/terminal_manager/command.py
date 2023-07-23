from __future__ import annotations

import re as _re
from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
from string import Template
from time import time
from typing import TYPE_CHECKING

from .errors import CommandError
from .helpers import name_to_key
from .sensor import Sensor

if TYPE_CHECKING:
    from . import CommandOutput, Manager

SENSOR_DELIMITER = "&"
VARIABLE_DELIMITER = "@"
PLACEHOLDER_KEY = "_"


# Not needed anymore after python 3.11
class Template(Template):
    def get_identifiers(self):
        ids = []
        for mo in self.pattern.finditer(self.template):
            named = mo.group("named") or mo.group("braced")
            if named is not None and named not in ids:
                ids.append(named)
            elif (
                named is None
                and mo.group("invalid") is None
                and mo.group("escaped") is None
            ):
                raise ValueError("Unrecognized named group in pattern", self.pattern)
        return ids


class SensorTemplate(Template):
    delimiter = SENSOR_DELIMITER
    pattern = rf"""
    {_re.escape(delimiter)}{{(?:
      (?P<braced>{Template.idpattern})|
      (?P<invalid>)|
      (?P<named>)|
      (?P<escaped>)
    )}}
    """


class VariableTemplate(Template):
    delimiter = VARIABLE_DELIMITER
    pattern = rf"""
    {_re.escape(delimiter)}{{(?:
      (?P<braced>{Template.idpattern})|
      (?P<invalid>)|
      (?P<named>)|
      (?P<escaped>)
    )}}
    """


@dataclass
class Command:
    string: str
    _: KW_ONLY
    timeout: float | None = None
    renderer: Callable[[str], str] | None = None

    @property
    def required_variables(self) -> set[str]:
        return set(VariableTemplate(self.string).get_identifiers())

    @property
    def required_sensors(self) -> set[str]:
        return set(SensorTemplate(self.string).get_identifiers())

    def _render(self, string: str) -> str:
        if self.renderer:
            string = self.renderer(string)
        return string

    async def async_generate_string(
        self,
        manager: Manager,
        variables: dict | None = None,
    ) -> str:
        """Generate the string.

        Raises:
            CommandError
        """
        variables = variables or {}
        sensor_values_by_key = {}
        string = self.string

        try:
            string = VariableTemplate(string).substitute(variables)
        except Exception as exc:
            raise CommandError(f"Failed to substitute variable ({exc})")

        try:
            sensors = await manager.async_poll_sensors(self.required_sensors)
        except Exception as exc:
            raise CommandError(f"Failed to poll sensors ({exc})")

        for sensor in sensors:
            if sensor.value is not None:
                sensor_values_by_key[sensor.key] = sensor.value
            else:
                raise CommandError(f"Value of sensor {sensor.key} is None")

        try:
            string = SensorTemplate(string).substitute(sensor_values_by_key)
        except Exception as exc:
            raise CommandError(f"Failed to substitute sensor ({exc})") from exc

        try:
            return self._render(string)
        except Exception as exc:
            raise CommandError(f"Failed to render string ({exc})")

    async def async_execute(
        self, manager: Manager, variables: dict | None = None
    ) -> CommandOutput:
        """Execute.

        Raises:
            CommandError
        """
        try:
            string = await self.async_generate_string(manager, variables)
        except CommandError as exc:
            manager.logger.debug("%s: %s => %s", manager.name, self.string, exc)
            raise

        try:
            output = await manager.async_execute_command_string(string, self.timeout)
        except CommandError as exc:
            manager.logger.debug("%s: %s => %s", manager.name, string, exc)
            raise

        manager.logger.debug(
            "%s: %s => %s, %s, %s",
            manager.name,
            string,
            output.stdout,
            output.stderr,
            output.code,
        )

        return output


@dataclass
class ActionCommand(Command):
    name: str | None = None
    key: str | None = None
    _: KW_ONLY
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        self.key = self.key or name_to_key(self.name)


@dataclass
class SensorCommand(Command):
    _: KW_ONLY
    interval: int | None = None
    sensors: list[Sensor] = field(default_factory=list)

    def __post_init__(self):
        self.last_update: float | None = None

    @property
    def should_update(self) -> bool:
        if not self.interval:
            return False
        if not self.last_update:
            return True
        if time() - self.last_update < self.interval:
            return False
        return True

    @property
    def sensors_by_key(self) -> dict[str, Sensor]:
        return {
            sensor.key: sensor
            for command_sensor in self.sensors
            for sensor in (command_sensor, *command_sensor.child_sensors)
            if command_sensor.key != PLACEHOLDER_KEY
        }

    def remove_sensor(self, key: str) -> None:
        """Remove a sensor."""
        self.sensors = [
            Sensor(key=PLACEHOLDER_KEY) if sensor.key == key else sensor
            for sensor in self.sensors
        ]

    def update_sensors(self, manager: Manager, output: CommandOutput | None) -> None:
        """Update the sensors."""
        if output and output.code == 0:
            self.last_update = output.timestamp
            data = output.stdout
        else:
            data = []

        for i, sensor in enumerate(self.sensors):
            if sensor.dynamic:
                sensor.update(manager, data[i:] or None)
                return
            sensor.update(manager, data[i] if len(data) > i else None)

    async def async_execute(
        self, manager: Manager, variables: dict | None = None
    ) -> CommandOutput:
        try:
            output = await super().async_execute(manager, variables)
        except CommandError:
            self.update_sensors(manager, None)
            raise

        self.update_sensors(manager, output)

        return output
