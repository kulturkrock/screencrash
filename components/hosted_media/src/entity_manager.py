from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
from pathlib import Path
import time
from video_streamer import VideoStreamer
import asyncio


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


@dataclass
class Video:
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
    loops_left: int
    # autostart only matters when creating
    # seamless and mimeCodec are specific to other media component
    # start_at only matters when creating
    fade_out: int
    destroy_on_end: bool
    playing: bool
    position: float  # How can this be synced with webpage? Get dynamically somehow?
    video_streamer: VideoStreamer

    def get_create_message(self, fade: Fade | None = None) -> dict[str, Any]:
        message = {
            "command": "create",
            "type": "video",
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
            # Autostart? Seek?
            # I AM HERE: Serve from a url already now. Create a new object for handling the video, that streams.
            # Do we play/pause in browser or backend? What about seek?
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
            "effectType": "video",
            "name": self.display_name,
            "visible": self.visible,
            "opacity": self.opacity,
            "viewport_x": self.x,
            "viewport_y": self.y,
            "viewport_width": self.width,
            "viewport_height": self.height,
            "layer": self.layer,
            "duration": 10,  # TODO: real value
            "currentTime": self.position,
            "lastSync": time.time() * 1000,
            "playing": self.playing,
            "looping": self.loops_left > 0,
        }


class EntityManager:

    def __init__(self, component_id: str):
        self.component_id = component_id
        self.webpage_message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.create_video_streamer_listeners: list[
            Callable[[str, VideoStreamer], None]
        ] = []
        self.delete_video_streamer_listeners: list[Callable[[str], None]] = []
        self.core_message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.entities: dict[str, Image | Video] = {}

    def _delete_entity(self, entity_id: str):
        self.broadcast_webpage_message({"command": "destroy", "entityId": entity_id})
        self.broadcast_core_message(
            {"messageType": "effect-removed", "entityId": entity_id}
        )
        entity = self.entities[entity_id]
        if isinstance(entity, Video):
            entity.video_streamer.stop()
            for listener in self.delete_video_streamer_listeners:
                listener(entity_id)
        del self.entities[entity_id]

    def handle_message(self, message):
        cmd = message["command"]
        type = message.get("type")
        entity_id = message.get("entityId")
        if cmd == "create":
            result = self.create(type, entity_id, message)
        elif cmd == "destroy":
            result = self.destroy(entity_id)
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
        elif type == "video":
            streamer = VideoStreamer(message["asset"])
            for listener in self.create_video_streamer_listeners:
                listener(entity_id, streamer)
            streamer.start()
            new_entity = Video(
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
                loops_left=message.get("looping", 1),
                fade_out=message.get("fadeOut", 0),
                destroy_on_end=message.get("destroyOnEnd", True),
                playing=message.get("autostart", True),
                position=message.get("start_at", 0),
                video_streamer=streamer,
            )
        else:
            raise RuntimeError(f"Unsupported type {type}")
        if "fadeIn" in message:
            fade = Fade(
                fade_from=message["fadeIn"]["from"],
                fade_to=message["fadeIn"]["to"],
                time=message["fadeIn"]["time"],
            )
        else:
            fade = None
        self.entities[entity_id] = new_entity
        self.broadcast_create_message(new_entity, fade)
        self.broadcast_core_message(
            {"messageType": "effect-added", "entityId": entity_id}
            | new_entity.get_state_for_core()
        )

    def destroy(self, entity_id: str) -> None:
        self._delete_entity(entity_id)

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

    async def _delete_with_delay(self, entity_id: str, delay: float) -> None:
        await asyncio.sleep(delay)
        self._delete_entity(entity_id)

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
            }
        )
        if destroy_on_end:
            # We wait one second longer than the fade should take, just to be sure it's done
            asyncio.create_task(self._delete_with_delay(entity_id, time + 1))
        else:
            self.entities[entity_id].opacity = fade_to
            self.broadcast_change_message(self.entities[entity_id])

    def get_component_id(self) -> str:
        return self.component_id

    def get_all_entity_create_messages(self) -> list[dict[str, Any]]:
        return [e.get_create_message() for e in self.entities.values()]

    def broadcast_create_message(
        self, entity: Image | Video, fade: Fade | None
    ) -> None:
        self.broadcast_webpage_message(entity.get_create_message(fade))

    def broadcast_webpage_message(self, message: dict[str, Any]) -> None:
        for listener in self.webpage_message_listeners:
            listener(message)

    def broadcast_change_message(self, entity: Image | Video) -> None:
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

    def add_create_video_streamer_listener(
        self, listener: Callable[[str, VideoStreamer], None]
    ):
        self.create_video_streamer_listeners.append(listener)

    def add_delete_video_streamer_listener(self, listener: Callable[[str], None]):
        self.delete_video_streamer_listeners.append(listener)

    def add_core_message_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> None:
        self.core_message_listeners.append(listener)
