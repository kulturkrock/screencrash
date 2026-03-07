from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
from pathlib import Path
import time
from media_streamer import MediaStreamer
import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
import os

CLIENT_PRECISE_ACTION_DELAY = float(
    os.environ.get("SCREENCRASH_HOSTED_MEDIA_CLIENT_PRECISE_ACTION_DELAY", "0.2")
)


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
class Audio:
    entity_id: str
    asset: str
    display_name: str
    muted: bool
    volume: int
    stream_id: str  # Different from entity ID so the browser doesn't cache the video
    media_streamer: MediaStreamer

    def get_create_message(self, fade: Fade | None = None) -> dict[str, Any]:
        message = {
            "command": "create",
            "type": "audio",
            "entityId": self.entity_id,
            "streamId": self.stream_id,
            "asset": "/".join(Path(self.asset).parts[1:]),
            "muted": self.muted,
            "volume": self.volume,
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
            "effectType": "audio",
            "name": self.display_name,
            "muted": self.muted,
            "volume": self.volume,
            "duration": self.media_streamer.get_duration(),
            "currentTime": self.media_streamer.get_position(),
            "lastSync": time.time() * 1000,
            "playing": self.media_streamer.is_playing(),
            "looping": self.media_streamer.is_looping(),
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
    muted: bool
    volume: int
    stream_id: str  # Different from entity ID so the browser doesn't cache the video
    media_streamer: MediaStreamer

    def get_create_message(self, fade: Fade | None = None) -> dict[str, Any]:
        message = {
            "command": "create",
            "type": "video",
            "entityId": self.entity_id,
            "streamId": self.stream_id,
            "asset": "/".join(Path(self.asset).parts[1:]),
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "usePercentage": self.use_percentage,
            "opacity": self.opacity,
            "layer": self.layer,
            "visible": self.visible,
            "muted": self.muted,
            "volume": self.volume,
            "hasVideo": self.media_streamer.has_video(),
            "hasAudio": self.media_streamer.has_audio(),
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
            "muted": self.muted,
            "volume": self.volume,
            "duration": self.media_streamer.get_duration(),
            "currentTime": self.media_streamer.get_position(),
            "lastSync": time.time() * 1000,
            "playing": self.media_streamer.is_playing(),
            "looping": self.media_streamer.is_looping(),
        }


class EntityManager:

    def __init__(self, component_id: str, asset_dir: Path):
        self.component_id = component_id
        self.asset_dir = asset_dir
        self.webpage_message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.create_media_streamer_listeners: list[
            Callable[[str, MediaStreamer], None]
        ] = []
        self.delete_media_streamer_listeners: list[Callable[[str], None]] = []
        self.core_message_listeners: list[Callable[[dict[str, Any]]]] = []
        self.entities: dict[str, Image | Audio | Video] = {}

    def _delete_entity(self, entity_id: str):
        self.broadcast_core_message(
            {"messageType": "effect-removed", "entityId": entity_id}
        )
        entity = self.entities[entity_id]
        if isinstance(entity, Video):
            entity.media_streamer.stop()
            for listener in self.delete_media_streamer_listeners:
                listener(entity.stream_id)
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
            # The volume of pure audio effects are given in 0-100 in the opus, but for our purposes fade is 0-1.
            # This is because audio fade should work the same for video and audio effects.
            target = (
                message["target"] / 100
                if message["type"] == "audio"
                else message["target"]
            )
            result = self.fade(
                entity_id, target, message["time"], message["stopOnDone"]
            )
        elif cmd == "play":
            result = self.play(entity_id)
        elif cmd == "pause":
            result = self.pause(entity_id)
        elif cmd == "seek":
            result = self.seek(entity_id, message["position"])
        elif cmd == "toggle_mute":
            result = self.toggle_mute(entity_id)
        elif cmd == "set_volume":
            result = self.set_volume(entity_id, message["volume"])
        elif cmd == "set_loops":
            result = self.set_loops(entity_id, message["looping"])
        elif cmd == "set_loop_times":
            result = self.set_loop_times(
                entity_id, message["loop_start"], message["loop_end"]
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
        elif type == "video" or type == "audio":
            if "fadeOut" in message:
                fade_out_time = message["fadeOut"]
                will_end_advance_warning = fade_out_time + CLIENT_PRECISE_ACTION_DELAY
                will_end_callback = lambda end_time: self._fade_at_time(
                    entity_id=entity_id,
                    fade_to=0,
                    fade_start_time=end_time - timedelta(seconds=fade_out_time),
                    fade_duration=fade_out_time,
                    destroy_on_end=message.get("destroyOnEnd", True),
                )
            elif message.get("destroyOnEnd", True):
                will_end_advance_warning = CLIENT_PRECISE_ACTION_DELAY
                will_end_callback = lambda end_time: self._delete_at_time(
                    entity_id,
                    end_time + timedelta(seconds=0.1),  # Just a bit later, just in case
                )
            else:
                will_end_advance_warning = CLIENT_PRECISE_ACTION_DELAY
                will_end_callback = lambda end_time: None

            sync_event_callback = (
                lambda playout_time, file_time: self.broadcast_webpage_message(
                    {
                        "command": "syncTime",
                        "entityId": entity_id,
                        "playoutTime": playout_time.isoformat(),
                        "mediaTimeSeconds": file_time,
                    }
                )
            )
            streamer = MediaStreamer(
                asset=message["asset"],
                asset_dir=self.asset_dir,
                loop_start=message.get("loop_start", "00:00:00.000000"),
                loop_end=message.get("loop_end", "end"),
                loops=message.get("looping", 1),
                start_at=message.get("start_at", 0),
                effect_changed_callback=lambda: (
                    self.broadcast_change_message(self.entities[entity_id])
                    if entity_id in self.entities
                    else None
                ),
                will_end_advance_warning=will_end_advance_warning,
                will_end_callback=will_end_callback,
                sync_event_callback=sync_event_callback,
            )
            stream_id = (
                entity_id
                + "-"
                + "".join(random.choice(string.ascii_lowercase) for i in range(20))
            )
            for listener in self.create_media_streamer_listeners:
                listener(stream_id, streamer)
            if type == "video":
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
                    muted=False,
                    volume=100,
                    stream_id=stream_id,
                    media_streamer=streamer,
                )
            elif type == "audio":
                new_entity = Audio(
                    entity_id=entity_id,
                    asset=message["asset"],
                    display_name=message.get("displayName", message["asset"]),
                    muted=False,
                    volume=100,
                    stream_id=stream_id,
                    media_streamer=streamer,
                )
            else:
                raise RuntimeError(f"'{type}' is not 'audio' or 'video'")
        else:
            raise RuntimeError(f"Unsupported type {type}")
        if "fadeIn" in message:
            # The volume of pure audio effects are given in 0-100 in the opus, but for our purposes fade is 0-1.
            # This is because audio fade should work the same for video and audio effects.
            fade_from = (
                message["fadeIn"]["from"] / 100
                if message["type"] == "audio"
                else message["fadeIn"]["from"]
            )
            fade_to = (
                message["fadeIn"]["to"] / 100
                if message["type"] == "audio"
                else message["fadeIn"]["to"]
            )
            fade = Fade(
                fade_from=fade_from,
                fade_to=fade_to,
                time=message["fadeIn"]["time"],
            )
        else:
            fade = None
        self.entities[entity_id] = new_entity
        self.broadcast_create_message(new_entity, fade)
        if message.get("autostart", True):
            self.play(entity_id)
        self.broadcast_core_message(
            {"messageType": "effect-added", "entityId": entity_id}
            | new_entity.get_state_for_core()
        )

    def destroy(self, entity_id: str) -> None:
        self.broadcast_webpage_message(
            {"command": "destroy", "entityId": entity_id, "time": None}
        )
        self._delete_entity(entity_id)

    def set_visible(self, entity_id: str, visible: bool) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Audio):
            raise RuntimeError(
                f"Tried to set visible for {entity_id}, but it is not supported"
            )
        self.broadcast_webpage_message(
            {"command": "setVisible", "entityId": entity_id, "visible": visible}
        )
        entity.visible = visible
        self.broadcast_change_message(entity)

    def set_opacity(self, entity_id: str, opacity: float) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Audio):
            raise RuntimeError(
                f"Tried to set opacity for {entity_id}, but it is not supported"
            )
        self.broadcast_webpage_message(
            {"command": "setOpacity", "entityId": entity_id, "opacity": opacity}
        )
        entity.opacity = opacity
        self.broadcast_change_message(entity)

    def set_viewport(
        self,
        entity_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        use_percentage: bool,
    ) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Audio):
            raise RuntimeError(
                f"Tried to set viewport for {entity_id}, but it is not supported"
            )
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
        entity.x = x
        entity.y = y
        entity.width = width
        entity.height = height
        entity.use_percentage = use_percentage
        self.broadcast_change_message(entity)

    def set_layer(self, entity_id: str, layer: int) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Audio):
            raise RuntimeError(
                f"Tried to set layer for {entity_id}, but it is not supported"
            )
        self.broadcast_webpage_message(
            {"command": "setLayer", "entityId": entity_id, "layer": layer}
        )
        entity.layer = layer
        self.broadcast_change_message(entity)

    def _delete_at_time(self, entity_id: str, delete_time: datetime) -> None:
        asyncio.create_task(self._async_delete_at_time(entity_id, delete_time))

    async def _async_delete_at_time(
        self, entity_id: str, delete_time: datetime
    ) -> None:
        self.broadcast_webpage_message(
            {
                "command": "destroy",
                "entityId": entity_id,
                "time": delete_time.isoformat(),
            }
        )
        delay = delete_time.timestamp() - time.time()
        await asyncio.sleep(delay)
        self._delete_entity(entity_id)

    def _fade_at_time(
        self,
        entity_id: str,
        fade_to: float,
        fade_start_time: datetime,
        fade_duration: float,
        destroy_on_end: bool,
    ) -> None:
        asyncio.create_task(
            self._async_fade_at_time(
                entity_id, fade_to, fade_start_time, fade_duration, destroy_on_end
            )
        )

    async def _async_fade_at_time(
        self,
        entity_id: str,
        fade_to: float,
        fade_start_time: datetime,
        fade_duration: float,
        destroy_on_end: bool,
    ) -> None:
        entity = self.entities[entity_id]
        self.broadcast_webpage_message(
            {
                "command": "fade",
                "entityId": entity_id,
                "to": fade_to,
                "time": fade_duration,
                "fadeStartTime": fade_start_time.isoformat(),
            }
        )
        delay = fade_start_time.timestamp() - time.time()
        await asyncio.sleep(delay)
        if destroy_on_end:
            # We wait one second longer than the fade should take, just to be sure it's done
            self._delete_at_time(
                entity_id,
                datetime.now(tz=timezone.utc) + timedelta(seconds=fade_duration + 1),
            )
        else:
            if isinstance(entity, Video) or isinstance(entity, Image):
                entity.opacity = fade_to
            if isinstance(entity, Video) or isinstance(entity, Audio):
                entity.volume = round(100 * fade_to)
            self.broadcast_change_message(entity)

    def fade(
        self,
        entity_id: str,
        fade_to: float,
        time: float,
        destroy_on_end: bool,
    ) -> None:
        entity = self.entities[entity_id]
        fade_audio = isinstance(entity, Video) or isinstance(entity, Audio)
        fade_video = isinstance(entity, Video) or isinstance(entity, Image)
        self.broadcast_webpage_message(
            {
                "command": "fade",
                "entityId": entity_id,
                "to": fade_to,
                "time": time,
                "fadeStartTime": None,
                "fadeAudio": fade_audio,
                "fadeVideo": fade_video,
            }
        )
        if destroy_on_end:
            # We wait one second longer than the fade should take, just to be sure it's done
            self._delete_at_time(
                entity_id, datetime.now(tz=timezone.utc) + timedelta(seconds=time + 1)
            )
        else:
            if isinstance(entity, Video) or isinstance(entity, Image):
                entity.opacity = fade_to
            if isinstance(entity, Video) or isinstance(entity, Audio):
                entity.volume = round(100 * fade_to)

            self.broadcast_change_message(entity)

    def play(self, entity_id: str) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(
                f"Tried to play/resume {entity_id}, which does not support it"
            )
        clients_play_time = datetime.now(tz=timezone.utc) + timedelta(
            seconds=CLIENT_PRECISE_ACTION_DELAY
        )
        self.broadcast_webpage_message(
            {
                "command": "play",
                "entityId": entity_id,
                "time": clients_play_time.isoformat(),
            }
        )
        entity.media_streamer.play(clients_play_time)
        self.broadcast_change_message(entity)

    def pause(self, entity_id: str) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(f"Tried to pause {entity_id}, which does not support it")
        clients_pause_time = datetime.now(tz=timezone.utc) + timedelta(
            seconds=CLIENT_PRECISE_ACTION_DELAY
        )
        pause_time_in_stream = entity.media_streamer.pause(clients_pause_time)
        self.broadcast_webpage_message(
            {
                "command": "pause",
                "entityId": entity_id,
                "time": clients_pause_time.isoformat(),
                "pauseTimeInStream": pause_time_in_stream,
            }
        )
        self.broadcast_change_message(entity)

    def seek(self, entity_id: str, position: float) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(
                f"Tried to set position in {entity_id}, which does not support it"
            )
        entity.media_streamer.seek(position)
        self.broadcast_change_message(entity)

    def toggle_mute(self, entity_id: str) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(
                f"Tried to toggle mute on {entity_id}, which does not support it"
            )
        entity.muted = not entity.muted
        self.broadcast_webpage_message(
            {
                "command": "mute" if entity.muted else "unmute",
                "entityId": entity_id,
            }
        )
        self.broadcast_change_message(entity)

    def set_volume(self, entity_id: str, volume: int) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(
                f"Tried to set volume on {entity_id}, which does not support it"
            )
        entity.volume = volume
        self.broadcast_webpage_message(
            {"command": "setVolume", "entityId": entity_id, "volume": volume}
        )
        self.broadcast_change_message(entity)

    def set_loops(self, entity_id: str, loops: int) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(
                f"Tried to set loops on {entity_id}, which does not support it"
            )
        entity.media_streamer.set_loop_count(loops)

    def set_loop_times(self, entity_id: str, loop_start: str, loop_end: str) -> None:
        entity = self.entities[entity_id]
        if isinstance(entity, Image):
            raise RuntimeError(
                f"Tried to set loop times on {entity_id}, which does not support it"
            )
        entity.media_streamer.set_loop_times(loop_start, loop_end)

    def get_component_id(self) -> str:
        return self.component_id

    def get_all_entity_create_messages(self) -> list[dict[str, Any]]:
        return [e.get_create_message() for e in self.entities.values()]

    def broadcast_create_message(
        self, entity: Image | Audio | Video, fade: Fade | None
    ) -> None:
        self.broadcast_webpage_message(entity.get_create_message(fade))

    def broadcast_webpage_message(self, message: dict[str, Any]) -> None:
        for listener in self.webpage_message_listeners:
            listener(message)

    def broadcast_change_message(self, entity: Image | Audio | Video) -> None:
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

    def add_create_media_streamer_listener(
        self, listener: Callable[[str, MediaStreamer], None]
    ):
        self.create_media_streamer_listeners.append(listener)

    def add_delete_media_streamer_listener(self, listener: Callable[[str], None]):
        self.delete_media_streamer_listeners.append(listener)

    def add_core_message_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> None:
        self.core_message_listeners.append(listener)
