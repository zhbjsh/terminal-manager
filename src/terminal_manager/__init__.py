"""Terminal manager."""

from .collection import Collection
from .command import PLACEHOLDER_KEY, ActionCommand, Command, SensorCommand
from .default_collections.const import ACTION_NAMES, SENSOR_NAMES, ActionKey, SensorKey
from .error import (
    AuthenticationError,
    CommandError,
    ConnectError,
    ExecutionError,
    ManagerError,
    NameKeyError,
    OfflineError,
    SensorError,
)
from .event import Event
from .manager import (
    DEFAULT_ALLOW_TURN_OFF,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_DISCONNECT_MODE,
    DEFAULT_NAME,
    CommandOutput,
    Manager,
)
from .sensor import BinarySensor, NumberSensor, Sensor, TextSensor, VersionSensor
from .state import Request, State
from .terminal import Terminal

__all__ = [
    "Collection",
    "PLACEHOLDER_KEY",
    "ActionCommand",
    "Command",
    "SensorCommand",
    "ACTION_NAMES",
    "SENSOR_NAMES",
    "ActionKey",
    "SensorKey",
    "AuthenticationError",
    "CommandError",
    "ConnectError",
    "ExecutionError",
    "ManagerError",
    "NameKeyError",
    "OfflineError",
    "SensorError",
    "Event",
    "DEFAULT_ALLOW_TURN_OFF",
    "DEFAULT_COMMAND_TIMEOUT",
    "DEFAULT_DISCONNECT_MODE",
    "DEFAULT_NAME",
    "CommandOutput",
    "Manager",
    "BinarySensor",
    "NumberSensor",
    "Sensor",
    "TextSensor",
    "VersionSensor",
    "Request",
    "State",
    "Terminal",
]
