from dataclasses import dataclass
from pathlib import Path
import tempfile
from collections.abc import Callable
from datetime import datetime
import typing
import asyncio
import time

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


@dataclass
class _Looping:
    loop_start: int  # in av.time_base
    loop_end: int  # in av.time_base
    loops_left: int | None


@dataclass
class _JumpInProgress:
    jumping_to: int  # in av.time_base
    jumping_from: int  # in av.time_base
    partial_loop_end_packet: av.Packet


@dataclass
class _PlayingState:
    output_video_file_path: Path
    output_audio_file_path: Path
    out_audio_stream: av.AudioStream
    input_container: av.container.InputContainer
    duration: float
    jump_in_progress: _JumpInProgress | None
    next_video_timestamp: int  # In the time_base of the video stream
    next_audio_timestamp: int  # In the time_base of the audio stream
    waiting_for_video_keyframe: bool


class MediaStreamer:

    def __init__(
        self,
        asset: Path,
        asset_dir: Path,
        effect_changed_callback: Callable[[], None],
    ):
        self.input_video_file_path = asset_dir / "/".join(Path(asset).parts[1:])
        self.effect_changed_callback = effect_changed_callback
        self.looping: _Looping | None = None  # _Looping(1_212_720, 3_612_920, 5)  # tmp
        self.playing_state: _PlayingState | None = None
        self.stream_task: asyncio.Task | None = None
        self.done = False

    def start(self) -> None:
        self.stream_task = asyncio.create_task(self._stream())

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
        if self.stream_task is None:
            raise RuntimeError("VideoStreamer never started")
        self.stream_task.cancel()
        self.done = True

    def get_mimetype(self, stream_type: typing.Literal["audio", "video"]) -> str:
        if stream_type == "video":
            return "video/webm"
        else:
            return "audio/flac"

    def is_done(self) -> bool:
        return self.done

    def get_output_file(self, stream_type: typing.Literal["audio", "video"]) -> Path:
        if self.playing_state is None:
            raise RuntimeError("VideoStreamer never started")
        if stream_type == "video":
            return self.playing_state.output_video_file_path
        else:
            return self.playing_state.output_audio_file_path

    def _broadcast_change(self) -> None:
        self.effect_changed_callback()

    async def _stream(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(
            prefix=f"screencrash-video-{datetime.now().isoformat()}-"
        )
        try:
            output_video_file_path = Path(temp_dir.name) / "out.webm"
            output_video_file_path.touch()
            output_audio_file_path = Path(temp_dir.name) / "out.flac"
            output_audio_file_path.touch()
            with (
                open(self.input_video_file_path, "rb") as input_video_file,
                open(output_video_file_path, "wb") as output_video_file,
                open(output_audio_file_path, "wb") as output_audio_file,
            ):
                with (
                    av.open(input_video_file, "r") as input_container,
                    av.open(
                        output_video_file,
                        "w",
                        format="webm",
                        options={"live": "1"},
                    ) as output_video_container,
                    av.open(
                        output_audio_file,
                        "w",
                        format="flac",
                        options={"live": "1"},
                    ) as output_audio_container,
                ):
                    out_audio_stream, duration = self._init_containers_and_state(
                        input_container, output_video_container, output_audio_container
                    )
                    self.playing_state = _PlayingState(
                        output_video_file_path=output_video_file_path,
                        output_audio_file_path=output_audio_file_path,
                        out_audio_stream=out_audio_stream,
                        input_container=input_container,
                        duration=duration / av.time_base,
                        jump_in_progress=None,
                        next_video_timestamp=0,
                        next_audio_timestamp=0,
                        waiting_for_video_keyframe=False,
                    )
                    self._broadcast_change()  # For the updated duration

                    started_playing = time.time()

                    # The loop will go on until we reach the end of the file.
                    # Jumping back using input_container.seek() is safe during the loop.
                    for packet in input_container.demux():

                        if packet.stream.type == "video":
                            self._handle_video_packet(packet, output_video_container)
                        elif packet.stream.type == "audio":
                            self._handle_audio_packet(packet, output_audio_container)
                            if packet.time_base is not None:
                                # Let's use the audio stream timestamps to see how far we've encoded
                                encoded_time = float(
                                    self.playing_state.next_audio_timestamp
                                    * packet.time_base
                                )
                                played_time = time.time() - started_playing
                                size_kb = (
                                    self.playing_state.output_video_file_path.stat().st_size
                                    / 1000
                                )
                                print(
                                    f"Enc: {encoded_time} Pla: {played_time:.2f} Siz: {size_kb:.2f}"
                                )
                                if encoded_time - played_time > 5:
                                    await asyncio.sleep(encoded_time - played_time - 5)

                    # Reached the end of the file
                    self.done = True
        finally:
            await asyncio.sleep(
                1
            )  # Wait a second to let any readers finish, just in case
            temp_dir.cleanup()

    def _init_containers_and_state(
        self,
        input_container: av.container.InputContainer,
        output_video_container: av.container.OutputContainer,
        output_audio_container: av.container.OutputContainer,
    ) -> tuple[av.AudioStream, int]:
        if len(input_container.streams.video) != 1:
            raise RuntimeError(
                f"Expected 1 video stream, found {len(input_container.streams.video)}"
            )
        in_video_stream = input_container.streams.video[0]

        if input_container.duration is None:
            raise RuntimeError("container.duration is None")
        duration = input_container.duration

        output_video_container.add_stream_from_template(in_video_stream)

        out_audio_stream = output_audio_container.add_stream("flac")

        assert isinstance(out_audio_stream, av.AudioStream)
        return out_audio_stream, duration

    def _handle_video_packet(
        self, packet: av.Packet, output_container: av.container.OutputContainer
    ):
        assert self.playing_state is not None
        if packet.pts is None:
            # Dummy packet, just pass it through
            output_container.mux(packet)
        elif (
            self.playing_state.jump_in_progress is not None
            and packet_fully_before_timestamp(
                packet, self.playing_state.jump_in_progress.jumping_to
            )
        ):
            # We just jumped, and haven't reached a packet containing the time we jumped to yet. Drop the packet.
            pass
        else:
            # Modify timestamp and pass through.
            # Or possibly drop, if haven't seen a keyframe after jumping.
            # Either way, update the next timestamp
            assert packet.duration is not None  # Not a dummy packet
            packet.pts = self.playing_state.next_video_timestamp
            packet.dts = packet.pts
            self.playing_state.next_video_timestamp += packet.duration
            if self.playing_state.waiting_for_video_keyframe and packet.is_keyframe:
                self.playing_state.waiting_for_video_keyframe = False
            if not self.playing_state.waiting_for_video_keyframe:
                output_container.mux(packet)

    def _handle_audio_packet(
        self,
        packet: av.Packet,
        output_container: av.container.OutputContainer,
    ):
        assert self.playing_state is not None
        if packet.pts is None:
            # Dummy packet, just pass it through
            output_container.mux(packet)
        elif (
            self.playing_state.jump_in_progress is not None
            and packet_fully_before_timestamp(
                packet, self.playing_state.jump_in_progress.jumping_to
            )
        ):
            # We just jumped, and haven't reached a packet containing the time we jumped to yet. Drop the packet.
            pass

        elif self.playing_state.jump_in_progress:
            # We've just jumped, and reached the audio packet containing a time we jumped to.
            # Stitch it together with the packet we stored before jumping.

            jumped_from_frame = typing.cast(
                av.AudioFrame,
                assert_and_get_one(
                    self.playing_state.jump_in_progress.partial_loop_end_packet.decode()
                ),
            )
            jumped_to_frame = typing.cast(
                av.AudioFrame, assert_and_get_one(packet.decode())
            )

            frame = stitch_audio_frames(
                jumped_from_frame,
                jumped_to_frame,
                self.playing_state.jump_in_progress.jumping_from,
                self.playing_state.jump_in_progress.jumping_to,
            )

            self.playing_state.jump_in_progress = None

            out_packets = self.playing_state.out_audio_stream.encode(frame)

            for out_packet in out_packets:
                if (
                    out_packet.duration is not None
                ):  # If it's a dummy packet somehow, just send it
                    out_packet.pts = self.playing_state.next_audio_timestamp
                    out_packet.dts = out_packet.pts
                    self.playing_state.next_audio_timestamp += out_packet.duration
                output_container.mux(out_packet)
        elif self.looping and not packet_fully_before_timestamp(
            packet, self.looping.loop_end
        ):
            # Audio packet containing the end of the looping portion.
            # Store the current packet so we can stitch it together with the start of the loop,
            # then seek to the start of the loop.
            assert packet.duration is not None  # Not a dummy packet
            self.playing_state.jump_in_progress = _JumpInProgress(
                jumping_from=self.looping.loop_end,
                jumping_to=self.looping.loop_start,
                partial_loop_end_packet=packet,
            )
            packet_duration = convert_to_av_time_base(packet.duration, packet.time_base)
            seek_to = max(
                self.playing_state.jump_in_progress.jumping_to - 5 * packet_duration,
                0,
            )

            self.playing_state.input_container.seek(seek_to, any_frame=True)
            self.playing_state.waiting_for_video_keyframe = True

            # tmp maybe, not sure we need to be able to loop N times
            if self.looping.loops_left is not None:
                self.looping.loops_left -= 1
                if self.looping.loops_left <= 0:
                    self.looping = None
                    # this one is definitely tmp
                    if self.playing_state.jump_in_progress.jumping_to == 1_212_720:
                        self.looping = _Looping(27_054_200, 32_793_060, 5)
        else:
            # A normal audio packet, just re-encode it

            frame = typing.cast(av.AudioFrame, assert_and_get_one(packet.decode()))

            out_packets = self.playing_state.out_audio_stream.encode(frame)

            for out_packet in out_packets:
                if (
                    out_packet.duration is not None
                ):  # If it's a dummy packet somehow, just send it
                    out_packet.pts = self.playing_state.next_audio_timestamp
                    out_packet.dts = out_packet.pts
                    self.playing_state.next_audio_timestamp += out_packet.duration
                output_container.mux(out_packet)
