from __future__ import annotations


class ManagerError(Exception):
    """Base class for terminal manager errors."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__()
        self.message = message
        self.details = details

    def __str__(self):
        return f"{self.message} ({self.details})" if self.details else self.message


class CommandError(ManagerError):
    """Error to indicate a command configuration problem."""

    def __init__(self, details: str) -> None:
        super().__init__("Command error", details)


class ExecutionError(ManagerError):
    """Error to indicate that the command execution failed."""

    def __init__(self, details: str) -> None:
        super().__init__("Execution error", details)


class NameKeyError(ManagerError):
    """Error to indicate that name and key are not defined."""

    def __init__(self) -> None:
        super().__init__("Name and key not defined")


class SensorError(ManagerError):
    """Error to indicate a sensor configuration problem."""

    def __init__(self, key: str, details: str) -> None:
        super().__init__(f"Sensor error: '{key}'", details)
        self.key = key
