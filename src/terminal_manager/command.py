from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
import re as _re
from string import Template
from time import time
from typing import TYPE_CHECKING

from .errors import CommandError, CommandLoopError, InvalidSensorError
from .helpers import name_to_key
from .sensor import Sensor

if TYPE_CHECKING:
    from . import Collection, CommandOutput, Manager

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


class DynamicData:
    def __init__(
        self,
        sensor: Sensor,
        id_field: str,
        data_field: str,
        name_field: str | None,
    ) -> None:
        self.id = id_field.strip()
        name = name_field.strip() if name_field else self.id
        self.key = f"{sensor.key}_{name_to_key(name)}"
        self.name = f"{sensor.name} {name}" if sensor.name else name
        self.data = data_field


@dataclass
class Command:
    string: str
    _: KW_ONLY
    timeout: float | None = None
    renderer: Callable[[str], str] | None = None
    _linked_sensors: set[str] = field(default_factory=set, init=False, repr=False)

    @property
    def required_variables(self) -> set[str]:
        """Variables required to render the command string."""
        return set(VariableTemplate(self.string).get_identifiers())

    @property
    def required_sensors(self) -> set[str]:
        """Sensors required to render the command string."""
        return set(SensorTemplate(self.string).get_identifiers())

    @property
    def linked_sensors(self) -> set[str]:
        """Sensors to poll after execution of the command."""
        return self._linked_sensors

    @property
    def sub_sensors(self) -> set[str]:
        """Set of required and linked sensors."""
        return {*self.required_sensors, *self.linked_sensors}

    def _render(self, string: str) -> str:
        if self.renderer:
            string = self.renderer(string)

        return string

    def check(self, collection: Collection) -> None:
        """Check configuration.

        Raises:
            InvalidSensorError
            CommandLoopError

        """
        commands_by_key = collection.sensor_commands_by_sensor_key
        commands = []

        def detect_loop(command: Command) -> None:
            commands.append(command)
            sub_commands = []
            for key in command.sub_sensors:
                if key not in commands_by_key:
                    continue
                if (sub_command := commands_by_key[key]) in commands:
                    raise CommandLoopError(f"Command loop detected: {key}")
                if sub_command not in sub_commands:
                    sub_commands.append(sub_command)
            for sub_command in sub_commands:
                detect_loop(sub_command)

        detect_loop(self)

    async def async_execute(
        self,
        manager: Manager,
        variables: dict | None = None,
    ) -> CommandOutput:
        """Execute.

        Raises:
            CommandError

        """
        variables = variables or {}
        sensor_values_by_key = {}
        string = self.string

        try:
            self.check(manager)
        except (CommandLoopError, InvalidSensorError) as exc:
            raise CommandError(f"Command check failed ({exc})") from exc

        try:
            string = VariableTemplate(string).substitute(variables)
        except Exception as exc:
            raise CommandError(f"Failed to substitute variable ({exc})") from exc

        try:
            sensors = await manager.async_poll_sensors(self.required_sensors)
        except Exception as exc:
            raise CommandError(f"Failed to poll required sensors ({exc})") from exc

        for sensor in sensors:
            if sensor.value is not None:
                sensor_values_by_key[sensor.key] = sensor.value
            else:
                raise CommandError(f"Value of required sensor {sensor.key} is None")

        try:
            string = SensorTemplate(string).substitute(sensor_values_by_key)
        except Exception as exc:
            raise CommandError(f"Failed to substitute sensor ({exc})") from exc

        try:
            string = self._render(string)
        except Exception as exc:
            raise CommandError(f"Failed to render string ({exc})") from exc

        output = await manager.async_execute_command_string(string, self.timeout)

        await manager.async_poll_sensors(self.linked_sensors, raise_errors=True)

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
    separator: str | None = None
    sensors: list[Sensor] = field(default_factory=list)

    def __post_init__(self):
        self.last_update: float | None = None

    @property
    def linked_sensors(self) -> set[str]:
        linked_sensors = {*self._linked_sensors}

        for sensor in self.sensors:
            linked_sensors.update(sensor.linked_sensors)

        return {key for key in linked_sensors if key not in self.sensors_by_key}

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

    def check(self, collection: Collection) -> None:
        """Check command configuration.

        Raises:
            InvalidSensorError
            CommandLoopError

        """
        dynamic = False

        for sensor in self.sensors:
            if sensor.dynamic:
                dynamic = True
            if dynamic and not sensor.dynamic:
                raise InvalidSensorError(
                    f"Static sensor can't be defined after dynamic sensor: {sensor.key}"
                )
            sensor.check(collection)

        super().check(collection)

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

        dyn_start = None
        
        for i, sensor in enumerate(self.sensors):
            if sensor.dynamic:
                dyn_start = i
                break
            sensor_data = data[i] if len(data) > i else None
            sensor.update(manager, sensor_data)

        if dyn_start is None:
            return

        dyn_data = data[dyn_start:]
        dyn_sensors = self.sensors[dyn_start:]
        dyn_count = len(dyn_sensors)

        for i, sensor in enumerate(dyn_sensors):
            sensor_data = [
                DynamicData(
                    sensor,
                    fields[0],
                    fields[i + 1],
                    fields[dyn_count + 1] if len(fields) > dyn_count + 1 else None,
                )
                for line in dyn_data
                if len(fields := line.split(self.separator)) > dyn_count
            ] or None
            sensor.update(manager, sensor_data or None)

    async def async_execute(
        self,
        manager: Manager,
        variables: dict | None = None,
    ) -> CommandOutput:
        try:
            output = await super().async_execute(manager, variables)
        except CommandError:
            self.update_sensors(manager, None)
            raise

        self.update_sensors(manager, output)

        return output
