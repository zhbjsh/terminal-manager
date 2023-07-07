"""Terminal manager."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import Any

from .collection import Collection
from .command import ActionCommand, Command, SensorCommand
from .default_collections import ActionKey, SensorKey
from .errors import CommandError
from .event import Event
from .locker import Locker
from .sensor import BinarySensor, NumberSensor, Sensor, TextSensor

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Manager"
DEFAULT_COMMAND_TIMEOUT = 15


@dataclass(frozen=True)
class CommandOutput:
    """The CommandOutput class."""

    timestamp: float
    stdout: list[str]
    stderr: list[str]
    code: int


class Manager(Collection, Locker):
    """The Manager class."""

    def __init__(
        self,
        *,
        name: str = DEFAULT_NAME,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
        collection: Collection | None = None,
        logger: logging.Logger = _LOGGER,
    ) -> None:
        Locker.__init__(self)
        Collection.__init__(self, name)
        self.command_timeout = command_timeout
        self.logger = logger

        if collection:
            self.set_action_commands(collection.action_commands)
            self.set_sensor_commands(collection.sensor_commands)

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
        await command.async_execute(self, variables)

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
            CommandError (`raise_errors`)
        """
        sensors = await self.async_poll_sensors([key], raise_errors=raise_errors)
        return sensors[0]

    async def async_poll_sensors(
        self, keys: Sequence[str], *, raise_errors: bool = False
    ) -> list[Sensor]:
        """Poll multiple sensors.

        Raises:
            CommandError (`raise_errors`)
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
        """Set the value of a sensor.

        Raises:
            TypeError (`raise_errors`)
            ValueError (`raise_errors`)
            CommandError (`raise_errors`)
        """
        sensors = await self.async_set_sensor_values(
            [key], [value], raise_errors=raise_errors
        )
        return sensors[0]

    async def async_set_sensor_values(
        self, keys: Sequence[str], values: Sequence[Any], *, raise_errors: bool = False
    ) -> list[Sensor]:
        """Set the value of multiple sensors.

        Raises:
            TypeError (`raise_errors`)
            ValueError (`raise_errors`)
            CommandError (`raise_errors`)
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
