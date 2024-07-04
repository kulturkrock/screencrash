import base64
import random
import string
import os
from pathlib import Path
from file_handler import FileHandler
from audio_vlc import AudioMixerVLC

class CommandHandler:

    def __init__(self):
        auto_generated_id = ''.join(random.choices(string.ascii_uppercase, k=16))
        self._component_id = os.environ.get("SCREENCRASH_COMPONENT_ID", auto_generated_id)
        self._base_path = Path(__file__).parent.parent / "resources"
        self._mixer = AudioMixerVLC(self._handle_mixer_event)
        self._file_handler = FileHandler(self._base_path)
        self._custom_event_handler = None
        self._sounds = {}

    def set_event_handler(self, event_handler):
        self._custom_event_handler = event_handler

    def _emit(self, data):
        if self._custom_event_handler:
            self._custom_event_handler(data)
        else:
            print(f"Got an event: {data}")

    def _handle_mixer_event(self, event_type, entity_id):
        if event_type == "removed":
            self._emit({"messageType": "effect-removed", "entityId": entity_id})
        elif event_type == "changed" or event_type == "added":
            sound_info = self._mixer.get_sound_info(entity_id)
            data = {
                "messageType": f"effect-{event_type}",
                "entityId": entity_id,
                "name": Path(self._sounds.get(entity_id, "")).stem,
                "duration": sound_info["duration"],
                "currentTime": sound_info["current_time"],
                "lastSync": sound_info["last_sync"],
                "playing": sound_info["playing"],
                "looping": sound_info["looping"],
                "muted": sound_info["muted"],
                "volume": self._mixer.get_volume(entity_id),
            }
            self._emit(data)
        else:
            print(f"Got unhandled event {event_type} with sound_id={entity_id}")

    def _create_error_msg(self, msg):
        result = {"messageType": "cmd-error", "msg": msg}
        return result
    
    def initial_message(self):
        hashes = self._file_handler.get_hashes()
        return {"client": "audio", "files": hashes }

    def handle_message(self, message):
        try:
            cmd = message["command"]
            entity_id = message.get("entityId")
            return self._handle_command(cmd, entity_id, message)
        except Exception as e:
            return self._create_error_msg(f"Failed to carry out command. {e}")

    def _handle_command(self, cmd, entity_id, message):
        result = None
        if cmd == "req_component_info":
            result = self._announce_component_info()
        elif cmd == "add":
            result = self._add_sound(entity_id, message)
        elif cmd == "create":
            result = self._add_video(entity_id, message)
        elif cmd == "play":
            result = self._play(entity_id)
        elif cmd == "pause":
            result = self._pause(entity_id)
        elif cmd == "stop" or cmd == "destroy":
            # Audio uses command 'stop', Video uses command 'destroy'
            result = self._stop(entity_id)
        elif cmd == "set_volume":
            result = self._set_volume(entity_id, message)
        elif cmd == "seek":
            result = self._seek(entity_id, message)
        elif cmd == "toggle_mute":
            result = self._toggle_mute(entity_id)
        elif cmd == "file":
            result = self._file_handler.write_file(Path(message["path"]), base64.b64decode(message["data"]))
        elif cmd in ["hide", "show", "viewport", "layer"] and message.get("type") == "video":
            # These are pure visual commands for video. Ignore.
            pass
        else:
            print("Unhandled message: {}".format(message))
            result = self._create_error_msg("Unsupported command")

        return result

    def _announce_component_info(self):
        self._emit({
            "messageType": "component_info",
            "componentId": self._component_id,
            "componentName": "audio",
            "status": "online"
        })

    def _add_sound(self, entity_id, params):
        path = self._base_path / params["asset"]
        # loops = number of EXTRA times we play the clip (apart from the first) -> 0-indexed
        loops = params.get("loops", 1) - 1
        autostart = params.get("autostart", False)
        self._sounds[entity_id] = path

        if not self._mixer.add(entity_id, path=path, loops=loops, autostart=autostart):
            del self._sounds[entity_id]
            return self._create_error_msg("Unable to add sound. No more channels?")
        else:
            start_position = params.get("start_at", 0)
            if start_position != 0:
                self._mixer.seek(entity_id, start_position)

    def _add_video(self, entity_id, params):
        path = self._base_path / params["asset"]
        loops = params.get("looping", 1) - 1  # pygame uses zero indexing for this
        autostart = params.get("autostart", False)
        self._sounds[entity_id] = path

        # Don't send add event here. The screen component handles that.
        if not self._mixer.add(entity_id, path=path, loops=loops, autostart=autostart, send_add_event=False):
            del self._sounds[entity_id]
            return self._create_error_msg("Unable to add video. No more channels?")
        else:
            start_position = params.get("start_at", 0)
            if start_position != 0:
                self._mixer.seek(entity_id, start_position)

    def _play(self, entity_id):
        if entity_id not in self._sounds:
            return self._create_error_msg("Audio not found. Did you add it?")
        self._mixer.play(entity_id)

    def _pause(self, entity_id):
        if entity_id not in self._sounds:
            return self._create_error_msg("Audio not found. Did you add it?")
        self._mixer.pause(entity_id)

    def _stop(self, entity_id):
        if entity_id not in self._sounds:
            return self._create_error_msg("Audio not found. Did you add it?")
        self._mixer.stop(entity_id)

    def _toggle_mute(self, entity_id):
        if entity_id not in self._sounds:
            return self._create_error_msg("Audio not found. Did you add it?")
        self._mixer.toggle_mute(entity_id)

    def _set_volume(self, entity_id, params):
        if entity_id not in self._sounds:
            return self._create_error_msg("Audio not found. Did you add it?")
        if "volumeLeft" in params or "volumeRight" in params:
            left = params.get("volumeLeft", 0)
            right = params.get("volumeRight", 0)
            self._mixer.set_volume_stereo(entity_id, left, right)
        else:
            self._mixer.set_volume(entity_id, params.get("volume", 50))

    def _seek(self, entity_id, params):
        if entity_id not in self._sounds:
            return self._create_error_msg("Audio not found. Did you add it?")
        position = params.get('position', 0)
        self._mixer.seek(entity_id, position)
