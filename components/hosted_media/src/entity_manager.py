from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Fade:
    fade_from: float
    fade_to: float
    time: float


@dataclass
class Image:
    entity_id: str
    asset: str
    display_name: str
    x: int
    y: int
    width: int | None
    height: int | None
    use_percentage: bool
    opacity: float
    layer: int
    visible: bool
    # fade_in only matters when creating
    # animation and transitions are not supported

    def get_create_message(self, fade: Fade | None = None) -> dict[str, Any]:
        message = {
            "command": "create",
            "type": "image",
            "entityId": self.entity_id,
            "asset": "/".join(Path(self.asset).parts[1:]),
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "usePercentage": self.use_percentage,
            "opacity": self.opacity,
            "layer": self.layer,
            "visible": self.visible,
        }
        if fade is not None:
            message["fadeIn"] = {
                "from": fade.fade_from,
                "to": fade.fade_to,
                "time": fade.time,
            }
        return message

    def get_state_for_core(self) -> dict[str, Any]:
        return {
            "effectType": "image",
            "name": self.display_name,
            "visible": self.visible,
            "opacity": self.opacity,
            "viewport_x": self.x,
            "viewport_y": self.y,
            "viewport_width": self.width,
            "viewport_height": self.height,
            "layer": self.layer,
        }


class EntityManager:

    def __init__(self, component_id: str):
        self.component_id = component_id
        self.webpage_message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.core_message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.entities: dict[str, Image] = {}

    def handle_message(self, message):
        cmd = message["command"]
        type = message.get("type")
        entity_id = message.get("entityId")
        if cmd == "create":
            result = self.create(type, entity_id, message)
        elif cmd == "show":
            result = self.set_visible(entity_id, True)
        elif cmd == "hide":
            result = self.set_visible(entity_id, False)
        elif cmd == "opacity":
            result = self.set_opacity(entity_id, message["opacity"])
        elif cmd == "viewport":
            result = self.set_viewport(
                entity_id,
                message["x"],
                message["y"],
                message["width"],
                message["height"],
                message["usePercentage"],
            )
        elif cmd == "layer":
            result = self.set_layer(entity_id, message["layer"])
        elif cmd == "fade":
            result = self.fade(
                entity_id, message["target"], message["time"], message["stopOnDone"]
            )
        else:
            raise RuntimeError(f"Unsupported command: {cmd}")
        return result

    def create(self, type: str, entity_id: str, message: dict[str, Any]) -> None:
        if entity_id in self.entities:
            print(f"'{entity_id}' already exists, destroying")
            self.destroy(entity_id)
        if type == "image":
            new_entity = Image(
                entity_id=entity_id,
                asset=message["asset"],
                display_name=message.get("displayName", message["asset"]),
                x=message.get("x", 0),
                y=message.get("y", 0),
                width=message.get("width", None),
                height=message.get("height", None),
                use_percentage=message.get("usePercentage", False),
                opacity=message.get("opacity", 1),
                layer=message.get("layer", 0),
                visible=message.get("visible", False),
            )
            if "fadeIn" in message:
                fade = Fade(
                    fade_from=message["fadeIn"]["from"],
                    fade_to=message["fadeIn"]["to"],
                    time=message["fadeIn"]["time"],
                )
            else:
                fade = None
        else:
            raise RuntimeError(f"Unsupported type {type}")
        self.entities[entity_id] = new_entity
        self.broadcast_create_message(new_entity, fade)
        self.broadcast_core_message(
            {"messageType": "effect-added", "entityId": entity_id}
            | new_entity.get_state_for_core()
        )

    def destroy(self, entity_id: str) -> None:
        self.broadcast_webpage_message({"command": "destroy", "entityId": entity_id})
        self.broadcast_core_message(
            {"messageType": "effect-removed", "entityId": entity_id}
        )
        del self.entities[entity_id]

    def set_visible(self, entity_id: str, visible: bool) -> None:
        self.broadcast_webpage_message(
            {"command": "setVisible", "entityId": entity_id, "visible": visible}
        )
        self.entities[entity_id].visible = visible
        self.broadcast_change_message(self.entities[entity_id])

    def set_opacity(self, entity_id: str, opacity: float) -> None:
        self.broadcast_webpage_message(
            {"command": "setOpacity", "entityId": entity_id, "opacity": opacity}
        )
        self.entities[entity_id].opacity = opacity
        self.broadcast_change_message(self.entities[entity_id])

    def set_viewport(
        self,
        entity_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        use_percentage: bool,
    ) -> None:
        self.broadcast_webpage_message(
            {
                "command": "setViewport",
                "entityId": entity_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "usePercentage": use_percentage,
            }
        )
        entity = self.entities[entity_id]
        entity.x = x
        entity.y = y
        entity.width = width
        entity.height = height
        entity.use_percentage = use_percentage
        self.broadcast_change_message(entity)

    def set_layer(self, entity_id: str, layer: int) -> None:
        self.broadcast_webpage_message(
            {"command": "setLayer", "entityId": entity_id, "layer": layer}
        )
        self.entities[entity_id].layer = layer
        self.broadcast_change_message(self.entities[entity_id])

    def fade(
        self,
        entity_id: str,
        fade_to: float,
        time: float,
        destroy_on_end: bool,
    ) -> None:
        self.broadcast_webpage_message(
            {
                "command": "fade",
                "entityId": entity_id,
                "to": fade_to,
                "time": time,
                "destroyOnEnd": destroy_on_end,
            }
        )
        if destroy_on_end:
            del self.entities[entity_id]
            self.broadcast_core_message(
                {"messageType": "effect-removed", "entityId": entity_id}
            )
        else:
            self.entities[entity_id].opacity = fade_to
            self.broadcast_change_message(self.entities[entity_id])

    def get_component_id(self) -> str:
        return self.component_id

    def get_all_entity_create_messages(self) -> list[str]:
        return [e.get_create_message() for e in self.entities.values()]

    def broadcast_create_message(self, entity: Image, fade: Fade | None) -> None:
        self.broadcast_webpage_message(entity.get_create_message(fade))

    def broadcast_webpage_message(self, message: dict[str, Any]) -> None:
        for listener in self.webpage_message_listeners:
            listener(message)

    def broadcast_change_message(self, entity: Image) -> None:
        self.broadcast_core_message(
            {"messageType": "effect-changed", "entityId": entity.entity_id}
            | entity.get_state_for_core()
        )

    def broadcast_core_message(self, message: dict[str, Any]) -> None:
        for listener in self.core_message_listeners:
            listener(message)

    def add_webpage_message_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> None:
        self.webpage_message_listeners.append(listener)

    def add_core_message_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> None:
        self.core_message_listeners.append(listener)
