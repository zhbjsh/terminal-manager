"""Terminal manager."""

from .collection import Collection
from .command import PLACEHOLDER_KEY, ActionCommand, Command, SensorCommand
from .default_collections.const import ActionKey, SensorKey
from .errors import (
    CommandError,
    ExecutionError,
    ManagerError,
    NameKeyError,
    SensorError,
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
    "ExecutionError",
    "ManagerError",
    "NameKeyError",
    "SensorError",
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
