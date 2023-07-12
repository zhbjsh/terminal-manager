from collections.abc import Callable


class Event:
    def __init__(self) -> None:
        self._subscribers: list[Callable] = []

    def subscribe(self, subscriber) -> Callable:
        """Subscribe."""
        self._subscribers.append(subscriber)

        def callback():
            self.unsubscribe(subscriber)

        return callback

    def unsubscribe(self, subscriber) -> None:
        """Unsubscribe."""
        self._subscribers.remove(subscriber)

    def notify(self, *args, **kwargs) -> None:
        """Notify."""
        for subscriber in self._subscribers:
            subscriber(*args, **kwargs)
