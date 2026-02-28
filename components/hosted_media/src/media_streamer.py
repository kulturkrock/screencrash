from dataclasses import dataclass
from pathlib import Path
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta
import typing
import asyncio
import time
import os

import av
import av.container

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

STREAM_DELAY = float(os.environ.get("SCREENCRASH_HOSTED_MEDIA_STREAM_DELAY", "2"))


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
        will_end_advance_warning: float,
        will_end_callback: Callable[
            [datetime], None
        ],  # Function that takes the expected end of the clients' played streams
    ):
        # Setup callbacks
        self.effect_changed_callback = effect_changed_callback
        self.will_end_advance_warning = will_end_advance_warning
        self.will_end_callback = will_end_callback
        self.sent_will_end_callback = False

        # Setup looping
        self.loop_start = _parse_timestamp(loop_start)
        self.loop_end = _parse_timestamp(loop_end) if loop_end != "end" else None
        self.loops_left = (
            None if loops == 0 else loops - 1
        )  # loops=0 means "forever" in the opus, but we use None for that here
        self.jump_in_progress: _JumpInProgress | None = None

        # Setup files
        self.input_video_file_path = asset_dir / "/".join(Path(asset).parts[1:])
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix=f"screencrash-video-{datetime.now().isoformat()}-"
        )
        self.output_video_file_path = Path(self.temp_dir.name) / "out.webm"
        self.output_audio_file_path = Path(self.temp_dir.name) / "out.flac"
        self.input_video_file = open(self.input_video_file_path, "rb")
        self.output_video_file = open(self.output_video_file_path, "wb")
        self.output_audio_file = open(self.output_audio_file_path, "wb")

        # Setup containers
        self.input_container = av.open(self.input_video_file, "r")
        self.output_video_container = av.open(
            self.output_video_file,
            "w",
            format="webm",
            options={"live": "1"},
        )
        self.output_audio_container = av.open(
            self.output_audio_file,
            "w",
            format="webm",
            options={"live": "1"},
        )
        if len(self.input_container.streams.video) != 1:
            raise RuntimeError(
                f"Expected 1 video stream, found {len(self.input_container.streams.video)}"
            )
        in_video_stream = self.input_container.streams.video[0]
        self.output_video_container.add_stream_from_template(in_video_stream)
        self.out_audio_stream = self.output_audio_container.add_stream("libopus")

        # Setup misc
        if self.input_container.duration is None:
            raise RuntimeError("container.duration is None")
        self.duration = self.input_container.duration / av.time_base

        # Setup encoding
        self.play_pause_status: _Playing | _Paused = _Paused(pause_time_in_stream=0)
        self.next_video_timestamp: int = 0
        self.next_audio_timestamp: int = 0
        self.last_audio_out_packet: av.Packet | None = None
        self.waiting_for_video_keyframe = False
        self.input_container.seek(round(start_at * av.time_base))
        self.decoded_audio_time = start_at
        self.done = False

        # Start encoding
        self.stream_task = asyncio.create_task(self.encode())

    def _cleanup(self) -> None:
        self.input_container.close()
        self.output_audio_container.close()
        self.output_video_container.close()
        self.input_video_file.close()
        self.output_video_file.close()
        self.output_audio_file.close()
        self.temp_dir.cleanup()

    def _broadcast_change(self) -> None:
        self.effect_changed_callback()

    async def encode(self) -> None:
        try:
            looped = False
            while True:
                if not looped:
                    pass
                else:
                    self.input_container.seek(0)
                    self.decoded_audio_time = 0
                self._broadcast_change()
                # The for-loop will go on until we reach the end of the file.
                # Jumping back using input_container.seek() is safe during the for-loop.
                for packet in self.input_container.demux():
                    await self._handle_packet(
                        packet, self.output_video_container, self.output_audio_container
                    )
                    if (
                        self.duration - self.decoded_audio_time + STREAM_DELAY
                        < self.will_end_advance_warning
                        and not self.sent_will_end_callback
                    ):
                        will_end_at = datetime.now() + timedelta(
                            seconds=self.duration
                            - self.decoded_audio_time
                            + STREAM_DELAY
                        )
                        self.will_end_callback(will_end_at)
                        self.sent_will_end_callback = True
                if self.loop_end is not None or self.loops_left == 0:
                    break
                else:
                    self._handle_completed_loop()

            # Reached the end of the file and no loops left
            print(f"Finished encoding from {self.input_video_file_path.name}")
            self.done = True
            if not self.sent_will_end_callback:
                will_end_at = datetime.now() + timedelta(seconds=STREAM_DELAY)
                time_to_sleep = (
                    will_end_at.timestamp()
                    - self.will_end_advance_warning
                    - time.time()
                )
                await asyncio.sleep(max(time_to_sleep, 0))
                self.will_end_callback(will_end_at)
                self.sent_will_end_callback = True
                await asyncio.sleep(max(will_end_at.timestamp() - time.time(), 0))
        finally:
            await asyncio.sleep(
                1
            )  # Wait a second to let any readers finish, just in case
            self._cleanup()

    def set_loop_count(self, loops: int) -> None:
        self.loops_left = None if loops == 0 else loops - 1
        self._broadcast_change()

    def set_loop_times(self, loop_start: str, loop_end: str) -> None:
        self.loop_start = _parse_timestamp(loop_start)
        self.loop_end = _parse_timestamp(loop_end) if loop_end != "end" else None

    def get_duration(self) -> float:
        return self.duration

    def get_position(self) -> float:
        # This will generally be a bit ahead of the actually played position in the client,
        # but is more meaningful in other ways:
        # - It matches the position you seek to from the UI
        # - It tells you whether you can break out of a vamp loop
        # - It doesn't tell you a position before the loop when you've just jumped
        return self.decoded_audio_time

    def is_playing(self) -> bool:
        return isinstance(self.play_pause_status, _Playing)

    def is_looping(self) -> bool:
        return self.loops_left is None or self.loops_left > 0

    def stop(self) -> None:
        self.stream_task.cancel()
        self.done = True

    def play(self, clients_play_time: datetime) -> None:
        if isinstance(self.play_pause_status, _Playing):
            return  # Already playing
        self.play_pause_status = _Playing(
            clients_start_time=clients_play_time.timestamp(),
            start_time_in_stream=self.play_pause_status.pause_time_in_stream,
        )

    def pause(self) -> None:
        if isinstance(self.play_pause_status, _Paused):
            return  # Already paused
        last_packet = self.last_audio_out_packet
        if last_packet is None:
            last_time = 0
        else:
            assert last_packet.pts is not None
            assert last_packet.time_base is not None
            last_time = convert_to_av_time_base(last_packet.pts, last_packet.time_base)
        self.play_pause_status = _Paused(pause_time_in_stream=last_time)

    def seek(self, position: float) -> None:
        self.input_container.seek(round(position * av.time_base))
        self.decoded_audio_time = position

    def get_mimetype(self, stream_type: typing.Literal["audio", "video"]) -> str:
        if stream_type == "video":
            return "video/webm"
        else:
            return "audio/webm"

    def is_done(self) -> bool:
        return self.done

    def get_output_file(self, stream_type: typing.Literal["audio", "video"]) -> Path:
        if stream_type == "video":
            return self.output_video_file_path
        else:
            return self.output_audio_file_path

    def _handle_completed_loop(self):
        if self.loops_left is not None:
            self.loops_left -= 1

    async def _handle_packet(
        self,
        packet: av.Packet,
        output_video_container: av.container.OutputContainer,
        output_audio_container: av.container.OutputContainer,
    ):
        if packet.stream.type == "video":
            self._handle_video_packet(packet, output_video_container)
        elif packet.stream.type == "audio":
            if packet.pts is not None:
                assert packet.time_base is not None
                self.decoded_audio_time = float(packet.pts * packet.time_base)
            self._handle_audio_packet(packet, output_audio_container)
            if (
                self.last_audio_out_packet
                and self.last_audio_out_packet.time_base is not None
                and self.last_audio_out_packet.pts is not None
            ):
                if isinstance(self.play_pause_status, _Playing):
                    # Let's use the audio stream timestamps to see how far we've encoded, and make sure
                    # we don't get too far ahead. We're trusting that the clients really did start playing
                    # at the time they were told.
                    played_time_since_unpause = (
                        time.time() - self.play_pause_status.clients_start_time
                    )

                    encoded_time_since_unpause = (
                        convert_to_av_time_base(
                            self.last_audio_out_packet.pts,
                            self.last_audio_out_packet.time_base,
                        )
                        - self.play_pause_status.start_time_in_stream
                    ) / av.time_base
                    if (
                        encoded_time_since_unpause - played_time_since_unpause
                        > STREAM_DELAY
                    ):
                        await asyncio.sleep(
                            encoded_time_since_unpause
                            - played_time_since_unpause
                            - STREAM_DELAY
                        )
                else:
                    encoded_after_pause = (
                        convert_to_av_time_base(
                            self.last_audio_out_packet.pts,
                            self.last_audio_out_packet.time_base,
                        )
                        - self.play_pause_status.pause_time_in_stream
                    ) / av.time_base
                    if encoded_after_pause > STREAM_DELAY:
                        # Wait for unpausing before doing anything else
                        while isinstance(self.play_pause_status, _Paused):
                            await asyncio.sleep(0.1)

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

            out_packets = self.out_audio_stream.encode(frame)

            for out_packet in out_packets:
                if (
                    out_packet.duration is not None
                ):  # If it's a dummy packet somehow, just send it
                    out_packet.pts = self.next_audio_timestamp
                    out_packet.dts = out_packet.pts
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
            self._handle_completed_loop()
        else:
            # A normal audio packet, just re-encode it

            frame = typing.cast(av.AudioFrame, assert_and_get_one(packet.decode()))

            out_packets = self.out_audio_stream.encode(frame)

            for out_packet in out_packets:
                if (
                    out_packet.duration is not None
                ):  # If it's a dummy packet somehow, just send it
                    out_packet.pts = self.next_audio_timestamp
                    out_packet.dts = out_packet.pts
                    self.next_audio_timestamp += out_packet.duration
                    self.last_audio_out_packet = (
                        out_packet  # Only save real packets here
                    )
                output_container.mux(out_packet)
