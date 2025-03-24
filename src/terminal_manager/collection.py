from __future__ import annotations

from copy import deepcopy
from typing import Any

from .command import ActionCommand, Command, SensorCommand
from .sensor import Sensor


class Collection:
    action_commands: list[ActionCommand]
    sensor_commands: list[SensorCommand]

    _action_names = {}
    _sensor_names = {}

    def __init__(
        self,
        name: str,
        action_commands: list[ActionCommand] | None = None,
        sensor_commands: list[SensorCommand] | None = None,
    ) -> None:
        self.name = name
        self.set_action_commands(action_commands or [])
        self.set_sensor_commands(sensor_commands or [])
        self.check()

    @property
    def commands(self) -> list[Command]:
        return [*self.action_commands, *self.sensor_commands]

    @property
    def action_commands_by_key(self) -> dict[str, ActionCommand]:
        return {command.key: command for command in self.action_commands}

    @property
    def sensor_commands_by_sensor_key(self) -> dict[str, SensorCommand]:
        return {
            key: command
            for command in self.sensor_commands
            for key in command.sensors_by_key
        }

    @property
    def sensors_by_key(self) -> dict[str, Sensor]:
        return {
            key: sensor
            for command in self.sensor_commands
            for key, sensor in command.sensors_by_key.items()
        }

    def set_action_commands(self, action_commands: list[ActionCommand]) -> None:
        """Set the action commands."""
        self.action_commands = []

        for command in action_commands:
            self.add_action_command(command)

    def set_sensor_commands(self, sensor_commands: list[SensorCommand]) -> None:
        """Set the sensor commands."""
        self.sensor_commands = []

        for command in sensor_commands:
            self.add_sensor_command(command)

    def add_action_command(self, command: ActionCommand) -> None:
        """Add an action command.

        Remove existing action command with the same key.
        """
        command = deepcopy(command)

        if command.key in self.action_commands_by_key:
            self.remove_action_command(command.key)
        if not command.name and command.key in self._action_names:
            command.name = self._action_names[command.key]

        self.action_commands.append(command)

    def add_sensor_command(self, command: SensorCommand) -> None:
        """Add a sensor command.

        Remove existing sensors with the same keys.
        """
        command = deepcopy(command)

        for sensor in command.sensors:
            if sensor.key in self.sensors_by_key:
                self.remove_sensor(sensor.key)
            if not sensor.name and sensor.key in self._sensor_names:
                sensor.name = self._sensor_names[sensor.key]

        self.sensor_commands.append(command)

    def get_action_command(self, key: str) -> ActionCommand:
        """Get an action command.

        Raises:
            `KeyError`

        """
        return self.action_commands_by_key[key]

    def get_sensor_command(self, key: str) -> SensorCommand:
        """Get a sensor command.

        Raises:
            `KeyError`

        """
        return self.sensor_commands_by_sensor_key[key]

    def get_sensor(self, key: str) -> Sensor:
        """Get a sensor.

        Raises:
            `KeyError`

        """
        return self.sensors_by_key[key]

    def get_sensor_value(self, key: str, last_known: bool = True) -> Any | None:
        """Get sensor value or `None`."""
        if sensor := self.sensors_by_key.get(key):
            return sensor.last_known_value if last_known else sensor.value

        return None

    def remove_action_command(self, key: str) -> None:
        """Remove an action command.

        Raises:
            `KeyError`

        """
        command = self.get_action_command(key)
        self.action_commands.remove(command)

    def remove_sensor(self, key: str) -> None:
        """Remove a sensor.

        Remove the sensor command if it doesnt have any other sensors.

        Raises:
            `KeyError`

        """
        command = self.get_sensor_command(key)
        command.remove_sensor(key)

        if not command.sensors_by_key:
            self.sensor_commands.remove(command)

    def check(self) -> None:
        """Check commands.

        Raises:
            `SensorError`
            `CommandError`

        """
        for command in self.commands:
            command.check(self)
