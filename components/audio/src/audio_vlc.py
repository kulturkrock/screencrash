import os
import time
import threading
from functools import partial
import platform
import struct

# -------------------- TWEAKS FOR VLC -------------------------
is_32bit = (struct.calcsize("P") * 8 == 32)
if platform.system() == "Windows":
    if is_32bit:
        os.add_dll_directory(r"C:\Program Files (x86)\VideoLAN\VLC")
    else:
        os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")
elif platform.system() == "Linux":
    # See https://github.com/pyinstaller/pyinstaller/issues/4506
    if is_32bit:
        os.environ["VLC_PLUGIN_PATH"] = "/usr/lib/vlc/plugins"
    else:
        os.environ["VLC_PLUGIN_PATH"] = "/usr/lib64/vlc/plugins"
elif platform.system() == "Darwin":
    # Todo: Fix for Mac OS X
    raise RuntimeError("MacOS X not supported yet")
# -------------------------------------------------------------

import vlc


class AudioMixerVLC:
    """
    Implementation of the AudioMixer for VLC. Documentation for 
    the VLC MediaPlayer API can be found here:
    https://www.olivieraubert.net/vlc/python-ctypes/doc/vlc.MediaPlayer-class.html
    """

    def __init__(self, event_callback):
        self._event_callback = event_callback
        self._sounds = {}
        self._looping = {}

    def _emit(self, event, sound_id, delay=0.1):
        if self._event_callback:
            # We don't wait for commands to go through so sometimes
            # we get an erronous state if we read state immediately
            # after changing things. This is ugly, but works.
            time.sleep(delay)
            self._event_callback(event, sound_id)
        else:
            print(f"Got event {event} for {sound_id}")

    def _playback_reached_end(self, sound_id, _event):
        (sound_path, loops_left) = self._looping.get(sound_id, ("", 0))
        if loops_left != 0 and sound_id in self._sounds:
            if loops_left > 0:
                self._looping[sound_id] = (sound_path, loops_left-1)
            threading.Thread(target=partial(self._restart_song, sound_id, sound_path)).start()
        else:
            self._sound_stopped(sound_id)

    def _sound_stopped(self, sound_id, _event=None):
        # Always run in own thread to avoid dead lock in
        # VLC instance event thread
        threading.Thread(target=partial(self._stop_song, sound_id)).start()

    def _restart_song(self, sound_id, path):
        self._sounds[sound_id].set_mrl(path)
        self._sounds[sound_id].play()

    def _stop_song(self, sound_id):
        if sound_id in self._sounds:
            mediaplayer = self._sounds[sound_id]
            instance = mediaplayer.get_instance()
            mediaplayer.get_media().release()
            mediaplayer.release()
            instance.release()
            del self._sounds[sound_id]
        self._emit("removed", sound_id, 0.0)

    def add(self, sound_id, path, loops=0, autostart=False, send_add_event=True):
        instance = vlc.Instance("--vout=dummy")
        player = instance.media_player_new()
        player.set_mrl(path)

        events = player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, partial(self._playback_reached_end, sound_id))
        events.event_attach(vlc.EventType.MediaPlayerStopped, partial(self._sound_stopped, sound_id))

        self._sounds[sound_id] = player
        self._looping[sound_id] = (path, loops)

        player.play()
        if not autostart:
            player.pause()

        if send_add_event:
            self._emit("added", sound_id)

        return True

    def play(self, sound_id):
        player = self._sounds.get(sound_id)
        if player:
            if not player.is_playing():
                player.play()
                self._emit("changed", sound_id)
        return player is not None

    def pause(self, sound_id):
        player = self._sounds.get(sound_id)
        if player:
            if player.is_playing():
                player.pause()
                self._emit("changed", sound_id)
        return player is not None

    def stop(self, sound_id):
        player = self._sounds.get(sound_id)
        if player:
            player.stop()
        return player is not None

    def is_running(self, sound_id):
        player = self._sounds.get(sound_id)
        return player and player.is_playing()

    def get_volume(self, sound_id):
        player = self._sounds.get(sound_id)
        return player.audio_get_volume() if player else 0

    def get_duration(self, sound_id):
        player = self._sounds.get(sound_id)
        return player.get_length() / 1000 if player else 0

    def get_sound_info(self, sound_id):
        player = self._sounds.get(sound_id)
        if player:
            return {
                "duration": player.get_length() / 1000,
                "current_time": player.get_time() / 1000,
                "last_sync": int(time.time() * 1000),
                "playing": player.is_playing() == 1,
                "looping": self._looping.get(sound_id, ("", 0))[1] != 0,
                "muted": player.audio_get_mute() == True,
            }
        return None

    def set_volume(self, sound_id, volume, skip_event=False):
        player = self._sounds.get(sound_id)
        if player:
            player.audio_set_volume(volume)
            self._emit("changed", sound_id, 0.04)

    def set_volume_stereo(self, sound_id, volume_left, volume_right, skip_event=False):
        self.set_volume((volume_left+volume_right)//2)

    def toggle_mute(self, sound_id):
        player = self._sounds.get(sound_id)
        if player:
            player.audio_toggle_mute()
            self._emit("changed", sound_id)

    # Position is given in seconds (may be float)
    def seek(self, sound_id, position):
        player = self._sounds.get(sound_id)
        if player:
            player.set_time(int(position*1000))
            self._emit("changed", sound_id)