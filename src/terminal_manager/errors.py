class CommandError(Exception):
    """Error to indicate that the command execution failed."""


class NameKeyError(Exception):
    """Error to indicate that name and key are not defined."""


class InvalidSensorError(Exception):
    """Error to indicate that a sensor is invalid."""


class CommandLoopError(Exception):
    """Error to indicate that a command loop was detected."""
