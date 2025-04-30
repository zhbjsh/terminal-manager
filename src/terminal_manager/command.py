from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
import re
from string import Template
from time import time
from typing import TYPE_CHECKING

from .error import CommandError, ExecutionError
from .helpers import name_to_key
from .sensor import Sensor

if TYPE_CHECKING:
    from .collection import Collection
    from .manager import CommandOutput, ExecuteErrorType, Manager

SENSOR_DELIMITER = "&"
VARIABLE_DELIMITER = "@"
PLACEHOLDER_KEY = "_"


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
        self.output: CommandOutput | None = None
        self.error: ExecuteErrorType | None = None

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

    def _check_loop(self, collection: Collection) -> None:
        commands_by_key = collection.sensor_commands_by_sensor_key

        def detect_loop(command: Command, command_chain: list[Command]) -> None:
            command_chain = [*command_chain, command]
            for key in command.sub_sensors:
                if key not in commands_by_key:
                    continue
                if (sub_command := commands_by_key[key]) in command_chain:
                    raise CommandError(f"Loop detected: '{key}'")
                detect_loop(sub_command, command_chain)

        detect_loop(self, [])

    def _check_renderer(self) -> None:
        if not self.renderer:
            return

        try:
            string = self.renderer(self.string)
        except Exception as exc:
            raise CommandError(f"Failed to render string: '{exc}'") from exc

        if not isinstance(string, str):
            raise CommandError(f"Renderer returned {type(string)} instead of {str}")

    def check(self, collection: Collection) -> None:
        """Check configuration.

        Raises:
            `SensorError`
            `CommandError`

        """
        self._check_loop(collection)
        self._check_renderer()

    async def async_render_string(
        self,
        manager: Manager,
        variables: dict | None = None,
    ) -> str:
        """Render string.

        Raises:
            `ConnectError`
            `ExecutionError`

        """
        variables = variables or {}
        sensor_values_by_key = {}
        string = self.string

        try:
            string = VariableTemplate(string).substitute(variables)
        except Exception as exc:
            raise ExecutionError(f"Failed to substitute variables: {exc}") from exc

        try:
            sensors, _ = await manager.async_poll_sensors(self.required_sensors)
        except KeyError as exc:
            raise ExecutionError(f"Required sensor not found: {exc}") from exc

        for sensor in sensors:
            if sensor.value is not None:
                sensor_values_by_key[sensor.key] = sensor.value
            else:
                raise ExecutionError(f"Value of required sensor {sensor.key} is None")

        try:
            string = SensorTemplate(string).substitute(sensor_values_by_key)
        except Exception as exc:
            raise ExecutionError(f"Failed to substitute sensors: {exc}") from exc

        if self.renderer:
            return self.renderer(string)

        return string

    def reset(self, manager: Manager) -> None:
        """Reset."""
        self.output = None
        self.error = None

    def handle_success(self, manager: Manager, output: CommandOutput) -> None:
        """Handle success."""
        self.output = output
        self.error = None

    def handle_error(self, manager: Manager, exc: ExecuteErrorType) -> None:
        """Handle error."""
        self.output = None
        self.error = exc


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
            return True

        if not self.interval:
            return False

        return time() - self.output.timestamp > self.interval

    @property
    def sensors_by_key(self) -> dict[str, Sensor]:
        return {
            sensor.key: sensor
            for command_sensor in self.sensors
            for sensor in (command_sensor, *command_sensor.child_sensors)
            if command_sensor.key != PLACEHOLDER_KEY
        }

    def _check_sensors(self, collection: Collection) -> None:
        dynamic = False

        for sensor in self.sensors:
            if sensor.dynamic:
                dynamic = True
            if dynamic and not sensor.dynamic:
                raise CommandError(f"Sensor '{sensor.key}' must be dynamic")
            sensor.check(collection)

    def _check_required_variables(self) -> None:
        if self.required_variables:
            raise CommandError("Variables not allowed in sensor commands")

    def check(self, collection: Collection) -> None:
        """Check command configuration.

        Raises:
            `SensorError`
            `CommandError`

        """
        self._check_sensors(collection)
        self._check_required_variables()
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
        if self.output:
            self.clear_sensor_values(manager)

        super().reset(manager)

    def handle_success(self, manager: Manager, output: CommandOutput) -> None:
        """Handle success and update sensors."""
        super().handle_success(manager, output)
        self.update_sensors(manager)

    def handle_error(self, manager: Manager, exc: ExecuteErrorType) -> None:
        """Handle error and update sensors."""
        super().handle_error(manager, exc)
        self.update_sensors(manager)

    def update_sensors(self, manager: Manager) -> None:
        """Update sensors."""
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
