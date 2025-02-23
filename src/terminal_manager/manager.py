from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
import logging
from typing import Any

from .collection import Collection
from .command import Command, SensorCommand
from .default_collections.const import ActionKey, SensorKey
from .errors import CommandError, ExecutionError, SensorError
from .sensor import Sensor
from .synchronizer import Synchronizer

_LOGGER = logging.getLogger(__name__)
_TEST_COMMAND = Command("echo ''")

DEFAULT_NAME = "Manager"
DEFAULT_COMMAND_TIMEOUT = 15
DEFAULT_ALLOW_TURN_OFF = False

CommandExecuteError = CommandError | ExecutionError
SensorSetError = CommandError | ExecutionError | SensorError | TypeError | ValueError


@dataclass(frozen=True)
class CommandOutput:
    command_string: str
    timestamp: float
    stdout: list[str]
    stderr: list[str]
    code: int


class Manager(Collection, Synchronizer):
    def __init__(
        self,
        *,
        name: str = DEFAULT_NAME,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
        allow_turn_off: bool = DEFAULT_ALLOW_TURN_OFF,
        collection: Collection | None = None,
        logger: logging.Logger = _LOGGER,
    ) -> None:
        Synchronizer.__init__(self)
        Collection.__init__(
            self,
            name,
            collection.action_commands if collection else None,
            collection.sensor_commands if collection else None,
        )
        self.command_timeout = command_timeout
        self.allow_turn_off = allow_turn_off
        self.logger = logger

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.async_close()

    @property
    def network_interface(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.NETWORK_INTERFACE)

    @property
    def mac_address(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.MAC_ADDRESS)

    @property
    def wake_on_lan(self) -> bool | None:
        return self._last_known_value_or_none(SensorKey.WAKE_ON_LAN)

    @property
    def machine_type(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.MACHINE_TYPE)

    @property
    def hostname(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.HOSTNAME)

    @property
    def os_name(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.OS_NAME)

    @property
    def os_version(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.OS_VERSION)

    @property
    def os_architecture(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.OS_ARCHITECTURE)

    @property
    def device_name(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.DEVICE_NAME)

    @property
    def device_model(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.DEVICE_MODEL)

    @property
    def manufacturer(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.MANUFACTURER)

    @property
    def serial_number(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.SERIAL_NUMBER)

    @property
    def cpu_name(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.CPU_NAME)

    @property
    def cpu_cores(self) -> int | None:
        return self._last_known_value_or_none(SensorKey.CPU_CORES)

    @property
    def cpu_hardware(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.CPU_HARDWARE)

    @property
    def cpu_model(self) -> str | None:
        return self._last_known_value_or_none(SensorKey.CPU_MODEL)

    def _last_known_value_or_none(self, sensor_key: str) -> Any | None:
        if sensor := self.sensors_by_key.get(sensor_key):
            return sensor.last_known_value

        return None

    def reset_commands(self) -> None:
        """Reset commands and clear sensor values."""
        for command in *self.action_commands, *self.sensor_commands:
            command.reset(self)

    async def async_close(self) -> None:
        """Close."""

    async def async_update(
        self,
        *,
        force: bool = False,
        once: bool = False,
        test: bool = False,
        raise_errors: bool = False,
    ) -> None:
        """Update state and sensor commands, raise errors when done.

        Commands that raised a `CommandError` count as updated.
        Update all commands with `force`.
        Update only commands that have never been updated before with `once`.
        Execute a test command if there are no commands to update with `test`.

        Raises:
            `CommandError` (only with `raise_errors`)
            `ExecuteError` (only with `raise_errors`)

        """
        commands = [
            command
            for command in self.sensor_commands
            if force or (command.should_update and not (once and command.output))
        ]

        if test:
            commands = commands or [_TEST_COMMAND]

        await self.async_execute_commands(commands, raise_errors=raise_errors)

    async def async_execute_command_string(
        self,
        string: str,
        command_timeout: int | None = None,
    ) -> CommandOutput:
        """Execute a command string.

        Raises:
            ExecutionError

        """
        raise ExecutionError("Not implemented")

    async def async_execute_command(
        self,
        command: Command,
        variables: dict | None = None,
    ) -> CommandOutput:
        """Execute a command.

        Raises:
            CommandError
            ExecutionError

        """
        return await command.async_execute(self, variables)

    async def async_execute_commands(
        self,
        commands: Sequence[Command],
        *,
        raise_errors: bool = False,
    ) -> tuple[CommandExecuteError | None]:
        """Execute multiple commands, raise errors when done.

        Raises:
            `CommandError` (only with `raise_errors`)
            `ExecuteError` (only with `raise_errors`)

        Returns:
            Tuple of errors in the same order as `commands`.

        """
        for command in commands:
            with suppress(CommandError, ExecutionError):
                await self.async_execute_command(command)

        errors = tuple(command.error for command in commands)
        first_error = next((exc for exc in errors if exc), None)

        if raise_errors and first_error:
            raise first_error

        return errors

    async def async_run_action(
        self,
        key: str,
        variables: dict | None = None,
    ) -> CommandOutput:
        """Run an action.

        Raises:
            KeyError
            CommandError
            ExecutionError

        """
        command = self.get_action_command(key)
        return await self.async_execute_command(command, variables)

    async def async_poll_sensor(
        self,
        key: str,
        *,
        raise_errors: bool = False,
    ) -> Sensor:
        """Poll a sensor.

        Raises:
            KeyError
            CommandError (only with `raise_errors`)
            ExecutionError (only with `raise_errors`)

        """
        sensors, errors = await self.async_poll_sensors(
            [key], raise_errors=raise_errors
        )
        return sensors[0]

    async def async_poll_sensors(
        self,
        keys: Sequence[str],
        *,
        raise_errors: bool = False,
    ) -> tuple[tuple[Sensor], tuple[CommandExecuteError | None]]:
        """Poll multiple sensors, raise errors when done.

        Raises:
            KeyError
            CommandError (only with `raise_errors`)
            ExecutionError (only with `raise_errors`)

        Returns:
            Tuples of sensors and errors in the same order as `keys`.

        """
        sensors = tuple(self.get_sensor(key) for key in keys)
        commands = tuple(self.get_sensor_command(key) for key in keys)
        unique_commands: list[SensorCommand] = []

        for command in commands:
            if command not in unique_commands:
                unique_commands.append(command)

        errors = await self.async_execute_commands(
            unique_commands,
            raise_errors=raise_errors,
        )

        return sensors, errors

    async def async_set_sensor_value(
        self,
        key: str,
        value: Any,
        *,
        raise_errors: bool = False,
    ) -> Sensor:
        """Set the value of a controllable sensor.

        Raises:
            KeyError
            CommandError (only with `raise_errors`)
            ExecutionError (only with `raise_errors`)
            TypeError (only with `raise_errors`)
            ValueError (only with `raise_errors`)

        """
        sensors, errors = await self.async_set_sensor_values(
            [key], [value], raise_errors=raise_errors
        )
        return sensors[0]

    async def async_set_sensor_values(
        self,
        keys: Sequence[str],
        values: Sequence[Any],
        *,
        raise_errors: bool = False,
    ) -> tuple[tuple[Sensor], tuple[SensorSetError | None]]:
        """Set the value of multiple controllable sensors, raise errors when done.

        Raises:
            KeyError
            CommandError (only with `raise_errors`)
            ExecutionError (only with `raise_errors`)
            SensorError (only with `raise_errors`)
            TypeError (only with `raise_errors`)
            ValueError (only with `raise_errors`)

        Returns:
            Tuples of sensors and errors in the same order as `keys`.

        """
        sensors, poll_errors = await self.async_poll_sensors(keys)
        errors: list[SensorSetError | None] = [*poll_errors]
        values = [*values]

        for i, sensor in enumerate(sensors):
            if errors[i]:
                continue
            try:
                values[i] = await sensor.async_set(self, values[i])
            except (
                SensorError,
                TypeError,
                ValueError,
                CommandError,
                ExecutionError,
            ) as exc:
                errors[i] = exc

        _, poll_errors = await self.async_poll_sensors(keys)

        for i, sensor in enumerate(sensors):
            if errors[i]:
                continue
            if exc := poll_errors[i]:
                errors[i] = exc
                continue
            if values[i] != sensor.value:
                errors[i] = SensorError("Value not set correctly")

        errors = set(errors)
        first_error = next((exc for exc in errors if exc), None)

        if raise_errors and first_error:
            raise first_error

        return sensors, errors

    async def async_turn_off(self) -> CommandOutput:
        """Turn off by running the `TURN_OFF` action.

        Raises:
            PermissionError
            KeyError
            CommandError
            ExecutionError

        """
        if not self.allow_turn_off:
            raise PermissionError("Not allowed to turn off")

        output = await self.async_run_action(ActionKey.TURN_OFF)

        if output.code > 0:
            raise ExecutionError(f"'TURN_OFF' action returned exit code {output.code}")

        return output

    async def async_restart(self) -> CommandOutput:
        """Restart by running the `RESTART` action.

        Raises:
            KeyError
            CommandError
            ExecutionError

        """
        output = await self.async_run_action(ActionKey.RESTART)

        if output.code > 0:
            raise ExecutionError(f"'RESTART' action returned exit code {output.code}")

        return output
