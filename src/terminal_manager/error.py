from __future__ import annotations


class ManagerError(Exception):
    """Base class for terminal manager errors."""

    message = "Manager error"

    def __init__(self, details: str | None = None):
        super().__init__()
        self.details = details

    def __str__(self):
        return f"{self.message} ({self.details})" if self.details else self.message


class NameKeyError(ManagerError):
    """Error to indicate that name and key are not defined."""

    message = "Name and key not defined"


class CommandError(ManagerError):
    """Error to indicate a command configuration problem."""

    message = "Command error"


class SensorError(ManagerError):
    """Error to indicate a sensor configuration problem."""

    def __init__(self, key: str, details: str) -> None:
        super().__init__(details)
        self.key = key
        self.message = f"Sensor error: {key}"


class OfflineError(ManagerError):
    """Error to indicate that the host is offline."""

    def __init__(self, host: str, details: str | None = None) -> None:
        super().__init__(details)
        self.host = host
        self.message = f"Host {host} is offline"


class ConnectError(ManagerError):
    """Error to indicate that the connection failed."""

    message = "Connection failed"


class AuthenticationError(ConnectError):
    """Error to indicate that the authentication failed."""

    message = "Authentication failed"


class ExecutionError(ManagerError):
    """Error to indicate that the command execution failed."""

    message = "Execution failed"
