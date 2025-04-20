from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
import logging
from typing import Any

from .collection import Collection
from .command import Command, SensorCommand
from .default_collections.const import ACTION_NAMES, SENSOR_NAMES, ActionKey, SensorKey
from .error import ConnectError, ExecutionError, OfflineError, SensorError
from .sensor import Sensor
from .state import State
from .synchronizer import Synchronizer
from .terminal import Terminal

_LOGGER = logging.getLogger(__name__)
_TEST_COMMAND = Command("echo ''")

DEFAULT_NAME = "Manager"
DEFAULT_COMMAND_TIMEOUT = 15
DEFAULT_ALLOW_TURN_OFF = False
DEFAULT_DISCONNECT_MODE = False
DEFAULT_DISCONNECT_MODE_DELAY = 0
DEFAULT_REQUEST_TIMEOUTS = {
    "turn_on": 60,
    "turn_off": 30,
    "restart": 30,
    "connect": 30,
}

ExecuteErrorType = ConnectError | ExecutionError
SetErrorType = ConnectError | ExecutionError | SensorError | TypeError | ValueError


@dataclass(frozen=True)
class CommandOutput:
    command_string: str
    timestamp: float
    stdout: list[str]
    stderr: list[str]
    code: int


class Manager(Collection, Synchronizer):
    _action_names = ACTION_NAMES
    _sensor_names = SENSOR_NAMES

    def __init__(
        self,
        terminal: Terminal,
        *,
        name: str = DEFAULT_NAME,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
        allow_turn_off: bool = DEFAULT_ALLOW_TURN_OFF,
        disconnect_mode: bool = DEFAULT_DISCONNECT_MODE,
        disconnect_mode_delay: int = DEFAULT_DISCONNECT_MODE_DELAY,
        request_timeouts: dict[str, int] = DEFAULT_REQUEST_TIMEOUTS,
        mac_address: str | None = None,
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
        self._terminal = terminal
        self._command_timeout = command_timeout
        self._allow_turn_off = allow_turn_off
        self._disconnect_mode = disconnect_mode
        self._disconnect_mode_delay = disconnect_mode_delay
        self._mac_address = mac_address
        self._logger = logger
        self._state = State(self, request_timeouts)
        self._disconnector: asyncio.Task | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.async_disconnect()

    @property
    def state(self) -> State:
        return self._state

    @property
    def network_interface(self) -> str | None:
        return self.get_sensor_value(SensorKey.NETWORK_INTERFACE)

    @property
    def mac_address(self) -> str | None:
        return self._mac_address or self.get_sensor_value(SensorKey.MAC_ADDRESS)

    @property
    def wake_on_lan(self) -> bool | None:
        return self.get_sensor_value(SensorKey.WAKE_ON_LAN)

    @property
    def machine_type(self) -> str | None:
        return self.get_sensor_value(SensorKey.MACHINE_TYPE)

    @property
    def hostname(self) -> str | None:
        return self.get_sensor_value(SensorKey.HOSTNAME)

    @property
    def os_name(self) -> str | None:
        return self.get_sensor_value(SensorKey.OS_NAME)

    @property
    def os_version(self) -> str | None:
        return self.get_sensor_value(SensorKey.OS_VERSION)

    @property
    def os_release(self) -> str | None:
        return self.get_sensor_value(SensorKey.OS_RELEASE)

    @property
    def os_architecture(self) -> str | None:
        return self.get_sensor_value(SensorKey.OS_ARCHITECTURE)

    @property
    def device_name(self) -> str | None:
        return self.get_sensor_value(SensorKey.DEVICE_NAME)

    @property
    def device_model(self) -> str | None:
        return self.get_sensor_value(SensorKey.DEVICE_MODEL)

    @property
    def manufacturer(self) -> str | None:
        return self.get_sensor_value(SensorKey.MANUFACTURER)

    @property
    def serial_number(self) -> str | None:
        return self.get_sensor_value(SensorKey.SERIAL_NUMBER)

    @property
    def cpu_name(self) -> str | None:
        return self.get_sensor_value(SensorKey.CPU_NAME)

    @property
    def cpu_cores(self) -> int | None:
        return self.get_sensor_value(SensorKey.CPU_CORES)

    @property
    def cpu_hardware(self) -> str | None:
        return self.get_sensor_value(SensorKey.CPU_HARDWARE)

    @property
    def cpu_model(self) -> str | None:
        return self.get_sensor_value(SensorKey.CPU_MODEL)

    @property
    def can_connect(self) -> bool:
        return self.state.online and not (self.state.shutting_down or self.state.error)

    @property
    def can_execute(self) -> bool:
        return self.state.connected or (self._disconnect_mode and self.can_connect)

    @property
    def can_turn_off(self) -> bool:
        return (
            self.can_execute
            and self._allow_turn_off
            and ActionKey.TURN_OFF in self.action_commands_by_key
        )

    @property
    def can_restart(self) -> bool:
        return self.can_execute and ActionKey.RESTART in self.action_commands_by_key

    async def _async_disconnect_later(self) -> None:
        if delay := self._disconnect_mode_delay:
            await asyncio.sleep(delay)

        await self.async_disconnect()
        self._disconnector = None

    def _schedule_disconnect(self):
        if self._disconnector:
            self._disconnector.cancel()

        self._disconnector = asyncio.create_task(self._async_disconnect_later())

    def log(self, message: str) -> None:
        """Log a message."""
        self._logger.debug("%s: %s", self.name, message)

    async def async_reset(self) -> None:
        """Disconnect and reset commands."""
        await self.async_disconnect()

        for command in self.commands:
            command.reset(self)

    async def async_update(
        self,
        *,
        force: bool = False,
        once: bool = False,
        test: bool = False,
    ) -> None:
        """Update state and sensor commands, raise errors when done.

        Update all commands with `force`.
        Update only commands that have never been updated before with `once`.
        Execute a test command if there are no commands to update with `test`.
        Never execute a test command in disconnect mode.

        Raises:
            `OfflineError`
            `ConnectError`
            `ExecutionError`

        """
        self.state.update()

        def get_commands():
            commands = [
                command
                for command in self.sensor_commands
                if force or (command.should_update and not (once and command.output))
            ]
            if test and not self._disconnect_mode:
                commands = commands or [_TEST_COMMAND]
            return commands

        if not self._disconnect_mode and self.state.connected:
            try:
                await self.async_execute_commands(get_commands())
            except ExecutionError:
                if not self.state.error:
                    raise
                self.state.update()
            else:
                return

        await self.async_ping()

        if not self._disconnect_mode:
            await self.async_connect()

        await self.async_execute_commands(get_commands())

    async def async_ping(self) -> None:
        """Ping.

        Raises:
            `OfflineError`

        """
        try:
            await self._terminal.async_ping()
        except OfflineError:
            await self.async_reset()
            self.state.handle_ping_error()
            raise
        else:
            self.state.handle_ping_success()

    async def async_connect(self) -> None:
        """Connect.

        Return if already connected.

        Raises:
            `ConnectError`

        """
        if self.state.connected:
            return

        if not self.state.online:
            raise ConnectError("Host is offline")

        if self.state.shutting_down:
            raise ConnectError("Host is shutting down")

        if self.state.error:
            raise ConnectError("Waiting for update after error")

        try:
            await self._terminal.async_connect()
        except ConnectError:
            await self.async_reset()
            self.state.handle_connect_error()
            raise
        else:
            self.state.handle_connect_success()

    async def async_disconnect(self) -> None:
        """Disconnect.

        Return if already disconnected.
        """
        if not self.state.connected:
            return

        await self._terminal.async_disconnect()
        self.state.handle_disconnect()

    async def async_execute(
        self,
        string: str,
        command_timeout: int | None = None,
    ) -> CommandOutput:
        """Execute.

        Connect before and disconnect after execution if disconnect mode is enabled.

        Raises:
            `ConnectError`
            `ExecutionError`

        """
        if self._disconnect_mode:
            await self.async_connect()

        if not self.state.connected:
            raise ExecutionError("Not connected")

        try:
            return await self._terminal.async_execute(
                string, command_timeout or self._command_timeout
            )
        except TimeoutError as exc:
            raise ExecutionError("Timeout during command") from exc
        except ExecutionError:
            await self.async_reset()
            self.state.handle_execute_error()
            raise
        finally:
            if self._disconnect_mode and self.state.connected:
                self._schedule_disconnect()

    async def async_execute_command(
        self,
        command: Command,
        variables: dict | None = None,
    ) -> CommandOutput:
        """Execute a command.

        Raises:
            `ConnectError`
            `ExecutionError`

        """
        try:
            string = await command.async_render_string(self, variables)
        except (ConnectError, ExecutionError) as exc:
            self.log(f"{command.string} => {exc}")
            command.handle_error(self, exc)
            raise

        try:
            output = await self.async_execute(string, command.timeout)
        except (ConnectError, ExecutionError) as exc:
            self.log(f"{string} => {exc}")
            command.handle_error(self, exc)
            raise

        self.log(f"{string} => {output.stdout}, {output.stderr}, {output.code}")
        command.handle_success(self, output)
        await self.async_poll_sensors(command.linked_sensors)
        return output

    async def async_execute_commands(
        self,
        commands: Sequence[Command],
        *,
        raise_errors: bool = True,
    ) -> tuple[ExecuteErrorType | None]:
        """Execute multiple commands, raise errors when done.

        Raises:
            `ConnectError` (only with `raise_errors`)
            `ExecutionError` (only with `raise_errors`)

        Returns:
            Tuple of errors in the same order as `commands`.

        """
        for command in commands:
            with suppress(ConnectError, ExecutionError):
                await self.async_execute_command(command)

        errors = tuple(command.error for command in commands)

        if raise_errors and (exc := next((e for e in errors if e), None)):
            raise exc

        return errors

    async def async_run_action(
        self,
        key: str,
        variables: dict | None = None,
    ) -> CommandOutput:
        """Run an action.

        Raises:
            `KeyError`
            `ConnectError`
            `ExecutionError`

        """
        command = self.get_action_command(key)
        return await self.async_execute_command(command, variables)

    async def async_poll_sensor(self, key: str) -> Sensor:
        """Poll a sensor.

        Raises:
            `KeyError`
            `ConnectError`
            `ExecutionError`

        """
        sensors, _ = await self.async_poll_sensors([key])
        return sensors[0]

    async def async_poll_sensors(
        self,
        keys: Sequence[str],
        *,
        raise_errors: bool = True,
    ) -> tuple[tuple[Sensor], tuple[ExecuteErrorType | None]]:
        """Poll multiple sensors, raise errors when done.

        Raises:
            `KeyError`
            `ConnectError` (only with `raise_errors`)
            `ExecutionError` (only with `raise_errors`)

        Returns:
            Tuples of sensors and errors in the same order as `keys`.

        """
        sensors = tuple(self.get_sensor(key) for key in keys)
        commands = tuple(self.get_sensor_command(key) for key in keys)
        unique_commands: list[SensorCommand] = []

        for command in commands:
            if command not in unique_commands:
                unique_commands.append(command)

        await self.async_execute_commands(unique_commands, raise_errors=raise_errors)
        return sensors, tuple(command.error for command in commands)

    async def async_set_sensor_value(self, key: str, value: Any) -> Sensor:
        """Set the value of a controllable sensor.

        Raises:
            `KeyError`
            `ConnectError`
            `ExecutionError`
            `TypeError`
            `ValueError`

        """
        sensors, _ = await self.async_set_sensor_values([key], [value])
        return sensors[0]

    async def async_set_sensor_values(
        self,
        keys: Sequence[str],
        values: Sequence[Any],
        *,
        raise_errors: bool = True,
    ) -> tuple[tuple[Sensor], tuple[SetErrorType | None]]:
        """Set the value of multiple controllable sensors, raise errors when done.

        Raises:
            `KeyError`
            `ConnectError` (only with `raise_errors`)
            `ExecutionError` (only with `raise_errors`)
            `SensorError` (only with `raise_errors`)
            `TypeError` (only with `raise_errors`)
            `ValueError` (only with `raise_errors`)

        Returns:
            Tuples of sensors and errors in the same order as `keys`.

        """
        sensors, poll_errors = await self.async_poll_sensors(keys, raise_errors=False)
        errors = [*poll_errors]
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
                ConnectError,
                ExecutionError,
            ) as exc:
                errors[i] = exc

        _, poll_errors = await self.async_poll_sensors(keys, raise_errors=False)

        for i, sensor in enumerate(sensors):
            if errors[i]:
                continue
            if exc := poll_errors[i]:
                errors[i] = exc
                continue
            if values[i] != sensor.value:
                errors[i] = SensorError(sensor.key, "Value not set correctly")

        errors = tuple(errors)

        if raise_errors and (exc := next((e for e in errors if e), None)):
            raise exc

        return sensors, errors

    async def async_turn_off(self) -> CommandOutput:
        """Turn off by running the `TURN_OFF` action.

        Raises:
            `PermissionError`
            `KeyError`
            `ConnectError`
            `ExecutionError`

        """
        if not self._allow_turn_off:
            raise PermissionError("Not allowed to turn off")

        output = await self.async_run_action(ActionKey.TURN_OFF)

        if output.code > 0:
            raise ExecutionError(f"'TURN_OFF' action returned exit code {output.code}")

        await self.async_disconnect()
        self.state.handle_turn_off()
        return output

    async def async_restart(self) -> CommandOutput:
        """Restart by running the `RESTART` action.

        Raises:
            `KeyError`
            `ConnectError`
            `ExecutionError`

        """
        output = await self.async_run_action(ActionKey.RESTART)

        if output.code > 0:
            raise ExecutionError(f"'RESTART' action returned exit code {output.code}")

        await self.async_disconnect()
        self.state.handle_restart()
        return output
