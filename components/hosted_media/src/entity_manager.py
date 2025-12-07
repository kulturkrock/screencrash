from collections.abc import Callable
from typing import Any


class EntityManager:

    def __init__(self, component_id: str):
        self.component_id = component_id
        self.message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.last_created: str = ""

    def handle_message(self, message):
        cmd = message["command"]
        entity_id = message.get("entityId")
        if cmd == "create":
            result = self.create(entity_id)
        else:
            raise RuntimeError(f"Unsupported command: {cmd}")
        self.broadcast_message(message)
        return result

    def create(self, entity_id: str) -> None:
        self.last_created = entity_id

    def get_component_id(self) -> str:
        return self.component_id

    def get_last_created(self) -> str:
        return self.last_created

    def broadcast_message(self, message: dict[str, Any]) -> None:
        for listener in self.message_listeners:
            listener(message)

    def add_message_listener(self, listener: Callable[[dict[str, Any]], None]) -> None:
        self.message_listeners.append(listener)
