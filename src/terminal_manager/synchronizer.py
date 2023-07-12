from __future__ import annotations

import asyncio
import inspect
from collections.abc import Coroutine
from functools import wraps


def locked(coro: Coroutine):
    @wraps(coro)
    async def wrapper(obj: Synchronizer, *args, **kwargs):
        async with obj.lock:
            return await coro(obj, *args, **kwargs)

    return wrapper


class AsyncRLock(asyncio.Lock):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._task = None
        self._depth = 0

    async def acquire(self) -> None:
        if self._task is None or self._task != asyncio.current_task():
            await super().acquire()
            self._task = asyncio.current_task()
            assert self._depth == 0
        self._depth += 1

    def release(self) -> None:
        if self._depth > 0:
            self._depth -= 1
        if self._depth == 0:
            super().release()
            self._task = None


class Synchronizer:
    def __init__(self) -> None:
        self.lock = AsyncRLock()

    def __init_subclass__(cls, **kwargs):
        for name in cls.__dict__:
            attr = getattr(cls, name)
            if inspect.iscoroutinefunction(attr):
                setattr(cls, name, locked(attr))
