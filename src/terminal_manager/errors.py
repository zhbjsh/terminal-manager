class ManagerError(Exception):
    """Base class for terminal manager errors."""

    def __init__(self, message: str, exc: Exception | None = None):
        super().__init__()
        self.exc = exc
        self.message = message
        self.details = str(exc) if exc else None

    def __str__(self):
        return f"{self.message} ({self.details})" if self.details else self.message


class CommandError(ManagerError):
    """Error to indicate that the command execution failed."""


class NameKeyError(ManagerError):
    """Error to indicate that name and key are not defined."""

    def __init__(self) -> None:
        super().__init__("Name and key not defined")


class InvalidSensorError(ManagerError):
    """Error to indicate that a sensor is invalid."""

    def __init__(self, key: str, details: str) -> None:
        super().__init__(f"Sensor '{key}' is invalid")
        self.details = details
        self.key = key


class CommandLoopError(Exception):
    """Error to indicate that a command loop was detected."""

    def __init__(self, key: str) -> None:
        super().__init__("Command loop detected")
        self.details = f"Key: '{key}'"
        self.key = key
