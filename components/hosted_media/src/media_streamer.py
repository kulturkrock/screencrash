from dataclasses import dataclass
from pathlib import Path
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import typing
import asyncio
import time
import traceback
import io

import av
import av.container

from settings import (
    STREAM_DELAY,
    SYNC_CLIENTS,
    SYNC_EVENT_INTERVAL,
    TIME_BEFORE_FIRST_SYNC,
)
from av_utils import (
    convert_to_av_time_base,
    packet_fully_before_timestamp,
    stitch_audio_frames,
)
from util import assert_and_get_one

# This makes some assumptions about the video file:
# 1. The packets are ordered with nondecreasing timestamps, even across streams
# 2. There is a keyframe after the start of each looping portion, soon enough that
#    video frames can be dropped until then
# 3. The video codec is allowed in webm
# 4. Audio packets have only one audio frame
# 5. The audio codec does not use keyframes
# 6. The audio codec is lossless (or at least FFmpeg's decoder does not have state)
# 7. 1 000 000 can be divided by the audio sample rate with no remainder
# 8. Both the audio and video stream start at time 0
#
# You can create a file that matches this by:
# ffmpeg -i input.mp4 -c:v vp9 -c:a flac tmp_nokeyframes.mp4
# Open tmp_nokeyframes.mp4 in audacity, find very exact timestamps to loop
# ffmpeg -i tmp_nokeyframes.mp4 -c:v vp9 -c:a copy -force_key_frames 00:00:01.212720,00:00:27.054200 output.mp4
# (Replace the timestamps of -force_key_frames with your loop start times)


def _parse_timestamp(timestamp: str) -> int:  # In av.time_base
    parsed_time = datetime.strptime(timestamp, "%H:%M:%S.%f")
    hours = parsed_time.hour
    minutes = parsed_time.minute
    seconds = parsed_time.second
    microseconds = parsed_time.microsecond
    total_microseconds = (
        hours * 3600 * 1_000_000
        + minutes * 60 * 1_000_000
        + seconds * 1_000_000
        + microseconds
    )
    assert av.time_base == 1_000_000  # Just in case it changes in an update somehow
    return total_microseconds


@dataclass
class _Playing:
    clients_start_time: float
    start_time_in_stream: int  # In av.time_base


@dataclass
class _Paused:
    pause_time_in_stream: int  # In av.time_base


@dataclass
class _JumpInProgress:
    jumping_to: int  # in av.time_base
    jumping_from: int  # in av.time_base
    partial_loop_end_packet: av.Packet


@dataclass
class _VideoOutput:
    file_path: Path
    file_handle: io.BufferedWriter
    container: av.container.OutputContainer


@dataclass
class _AudioOutput:
    file_path: Path
    file_handle: io.BufferedWriter
    container: av.container.OutputContainer
    stream: av.AudioStream


