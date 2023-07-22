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

    @property
    def hostname(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.HOSTNAME):
            return sensor.last_known_value

    @property
    def os_name(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.OS_NAME):
            return sensor.last_known_value

    @property
    def os_version(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.OS_VERSION):
            return sensor.last_known_value

    @property
    def os_architecture(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.OS_ARCHITECTURE):
            return sensor.last_known_value

    @property
    def machine_type(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.MACHINE_TYPE):
            return sensor.last_known_value

    @property
    def network_interface(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.NETWORK_INTERFACE):
            return sensor.last_known_value

    @property
    def mac_address(self) -> str | None:
        if sensor := self.sensors_by_key.get(SensorKey.MAC_ADDRESS):
            return sensor.last_known_value

    @property
    def wake_on_lan(self) -> bool | None:
        if sensor := self.sensors_by_key.get(SensorKey.WAKE_ON_LAN):
            return sensor.last_known_value

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
            try:
                await sensor.async_set(self, values[i])
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
