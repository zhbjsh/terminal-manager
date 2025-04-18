from __future__ import annotations

from enum import StrEnum
from time import time
from typing import TYPE_CHECKING

from .event import Event

if TYPE_CHECKING:
    from .manager import Manager


STATE_NAMES = [
    "online",
    "connected",
    "request",
    "error",
]


class Request(StrEnum):
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    RESTART = "restart"
    CONNECT = "connect"


class State:
    online: bool = False
    connected: bool = False
    request: Request | None = None
    error: bool = False

    def __init__(self, manager: Manager, request_timeouts: dict[str, int]) -> None:
        self._manager = manager
        self._request_timeouts = request_timeouts
        self._request_timestamp = time()
        self.on_change = Event()

    def __setattr__(self, name, value):
        prev_value = getattr(self, name, None)
        super().__setattr__(name, value)

        if name not in STATE_NAMES or value == prev_value:
            return

        if name == "request":
            self._request_timestamp = time()

        self._manager.log(f"state.{name} => {value}")
        self.on_change.notify(self)

    @property
    def starting_up(self) -> bool:
        return self.request in [Request.TURN_ON, Request.CONNECT]

    @property
    def shutting_down(self) -> bool:
        return self.request in [Request.TURN_OFF, Request.RESTART]

    @property
    def request_expired(self) -> bool:
        if self.request:
            timeout = self._request_timeouts[self.request]
            return time() - self._request_timestamp > timeout
        return False

    def update(self) -> None:
        """Reset error and set request to `None` if expired."""
        if self.error:
            self.error = False
        if self.request_expired:
            self.request = None

    def handle_ping_error(self) -> None:
        if self.request == Request.TURN_OFF:
            self.request = None
        if self.request == Request.RESTART:
            self.request = Request.TURN_ON
        self.online = False

    def handle_ping_success(self) -> None:
        if self.request == Request.TURN_ON:
            self.request = Request.CONNECT
        self.online = True

    def handle_connect_error(self) -> None:
        self.error = True

    def handle_connect_success(self) -> None:
        if self.request == Request.CONNECT:
            self.request = None
        self.connected = True

    def handle_execute_error(self) -> None:
        self.error = True

    def handle_disconnect(self) -> None:
        self.connected = False

    def handle_turn_on(self) -> None:
        self.request = Request.TURN_ON

    def handle_turn_off(self) -> None:
        self.request = Request.TURN_OFF

    def handle_restart(self) -> None:
        self.request = Request.RESTART