class MediaStreamer:

    def __init__(
        self,
        asset: Path,
        asset_dir: Path,
        loop_start: str,
        loop_end: str,
        loops: int,
        start_at: float,
        effect_changed_callback: Callable[[], None],
        # How far in advance will_end_callback should fire. It may fire earlier, or slightly later
        will_end_advance_warning: float,
        will_end_callback: Callable[
            [datetime], None
        ],  # Function that takes the expected end of the clients' played streams
        sync_event_callback: Callable[
            [datetime, float], None
        ],  # Function that takes the playout time and the corresponding time in the output file
    ):
        # Setup callbacks
        self.effect_changed_callback = effect_changed_callback
        self.will_end_advance_warning = will_end_advance_warning
        self.will_end_callback = will_end_callback
        self.sent_will_end_callback = False
        self.sync_event_callback = sync_event_callback

        # Setup looping
        self.loop_start = _parse_timestamp(loop_start)
        self.loop_end = _parse_timestamp(loop_end) if loop_end != "end" else None
        self.loops_left = (
            None if loops == 0 else loops - 1
        )  # loops=0 means "forever" in the opus, but we use None for that here
        self.jump_in_progress: _JumpInProgress | None = None

        # Setup files and containers
        self.input_file_path = asset_dir / "/".join(Path(asset).parts[1:])
        self.input_file = open(self.input_file_path, "rb")
        self.input_container = av.open(self.input_file, "r")

        self.temp_dir = tempfile.TemporaryDirectory(
            prefix=f"screencrash-video-{datetime.now(tz=timezone.utc).isoformat()}-"
        )
        if len(self.input_container.streams.video) > 0:
            if len(self.input_container.streams.video) > 1:
                raise RuntimeError(
                    f"Expected at most 1 video stream, found {len(self.input_container.streams.video)}"
                )
            out_video_path = Path(self.temp_dir.name) / "video.webm"
            out_video_file_handle = open(out_video_path, "wb")
            out_video_container = av.open(
                out_video_file_handle,
                "w",
                format="webm",
                options={"live": "1"},
            )
            out_video_container.add_stream_from_template(
                self.input_container.streams.video[0]
            )
            self.video_output = _VideoOutput(
                file_path=out_video_path,
                file_handle=out_video_file_handle,
                container=out_video_container,
            )
        else:
            self.video_output = None
        if len(self.input_container.streams.audio) > 0:
            if len(self.input_container.streams.audio) > 1:
                raise RuntimeError(
                    f"Expected at most 1 audio stream, found {len(self.input_container.streams.audio)}"
                )
            out_audio_path = Path(self.temp_dir.name) / "audio.webm"
            out_audio_file_handle = open(out_audio_path, "wb")
            out_audio_container = av.open(
                out_audio_file_handle,
                "w",
                format="webm",
                options={"live": "1"},
            )
            out_audio_stream = out_audio_container.add_stream("libopus")
            self.audio_output = _AudioOutput(
                file_path=out_audio_path,
                file_handle=out_audio_file_handle,
                container=out_audio_container,
                stream=out_audio_stream,
            )
        else:
            self.audio_output = None

        # Setup misc
        if self.input_container.duration is None:
            raise RuntimeError("container.duration is None")
        self.duration = self.input_container.duration

        # Setup encoding
        self.play_pause_status: _Playing | _Paused = _Paused(pause_time_in_stream=0)
        self.next_video_timestamp: int = 0
        self.next_audio_timestamp: int = 0
        self.waiting_for_video_keyframe = False
        # This is the latest read audio timestamp in the input file.
        # If you seek to an earlier point, it will decrease. In av.time_base.
        self.latest_input_audio_timestamp: int = 0
        # This is the latest written audio timestamp in the output file.
        # It will increase mostly monotonically. In av.time_base
        self.latest_output_audio_timestamp: int = 0
        self.done = False

        self._seek(round(start_at * av.time_base))

        # Start encoding
        self.stream_task = asyncio.create_task(self._encode())
        if SYNC_CLIENTS:
            self.sync_events_task = asyncio.create_task(self._send_sync_events())
        else:
            self.sync_events_task = None

    def _close_containers(self) -> None:
        self.input_container.close()
        if self.audio_output:
            self.audio_output.container.close()
        if self.video_output:
            self.video_output.container.close()

    def _cleanup(self) -> None:
        if self.sync_events_task:
            self.sync_events_task.cancel()
        # In case _close_containers hasn't already been called.
        self._close_containers()
        self.input_file.close()
        if self.video_output:
            self.video_output.file_handle.close()
        if self.audio_output:
            self.audio_output.file_handle.close()
        self.temp_dir.cleanup()

    def _broadcast_change(self) -> None:
        self.effect_changed_callback()

    def _seek(self, position_in_av_time_base: int) -> None:
        self.input_container.seek(position_in_av_time_base)
        self.latest_input_audio_timestamp = position_in_av_time_base  # So we can broadcast changes immediately and get correct data

    def _handle_packet(
        self,
        packet: av.Packet,
    ):
        if (
            packet.stream.type == "video" and self.video_output
        ):  # Drop video packets if we don't have a video output for some reason
            self._handle_video_packet(packet, self.video_output.container)
        elif (
            packet.stream.type == "audio" and self.audio_output
        ):  # Drop audio packets if we don't have an audio output for some reason
            self._handle_audio_packet(packet, self.audio_output.container)

    def _maybe_send_will_end_callback(self) -> None:
        if self.sent_will_end_callback:
            return
        if not self.done:
            if (
                self.duration - self.latest_input_audio_timestamp
            ) / av.time_base + STREAM_DELAY < self.will_end_advance_warning:
                will_end_at = datetime.now(tz=timezone.utc) + timedelta(
                    seconds=(self.duration - self.latest_input_audio_timestamp)
                    / av.time_base
                    + STREAM_DELAY
                )
                self.will_end_callback(will_end_at)
                self.sent_will_end_callback = True
        else:
            will_end_at = datetime.now(tz=timezone.utc) + timedelta(
                seconds=STREAM_DELAY
            )
            self.will_end_callback(will_end_at)

    def _encoded_enough_for_now(self) -> bool:
        if isinstance(self.play_pause_status, _Playing):
            played_time_since_unpause = (
                time.time() - self.play_pause_status.clients_start_time
            )

            encoded_time_since_unpause = (
                self.latest_output_audio_timestamp
                - self.play_pause_status.start_time_in_stream
            ) / av.time_base
            return encoded_time_since_unpause - played_time_since_unpause > STREAM_DELAY
        else:
            encoded_after_pause = (
                self.latest_output_audio_timestamp
                - self.play_pause_status.pause_time_in_stream
            ) / av.time_base
            return encoded_after_pause > STREAM_DELAY

    async def _encode(self) -> None:
        try:
            packet_generator = self.input_container.demux()
            while True:
                if self._encoded_enough_for_now():
                    await asyncio.sleep(0.1)
                else:
                    try:
                        packet = next(packet_generator)
                    except StopIteration:
                        # Reached end of file
                        if self.loop_end is None and ():
                            # If we're looping, and the loop ends at the end of the file, jump back
                            self._seek(self.loop_start)
                            self._decrease_loops_left()
                            self._broadcast_change()
                            packet = next(packet_generator)
                        else:
                            # Else, stop encoding
                            break

                    self._handle_packet(packet)
                    self._maybe_send_will_end_callback()

            print(f"Finished encoding from {self.input_file_path.name}")
            self._close_containers()
            self.done = True
            self._maybe_send_will_end_callback()  # In case we haven't done it already
        except Exception:
            traceback.print_exc()
            raise
        finally:
            await asyncio.sleep(
                STREAM_DELAY + 1
            )  # Wait a bit to let any readers finish, just in case
            print(f"Cleaning up {self.input_file_path.name}")
            self._cleanup()

    async def _send_sync_events(self) -> None:
        await asyncio.sleep(
            TIME_BEFORE_FIRST_SYNC
        )  # Sleep before the first one, to give the playback time to stabilize
        while True:
            if isinstance(self.play_pause_status, _Playing):
                encoded_seconds_since_unpause = (
                    self.latest_output_audio_timestamp
                    - self.play_pause_status.start_time_in_stream
                ) / av.time_base
                playout_time = datetime.fromtimestamp(
                    self.play_pause_status.clients_start_time
                    + encoded_seconds_since_unpause,
                    tz=timezone.utc,
                )
                time_in_file = self.latest_output_audio_timestamp / av.time_base
                print(
                    f"playout: {playout_time}, infile: {time_in_file:5f}, latest: {self.latest_output_audio_timestamp}"
                )
                self.sync_event_callback(playout_time, time_in_file)
            await asyncio.sleep(SYNC_EVENT_INTERVAL)

    def set_loop_count(self, loops: int) -> None:
        self.loops_left = None if loops == 0 else loops - 1
        self._broadcast_change()

    def set_loop_times(self, loop_start: str, loop_end: str) -> None:
        self.loop_start = _parse_timestamp(loop_start)
        self.loop_end = _parse_timestamp(loop_end) if loop_end != "end" else None

    def get_duration(self) -> float:
        return self.duration / av.time_base

    def get_position(self) -> float:
        # This will generally be a bit ahead of the actually played position in the client,
        # but is more meaningful in other ways:
        # - It matches the position you seek to from the UI
        # - It tells you whether you can break out of a vamp loop
        # - It doesn't tell you a position before the loop when you've just jumped
        return self.latest_input_audio_timestamp / av.time_base

    def is_playing(self) -> bool:
        return isinstance(self.play_pause_status, _Playing)

    def is_looping(self) -> bool:
        return self.loops_left is None or self.loops_left > 0

    def stop(self) -> None:
        self.stream_task.cancel()
        if self.sync_events_task:
            self.sync_events_task.cancel()
        self.done = True

    def play(self, clients_play_time: datetime) -> None:
        if isinstance(self.play_pause_status, _Playing):
            return  # Already playing
        self.play_pause_status = _Playing(
            clients_start_time=clients_play_time.timestamp(),
            start_time_in_stream=self.play_pause_status.pause_time_in_stream,
        )

    def pause(self, clients_pause_time: datetime) -> float | None:
        if isinstance(self.play_pause_status, _Paused):
            return  # Already paused
        # Guess current played time in stream
        played_seconds_since_unpause = (
            clients_pause_time.timestamp() - self.play_pause_status.clients_start_time
        )
        pause_time_in_stream = round(
            self.play_pause_status.start_time_in_stream
            + played_seconds_since_unpause * av.time_base
        )
        self.play_pause_status = _Paused(pause_time_in_stream=pause_time_in_stream)
        return pause_time_in_stream / av.time_base

    def seek(self, position: float) -> None:
        self._seek(round(position * av.time_base))

    def get_mimetype(self, stream_type: typing.Literal["audio", "video"]) -> str:
        if stream_type == "video":
            return "video/webm"
        else:
            return "audio/webm"

    def is_done(self) -> bool:
        return self.done

    def get_output_file(
        self, stream_type: typing.Literal["audio", "video"]
    ) -> Path | None:
        if stream_type == "video":
            if not self.video_output:
                return None
            return self.video_output.file_path
        else:
            if not self.audio_output:
                return None
            return self.audio_output.file_path

    def _decrease_loops_left(self):
        if self.loops_left is not None:
            self.loops_left -= 1

    def _handle_video_packet(
        self, packet: av.Packet, output_container: av.container.OutputContainer
    ):
        if packet.pts is None:
            # Dummy packet, just pass it through
            output_container.mux(packet)
        elif self.jump_in_progress is not None and packet_fully_before_timestamp(
            packet, self.jump_in_progress.jumping_to
        ):
            # We just jumped, and haven't reached a packet containing the time we jumped to yet. Drop the packet.
            pass
        else:
            # Modify timestamp and pass through.
            # Or possibly drop, if haven't seen a keyframe after jumping.
            # Either way, update the next timestamp
            assert packet.duration is not None  # Not a dummy packet
            packet.pts = self.next_video_timestamp
            packet.dts = packet.pts
            self.next_video_timestamp += packet.duration
            if self.waiting_for_video_keyframe and packet.is_keyframe:
                self.waiting_for_video_keyframe = False
            if not self.waiting_for_video_keyframe:
                output_container.mux(packet)

    def _handle_audio_packet(
        self,
        packet: av.Packet,
        output_container: av.container.OutputContainer,
    ):
        if packet.pts is None:
            # Dummy packet, just pass it through
            output_container.mux(packet)
        elif self.jump_in_progress is not None and packet_fully_before_timestamp(
            packet, self.jump_in_progress.jumping_to
        ):
            # We just jumped, and haven't reached a packet containing the time we jumped to yet. Drop the packet.
            pass

        elif self.jump_in_progress:
            # We've just jumped, and reached the audio packet containing a time we jumped to.
            # Stitch it together with the packet we stored before jumping.

            jumped_from_frame = typing.cast(
                av.AudioFrame,
                assert_and_get_one(
                    self.jump_in_progress.partial_loop_end_packet.decode()
                ),
            )
            jumped_to_frame = typing.cast(
                av.AudioFrame, assert_and_get_one(packet.decode())
            )

            frame = stitch_audio_frames(
                jumped_from_frame,
                jumped_to_frame,
                self.jump_in_progress.jumping_from,
                self.jump_in_progress.jumping_to,
            )

            self.jump_in_progress = None

            assert self.audio_output is not None
            out_packets = self.audio_output.stream.encode(frame)

            for out_packet in out_packets:
                if (
                    out_packet.duration is not None
                ):  # If it's a dummy packet somehow, just send it
                    assert out_packet.pts is not None
                    self.latest_input_audio_timestamp = convert_to_av_time_base(
                        packet.pts, packet.time_base
                    )
                    out_packet.pts = self.next_audio_timestamp
                    out_packet.dts = out_packet.pts
                    self.latest_output_audio_timestamp = convert_to_av_time_base(
                        out_packet.pts, out_packet.time_base
                    )
                    self.next_audio_timestamp += out_packet.duration

                output_container.mux(out_packet)
            self._broadcast_change()  # For updated position
        elif (
            self.loop_end is not None
            and (self.loops_left is None or self.loops_left > 0)
            and not packet_fully_before_timestamp(packet, self.loop_end)
        ):
            # Audio packet containing the end of the looping portion.
            # Store the current packet so we can stitch it together with the start of the loop,
            # then seek to the start of the loop.
            assert packet.duration is not None  # Not a dummy packet
            self.jump_in_progress = _JumpInProgress(
                jumping_from=self.loop_end,
                jumping_to=self.loop_start,
                partial_loop_end_packet=packet,
            )
            packet_duration = convert_to_av_time_base(packet.duration, packet.time_base)
            seek_to = max(
                self.jump_in_progress.jumping_to - 5 * packet_duration,
                0,
            )

            self.input_container.seek(seek_to, any_frame=True)
            self.waiting_for_video_keyframe = True
            self._decrease_loops_left()
        else:
            # A normal audio packet, just re-encode it

            frame = typing.cast(av.AudioFrame, assert_and_get_one(packet.decode()))

            assert self.audio_output is not None
            out_packets = self.audio_output.stream.encode(frame)

            for out_packet in out_packets:
                if (
                    out_packet.duration is not None
                ):  # If it's a dummy packet somehow, just send it
                    assert out_packet.pts is not None
                    self.latest_input_audio_timestamp = convert_to_av_time_base(
                        packet.pts, packet.time_base
                    )
                    out_packet.pts = self.next_audio_timestamp
                    out_packet.dts = out_packet.pts
                    self.latest_output_audio_timestamp = convert_to_av_time_base(
                        out_packet.pts, out_packet.time_base
                    )
                    self.next_audio_timestamp += out_packet.duration
                output_container.mux(out_packet)
