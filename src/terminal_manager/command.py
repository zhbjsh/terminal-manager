from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
from string import Formatter
from typing import TYPE_CHECKING

from .errors import CommandError
from .helpers import name_to_key
from .sensor import Sensor

if TYPE_CHECKING:
    from . import CommandOutput, Manager

SENSOR_PLACEHOLDER_KEY = "_"


@dataclass
class Command:
    """The Command class."""

    string: str
    _: KW_ONLY
    timeout: float | None = None
    renderer: Callable[[str], str] | None = None

    @property
    def field_keys(self) -> list[str]:
        """Field keys."""
        return {key for _, key, _, _ in Formatter().parse(self.string) if key}

    def _render(self, string: str) -> str:
        if self.renderer:
            return self.renderer(string)

        return string

    def get_variable_keys(self, manager: Manager) -> set[str]:
        """Get variable keys."""
        return {key for key in self.field_keys if key not in manager.sensors_by_key}

    def get_sensor_keys(self, manager: Manager) -> set[str]:
        """Get sensor keys."""
        return {key for key in self.field_keys if key in manager.sensors_by_key}

    async def async_format(
        self, manager: Manager, variables: dict | None = None
    ) -> str:
        """Format the string.

        Raises:
            CommandError
        """
        variables = {**variables} if variables else {}
        missing_sensor_keys = set()

        for key in self.get_variable_keys(manager):
            if key not in variables:
                raise CommandError(f"Variable {key} is missing")

        for key in self.get_sensor_keys(manager):
            if key not in variables:
                sensor = manager.get_sensor(key)
                if sensor.value is not None:
                    variables[sensor.key] = sensor.value
                else:
                    missing_sensor_keys.add(sensor.key)

        for sensor in await manager.async_poll_sensors(missing_sensor_keys):
            if sensor.value is not None:
                variables[sensor.key] = sensor.value
            else:
                raise CommandError(f"Value of sensor {sensor.key} is None")

        try:
            return self._render(self.string.format(**variables))
        except Exception as exc:
            raise CommandError("Failed to generate string ({exc})") from exc

    async def async_execute(
        self, manager: Manager, variables: dict | None = None
    ) -> CommandOutput:
        """Execute.

        Raises:
            CommandError
        """
        try:
            string = await self.async_format(manager, variables)
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
    """The ActionCommand class."""

    name: str | None = None
    key: str | None = None
    _: KW_ONLY
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        self.key = self.key or name_to_key(self.name)


@dataclass
class SensorCommand(Command):
    """The SensorCommand class."""

    _: KW_ONLY
    interval: int | None = None
    sensors: list[Sensor] = field(default_factory=list)

    def __post_init__(self):
        self.last_update: float | None = None

    @property
    def sensors_by_key(self) -> dict[str, Sensor]:
        """Sensors by key."""
        return {
            sensor.key: sensor
            for command_sensor in self.sensors
            for sensor in (command_sensor, *command_sensor.child_sensors)
            if command_sensor.key != SENSOR_PLACEHOLDER_KEY
        }

    def remove_sensor(self, key: str) -> None:
        """Remove a sensor."""
        self.sensors = [
            Sensor(key=SENSOR_PLACEHOLDER_KEY) if sensor.key == key else sensor
            for sensor in self.sensors
        ]

    def update_sensors(self, manager: Manager, output: CommandOutput | None) -> None:
        """Update sensors."""
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
