from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
import re
from string import Template
from time import time
from typing import TYPE_CHECKING

from .errors import CommandError, ExecutionError, SensorError
from .helpers import name_to_key
from .sensor import Sensor

if TYPE_CHECKING:
    from .collection import Collection
    from .manager import CommandOutput, Manager

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
    {re.escape(delimiter)}{{(?:
      (?P<braced>{Template.idpattern})|
      (?P<invalid>)|
      (?P<named>)|
      (?P<escaped>)
    )}}
    """


class VariableTemplate(Template):
    delimiter = VARIABLE_DELIMITER
    pattern = rf"""
    {re.escape(delimiter)}{{(?:
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
        self.key = f"{sensor.key}_{name_to_key(self.id)}"
        self.name = f"{sensor.name} {name}" if sensor.name else name
        self.data = data_field


@dataclass
class Command:
    string: str
    _: KW_ONLY
    timeout: float | None = None
    renderer: Callable[[str], str] | None = None
    _linked_sensors: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self):
        self.error: CommandError | ExecutionError | None = None
        self.output: CommandOutput | None = None

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

    async def async_render_string(
        self,
        manager: Manager,
        variables: dict | None = None,
    ) -> str:
        """Render string.

        Raises:
            `CommandError`
            `ExecutionError`

        """
        variables = variables or {}
        sensor_values_by_key = {}
        string = self.string

        try:
            self.check(manager)
        except SensorError as exc:
            raise CommandError(str(exc)) from exc

        try:
            string = VariableTemplate(string).substitute(variables)
        except Exception as exc:
            raise CommandError(f"Failed to substitute variable: {exc}") from exc

        sensors, errors = await manager.async_poll_sensors(
            self.required_sensors,
            raise_errors=True,
        )

        for sensor in sensors:
            if sensor.value is not None:
                sensor_values_by_key[sensor.key] = sensor.value
            else:
                raise CommandError(f"Value of required sensor {sensor.key} is None")

        try:
            string = SensorTemplate(string).substitute(sensor_values_by_key)
        except Exception as exc:
            raise CommandError(f"Failed to substitute sensor {exc}") from exc

        if self.renderer:
            return self.renderer(string)

        return string

    def check(self, collection: Collection) -> None:
        """Check configuration.

        Raises:
            `SensorError`
            `CommandError`

        """
        commands_by_key = collection.sensor_commands_by_sensor_key
        commands = []

        def detect_loop(command: Command) -> None:
            sub_commands = []
            if command not in commands:
                commands.append(command)
            for key in command.sub_sensors:
                if key not in commands_by_key:
                    raise CommandError(f"Sensor '{key}' not found")
                if (sub_command := commands_by_key[key]) in commands:
                    raise CommandError(f"Loop detected: '{key}'")
                if sub_command not in sub_commands:
                    sub_commands.append(sub_command)
                    detect_loop(sub_command)

        detect_loop(self)

        if not self.renderer:
            return

        try:
            string = self.renderer(self.string)
        except Exception as exc:
            raise CommandError(f"Failed to render string: '{exc}'") from exc

        if not isinstance(string, str):
            raise CommandError(f"Renderer returned {type(string)} instead of {str}")

    def reset(self, manager: Manager) -> None:
        """Reset."""
        self.error = None
        self.output = None

    async def async_execute(
        self,
        manager: Manager,
        variables: dict | None = None,
    ) -> CommandOutput:
        """Execute.

        Raises:
            `CommandError`
            `ExecutionError`

        """
        try:
            string = await self.async_render_string(manager, variables)
            output = await manager.async_execute_command_string(string, self.timeout)
        except (CommandError, ExecutionError) as exc:
            self.error = exc
            self.output = None
            manager.logger.debug("%s: %s => %s", manager.name, self.string, exc)
            raise

        self.error = None
        self.output = output
        manager.logger.debug(
            "%s: %s => %s, %s, %s",
            manager.name,
            output.command_string,
            output.stdout,
            output.stderr,
            output.code,
        )

        await manager.async_poll_sensors(self.linked_sensors, raise_errors=True)
        return output


@dataclass
class ActionCommand(Command):
    name: str | None = None
    key: str | None = None
    _: KW_ONLY
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.name = self.name.strip() if self.name else None
        self.key = self.key.strip() if self.key else name_to_key(self.name)


@dataclass
class SensorCommand(Command):
    _: KW_ONLY
    interval: int | None = None
    separator: str | None = None
    sensors: list[Sensor] = field(default_factory=list)

    @property
    def linked_sensors(self) -> set[str]:
        linked_sensors = {*self._linked_sensors}

        for sensor in self.sensors:
            linked_sensors.update(sensor.linked_sensors)

        return {key for key in linked_sensors if key not in self.sensors_by_key}

    @property
    def should_update(self) -> bool:
        if not self.output:
            return not isinstance(self.error, CommandError)

        if not self.interval:
            return False

        if not self.output:
            return True

        return time() - self.output.timestamp > self.interval

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
            `SensorError`
            `CommandError`

        """
        dynamic = False

        for sensor in self.sensors:
            if sensor.dynamic:
                dynamic = True
            if dynamic and not sensor.dynamic:
                raise CommandError(f"Sensor '{sensor.key}' must be dynamic")
            sensor.check(collection)

        super().check(collection)

    def remove_sensor(self, key: str) -> None:
        """Remove a sensor."""
        self.sensors = [
            Sensor(key=PLACEHOLDER_KEY) if sensor.key == key else sensor
            for sensor in self.sensors
        ]

    def clear_sensor_values(self, manager: Manager) -> None:
        """Set sensor values to `None`."""
        for sensor in self.sensors:
            sensor.update(manager, None)

    def reset(self, manager: Manager) -> None:
        """Reset and clear sensor values."""
        super().reset(manager)
        self.clear_sensor_values(manager)

    def update_sensors(self, manager: Manager) -> None:
        """Update the sensors."""
        if not (output := self.output) or output.code > 0:
            self.clear_sensor_values(manager)
            return

        data = output.stdout
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
            return await super().async_execute(manager, variables)
        finally:
            self.update_sensors(manager)
