from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import CommandOutput


class Terminal(ABC):
    @abstractmethod
    async def async_ping(self) -> None:
        """Ping.

        Raises:
            `OfflineError`

        """

    @abstractmethod
    async def async_connect(self) -> None:
        """Connect.

        Raises:
            `ConnectError`

        """

    @abstractmethod
    async def async_disconnect(self) -> None:
        """Disconnect."""

    @abstractmethod
    async def async_execute(self, string: str, timeout: int) -> CommandOutput:
        """Execute.

        Raises:
            `TimeoutError`
            `ExecutionError`

        """
