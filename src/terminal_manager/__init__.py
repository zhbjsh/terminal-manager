"""Terminal manager."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .collection import Collection
from .command import PLACEHOLDER_KEY, ActionCommand, Command, SensorCommand
from .default_collections import ActionKey, SensorKey
from .errors import CommandError
from .event import Event
from .sensor import BinarySensor, NumberSensor, Sensor, TextSensor
from .synchronizer import Synchronizer

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Manager"
DEFAULT_COMMAND_TIMEOUT = 15
DEFAULT_ALLOW_TURN_OFF = False


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

    async def async_close(self) -> None:
        """Close."""

    async def async_update_sensor_commands(self, force: bool = False) -> None:
        """Update the sensor commands.

        Execute sensor commands that passed their `interval` or
        all sensor commands with `force=True`.

        """
        for command in self.sensor_commands:
            if not (force or command.should_update):
                return
            try:
                await self.async_execute_command(command)
            except CommandError:
                pass

    async def async_execute_command_string(
        self, string: str, command_timeout: int | None = None
    ) -> CommandOutput:
        """Execute a command string.

        Raises:
            CommandError
        """
        raise CommandError("Not implemented")

    async def async_execute_command(
        self, command: Command, variables: dict | None = None
    ) -> CommandOutput:
        """Execute a command.

        Raises:
            CommandError
        """
        return await command.async_execute(self, variables)

    async def async_run_action(
        self, key: str, variables: dict | None = None
    ) -> CommandOutput:
        """Run an action.

        Raises:
            CommandError
        """
        command = self.get_action_command(key)
        return await self.async_execute_command(command, variables)

    async def async_poll_sensor(
        self, key: str, *, raise_errors: bool = False
    ) -> Sensor:
        """Poll a sensor.

        Raises:
            CommandError (only with `raise_errors=True`)
        """
        sensors = await self.async_poll_sensors([key], raise_errors=raise_errors)
        return sensors[0]

    async def async_poll_sensors(
        self, keys: Sequence[str], *, raise_errors: bool = False
    ) -> list[Sensor]:
        """Poll multiple sensors.

        Raises:
            CommandError (only with `raise_errors=True`)
        """
        sensors = [self.get_sensor(key) for key in keys]
        commands = [self.get_sensor_command(key) for key in set(keys)]

        for command in commands:
            try:
                await self.async_execute_command(command)
            except CommandError:
                if raise_errors:
                    raise

        return sensors

    async def async_set_sensor_value(
        self, key: str, value: Any, *, raise_errors: bool = False
    ) -> Sensor:
        """Set the value of a controllable sensor.

        Raises:
            TypeError (only with `raise_errors=True`)
            ValueError (only with `raise_errors=True`)
            CommandError (only with `raise_errors=True`)
        """
        sensors = await self.async_set_sensor_values(
            [key], [value], raise_errors=raise_errors
        )
        return sensors[0]

    async def async_set_sensor_values(
        self, keys: Sequence[str], values: Sequence[Any], *, raise_errors: bool = False
    ) -> list[Sensor]:
        """Set the value of multiple controllable sensors.

        Raises:
            TypeError (only with `raise_errors=True`)
            ValueError (only with `raise_errors=True`)
            CommandError (only with `raise_errors=True`)
        """
        sensors = await self.async_poll_sensors(keys, raise_errors=raise_errors)

        for i, sensor in enumerate(sensors):
            if sensor.value is None:
                continue
            if callable(values[i]):
                value = values[i](sensor.value)
            else:
                value = values[i]
            try:
                await sensor.async_set(self, value)
            except (TypeError, ValueError, CommandError):
                if raise_errors:
                    raise

        return await self.async_poll_sensors(keys, raise_errors=raise_errors)

    async def async_turn_off(self) -> CommandOutput:
        """Turn off by running the `TURN_OFF` action.

        Raises:
            PermissionError
            CommandError
        """
        if not self.allow_turn_off:
            raise PermissionError("Not allowed to turn off")

        return await self.async_run_action(ActionKey.TURN_OFF)

    async def async_restart(self) -> CommandOutput:
        """Restart by running the `RESTART` action.

        Raises:
            CommandError
        """
        return await self.async_run_action(ActionKey.RESTART)
