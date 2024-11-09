class CommandError(Exception):
    """Error to indicate that the command execution failed."""


class NameKeyError(Exception):
    """Error to indicate that name and key are not defined."""


class InvalidRequiredSensorError(Exception):
    """Error to indicate that a required sensor is invalid."""
