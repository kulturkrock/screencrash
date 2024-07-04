from typing import Callable, List, Dict

# The arguments depend on the event type, and are not type checked
EventListener = Callable[..., None]


class EventEmitter:
    """
    Something that emits events.

    This is meant to be subclassed.
    """

    def __init__(self):
        self._listeners: Dict[str, List[EventListener]] = {}

    def add_event_listener(self, event_name: str, listener: EventListener):
        """
        Add a listener to an event.

        Parameters
        ----------
        event_name
            The event to listen to
        listener
            A function to be executed when the event fires
        """
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(listener)

    def emit(self, event_name: str, *args):
        """
        Emit an event.

        Parameters
        ----------
        event_name
            The event to emit
        """
        for listener in self._listeners.get(event_name, []):
            listener(*args)
