class CommandError(Exception):
    """Error to indicate that the command execution failed."""


class NameKeyError(Exception):
    """Error to indicate that name and key are not defined."""


class InvalidSensorError(Exception):
    """Error to indicate that a sensor is invalid."""

    def __init__(self, key: str, details: str) -> None:
        super().__init__(f"Sensor '{key}' is invalid ({details})")
        self.key = key
        self.details = details


class CommandLoopError(Exception):
    """Error to indicate that a command loop was detected."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Command loop detected ({key})")
        self.key = key
