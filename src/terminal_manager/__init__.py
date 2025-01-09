"""Terminal manager."""

from .collection import Collection
from .command import PLACEHOLDER_KEY, ActionCommand, Command, SensorCommand
from .default_collections.const import ActionKey, SensorKey
from .errors import (
    CommandError,
    CommandLoopError,
    InvalidSensorError,
    ManagerError,
    NameKeyError,
)
from .event import Event
from .manager import (
    DEFAULT_ALLOW_TURN_OFF,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_NAME,
    CommandOutput,
    Manager,
)
from .sensor import BinarySensor, NumberSensor, Sensor, TextSensor, VersionSensor

__all__ = [
    "Collection",
    "PLACEHOLDER_KEY",
    "ActionCommand",
    "Command",
    "SensorCommand",
    "ActionKey",
    "SensorKey",
    "CommandError",
    "CommandLoopError",
    "InvalidSensorError",
    "ManagerError",
    "NameKeyError",
    "Event",
    "DEFAULT_ALLOW_TURN_OFF",
    "DEFAULT_COMMAND_TIMEOUT",
    "DEFAULT_NAME",
    "CommandOutput",
    "Manager",
    "BinarySensor",
    "NumberSensor",
    "Sensor",
    "TextSensor",
    "VersionSensor",
]
