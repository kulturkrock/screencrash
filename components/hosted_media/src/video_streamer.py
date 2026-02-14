from dataclasses import dataclass
from pathlib import Path
import tempfile
from collections.abc import Callable
from datetime import datetime
import typing
import asyncio

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
# 3. The video codec is allowed in mp4
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


@dataclass
class _PlayingState:
    temp_dir: tempfile.TemporaryDirectory
    output_video_file_path: Path
    duration: float


@dataclass
class _JumpInProgress:
    jumping_to: int  # in av.time_base
    jumping_from: int  # in av.time_base
    partial_loop_end_packet: av.Packet


@dataclass
class _Looping:
    loop_start: int  # in av.time_base
    loop_end: int  # in av.time_base
    loops_left: int | None


class VideoStreamer:

    def __init__(
        self,
        asset: Path,
        asset_dir: Path,
        effect_changed_callback: Callable[[], None],
    ):
        self.input_video_file_path = asset_dir / "/".join(Path(asset).parts[1:])
        self.effect_changed_callback = effect_changed_callback
        self.playing_state: _PlayingState | None = None
        self.done = False

    def start(self) -> None:
        asyncio.create_task(self._stream())

    def get_duration(self) -> float:
        if self.playing_state is None:
            # This may be called before we've managed to get the duration from the input file, so we
            # should return something. It will look a bit weird in the UI at the start, but has no
            # other consequences.
            return 0
        return self.playing_state.duration

    def get_position(self) -> float:
        return 0

    def stop(self) -> None:
        if self.playing_state is None:
            raise RuntimeError("VideoStreamer never started")
        self.playing_state.temp_dir.cleanup()
        self.done = True

    def get_mimetype(self) -> str:
        return "video/webm"

    def is_done(self) -> bool:
        return self.done

    def get_output_file(self) -> Path:
        if self.playing_state is None:
            raise RuntimeError("VideoStreamer never started")
        return self.playing_state.output_video_file_path

    def _broadcast_change(self) -> None:
        self.effect_changed_callback()

    async def _stream(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(
            prefix=f"screencrash-video-{datetime.now().isoformat()}-"
        )
        output_video_file_path = Path(temp_dir.name) / (
            "out" + self.input_video_file_path.suffix
        )
        output_video_file_path.touch()
        with (
            av.open(self.input_video_file_path, "r") as input_container,
            av.open(output_video_file_path, "w", format="mp4") as output_container,
        ):
            in_video_stream, duration = self._extract_from_input_container(
                input_container
            )
            self.playing_state = _PlayingState(
                temp_dir, output_video_file_path, duration / av.time_base
            )
            self._broadcast_change()  # For the updated duration

            out_audio_stream = self._init_output_container(
                output_container, in_video_stream
            )

            # tmp
            looping: _Looping | None = _Looping(1_212_720, 3_612_920, 5)

            next_video_timestamp = 0
            next_audio_timestamp = 0
            jump_in_progress: _JumpInProgress | None = None
            waiting_for_video_keyframe = False
            # The loop will go on until we reach the end of the file.
            # Jumping back using input_container.seek() is safe during the loop.
            for packet in input_container.demux():

                if packet.pts is None:
                    # Dummy packet, just pass it through
                    output_container.mux(packet)
                elif jump_in_progress is not None and packet_fully_before_timestamp(
                    packet, jump_in_progress.jumping_to
                ):
                    # We just jumped, and haven't reached a packet containing the time we jumped to yet. Drop the packet.
                    pass
                elif packet.stream.type == "video":
                    # Video packet, modify timestamp and pass through.
                    # Or possibly drop, if haven't seen a keyframe after jumping.
                    # Either way, update the next timestamp
                    assert packet.duration is not None  # Not a dummy packet
                    packet.pts = next_video_timestamp
                    packet.dts = next_video_timestamp
                    next_video_timestamp += packet.duration
                    if waiting_for_video_keyframe and packet.is_keyframe:
                        waiting_for_video_keyframe = False
                    if not waiting_for_video_keyframe:
                        output_container.mux(packet)
                elif (
                    packet.stream.type == "audio"
                    and looping
                    and not packet_fully_before_timestamp(packet, looping.loop_end)
                ):
                    # Audio packet containing the end of the looping portion.
                    # Store the current packet so we can stitch it together with the start of the loop,
                    # then seek to the start of the loop.
                    assert packet.duration is not None  # Not a dummy packet
                    jump_in_progress = _JumpInProgress(
                        jumping_from=looping.loop_end,
                        jumping_to=looping.loop_start,
                        partial_loop_end_packet=packet,
                    )
                    packet_duration = convert_to_av_time_base(
                        packet.duration, packet.time_base
                    )
                    seek_to = max(
                        jump_in_progress.jumping_to - 5 * packet_duration,
                        0,
                    )

                    input_container.seek(seek_to, any_frame=True)
                    waiting_for_video_keyframe = True

                    # tmp maybe, not sure we need to be able to loop N times
                    if looping.loops_left is not None:
                        looping.loops_left -= 1
                        if looping.loops_left <= 0:
                            looping = None
                            # this one is definitely tmp
                            if jump_in_progress.jumping_to == 1_212_720:
                                looping = _Looping(27_054_200, 32_793_060, 5)

                elif packet.stream.type == "audio" and jump_in_progress:
                    # We've just jumped, and reached the audio packet containing a time we jumped to.
                    # Stitch it together with the packet we stored before jumping.

                    jumped_from_frame = typing.cast(
                        av.AudioFrame,
                        assert_and_get_one(
                            jump_in_progress.partial_loop_end_packet.decode()
                        ),
                    )
                    jumped_to_frame = typing.cast(
                        av.AudioFrame, assert_and_get_one(packet.decode())
                    )

                    frame = stitch_audio_frames(
                        jumped_from_frame,
                        jumped_to_frame,
                        jump_in_progress.jumping_from,
                        jump_in_progress.jumping_to,
                    )

                    jump_in_progress = None

                    out_packets = out_audio_stream.encode(frame)

                    for out_packet in out_packets:
                        if (
                            out_packet.duration is not None
                        ):  # If it's a dummy packet somehow, just send it
                            out_packet.pts = next_audio_timestamp
                            out_packet.dts = next_audio_timestamp
                            next_audio_timestamp = out_packet.pts + out_packet.duration
                        output_container.mux(out_packet)

                elif packet.stream.type == "audio":
                    # A normal audio packet, just re-encode it

                    frame = typing.cast(
                        av.AudioFrame, assert_and_get_one(packet.decode())
                    )

                    out_packets = out_audio_stream.encode(frame)

                    for out_packet in out_packets:
                        if (
                            out_packet.duration is not None
                        ):  # If it's a dummy packet somehow, just send it
                            out_packet.pts = next_audio_timestamp
                            out_packet.dts = next_audio_timestamp
                            next_audio_timestamp = out_packet.pts + out_packet.duration
                        output_container.mux(out_packet)
            # Reached the end of the file
            self.done = True

    def _extract_from_input_container(
        self, input_container: av.container.InputContainer
    ) -> tuple[av.VideoStream, int]:

        if len(input_container.streams.video) != 1:
            raise RuntimeError(
                f"Expected 1 video stream, found {len(input_container.streams.video)}"
            )
        in_video_stream = input_container.streams.video[0]

        if input_container.duration is None:
            raise RuntimeError("container.duration is None")
        duration = input_container.duration

        return in_video_stream, duration

    def _init_output_container(
        self,
        output_container: av.container.OutputContainer,
        in_video_stream: av.VideoStream,
    ) -> av.AudioStream:

        output_container.add_stream_from_template(in_video_stream)
        out_audio_stream = output_container.add_stream("flac")
        assert isinstance(out_audio_stream, av.AudioStream)
        return out_audio_stream
