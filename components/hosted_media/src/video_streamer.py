from pathlib import Path
import tempfile
from collections.abc import Callable
from fractions import Fraction
from datetime import datetime
import typing
import asyncio
import av
import av.container
import numpy
import math
from matplotlib import pyplot
import av.audio.resampler
from dataclasses import dataclass
from av_utils import (
    convert_to_av_time_base,
    packet_fully_before_timestamp,
    stitch_audio_frames,
)

# This makes some assumptions about the video file:
# 1. The packets are ordered with nondecreasing timestamps, even across streams
# 2. There is a keyframe after the start of each looping portion, soon enough that
#    video frames can be dropped until then
# 3. The codecs are allowed in webm
# 4. Audio packets generally have the same duration
# 5. Audio packets have only one audio frame
# 6. The audio codec does not use keyframes
# 7. The audio codec is lossless
# You can create a file that matches this by:
# ffmpeg -i filename.mp4 -c:v vp9 -c:a flac filename_nokeyframe.mp4
# Open in audacity, find very exact timestamps to loop
# ffmpeg -i filename_nokeyframe.mp4 -c:v vp9 -c:a copy -force_key_frames 00:00:01.212920,00:00:27.054200 filename_keyframe.mp4
# (Replace the timestamps of -force_key_frames with your loop starts)


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
        self.temp_dir = None
        self.output_video_file_path = None
        self.done = False
        self.duration: float | None = None

    def start(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix=f"screencrash-video-{datetime.now().isoformat()}-"
        )
        self.output_video_file_path = Path(self.temp_dir.name) / (
            "out" + self.input_video_file_path.suffix
        )
        self.output_video_file_path.touch()
        asyncio.create_task(self._stream())

    def get_duration(self) -> float:
        if self.duration is None:
            return 0
        return self.duration

    def get_position(self) -> float:
        return 0

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

    def _set_duration_and_broadcast_change(self, duration_in_av_time_base: int):
        self.duration = duration_in_av_time_base / av.time_base
        self.effect_changed_callback()  # To let people know the actual duration

    def _init_output_container(
        self,
        output_container: av.container.OutputContainer,
        in_video_stream: av.VideoStream,
    ) -> av.AudioStream:

        output_container.add_stream_from_template(in_video_stream)
        out_audio_stream = output_container.add_stream("flac")
        assert isinstance(out_audio_stream, av.AudioStream)
        return out_audio_stream

    async def _stream(self) -> None:
        if self.output_video_file_path is None:
            raise RuntimeError("VideoStreamer never started")
        with (
            av.open(self.input_video_file_path, "r") as input_container,
            av.open(self.output_video_file_path, "w", format="mp4") as output_container,
        ):
            in_video_stream, duration = self._extract_from_input_container(
                input_container
            )
            out_audio_stream = self._init_output_container(
                output_container, in_video_stream
            )

            self._set_duration_and_broadcast_change(duration)

            # tmp
            looping: _Looping | None = _Looping(1_212_720, 3_612_920, 5)

            next_video_timestamp = None
            next_audio_timestamp = None
            jump_in_progress: _JumpInProgress | None = None
            waiting_for_video_keyframe = False
            # The loop will go on until we reach the end of the file.
            # Jumping back using input_container.seek() is safe during the loop.
            for packet in input_container.demux():

                # Dummy packet, just pass it through
                if packet.pts is None:
                    output_container.mux(packet)
                    continue

                # After looping, we may be too early and should drop packets
                if jump_in_progress is not None:
                    if packet_fully_before_timestamp(
                        packet, jump_in_progress.jumping_to
                    ):
                        continue

                assert (
                    packet.duration is not None
                )  # If it's not a dummy, duration shouldn't be None

                # Video packet, modify timestamp and pass through
                # Or drop, if we're waiting for a keyframe after seeking
                if packet.stream.type == "video":
                    if next_video_timestamp is not None:
                        packet.pts = next_video_timestamp
                        packet.dts = next_video_timestamp
                    next_video_timestamp = packet.pts + packet.duration
                    if waiting_for_video_keyframe:
                        if not packet.is_keyframe:
                            continue  # Drop the frame, but still calculate next_video_pts
                        else:
                            waiting_for_video_keyframe = False
                    output_container.mux(packet)
                    continue

                # Audio packet, re-encode so we can stitch them together when seeking/looping
                if packet.stream.type == "audio":
                    # Loop if we're supposed to
                    if looping and not packet_fully_before_timestamp(
                        packet,
                        looping.loop_end,
                    ):
                        jump_in_progress = _JumpInProgress(
                            jumping_from=looping.loop_end,
                            jumping_to=looping.loop_start,
                            partial_loop_end_packet=packet,
                        )
                        packet_duration = convert_to_av_time_base(
                            packet.duration, packet.time_base
                        )
                        seek_to = (
                            jump_in_progress.jumping_to - 5 * packet_duration
                        )  # To have some margin
                        if seek_to < 0:
                            seek_to = 0
                        input_container.seek(seek_to, any_frame=True)
                        waiting_for_video_keyframe = True

                        if looping.loops_left is not None:
                            looping.loops_left -= 1
                            if looping.loops_left <= 0:
                                looping = None
                                # tmp
                                if jump_in_progress.jumping_to == 1_212_720:
                                    looping = _Looping(27_054_200, 32_793_060, 5)
                        continue  # Don't actually decode the packet yet, wait until the start of the loop

                    # If this is the first audio packet after looping, stitch it together with the one we saved
                    if jump_in_progress:
                        loop_start_frames = packet.decode()
                        assert len(loop_start_frames) == 1
                        loop_start_frame = typing.cast(
                            av.AudioFrame, loop_start_frames[0]
                        )
                        loop_end_frames = (
                            jump_in_progress.partial_loop_end_packet.decode()
                        )
                        assert len(loop_end_frames) == 1
                        loop_end_frame = typing.cast(av.AudioFrame, loop_end_frames[0])

                        frame = stitch_audio_frames(
                            loop_end_frame,
                            loop_start_frame,
                            jump_in_progress.jumping_from,
                            jump_in_progress.jumping_to,
                        )

                        jump_in_progress = None
                    else:
                        frames = packet.decode()
                        assert len(frames) == 1
                        frame = typing.cast(av.AudioFrame, frames[0])

                    out_packets = out_audio_stream.encode(frame)

                    for out_packet in out_packets:
                        if next_audio_timestamp is not None:
                            out_packet.pts = next_audio_timestamp
                            out_packet.dts = next_audio_timestamp
                        next_audio_timestamp = out_packet.pts + out_packet.duration
                        output_container.mux(out_packet)
            self.done = True

    def stop(self) -> None:
        if self.temp_dir is None:
            raise RuntimeError("VideoStreamer never started")
        self.temp_dir.cleanup()
        self.done = True

    def get_mimetype(self) -> str:
        return "video/webm"

    def is_done(self) -> bool:
        return self.done

    def get_output_file(self) -> Path:
        if self.output_video_file_path is None:
            raise RuntimeError("VideoStreamer never started")
        return self.output_video_file_path

    # TODO: Vamp script makes separate audio and video, so the files from Zelda are like that
    #       - Why did we need that?
    #         * Because video and audio sample rates didn't add up?
    #         * Because audio needs to be wav?

    # We can send data as we go
    # Using it for pause:
    # - We would need to have a very small buffer on the client, is that safe?
    # - Need to duplicate the frame, can't just stop sending or the browser will try to compensate
    # Using it for vamp:
    # - Same, really, or we will get another loop if we switch too late
    # - This is inherent to the problem, let's just try it with some throttling
    # - need to go into the video to make sure we end on a frame? No, end of the file is already a frame boundary
    # - Still need to be aware of frames to make sure we don't go too far ahead
    #   * Either that, or send something from the frontend. But then the frontend controls the position, need to handle several
    #   * Need to handle reconnections? Keyframes...
    # - Is there some starting data we need to skip on files after the first?

    # Let's think it through. What do I need?
    # - Stream a video, next part may be replaced on short notice (<1s)
    # - Pause (may be done in frontend)
    # - Seek (within a file)
    # Solutions:
    # - webrtc?
    #   * python lib only supports h264/vp8, check transparency
    # - libav?
    #   * trying, it's complex
    # - ffmpeg?
    #   * stream via rtmp, udp or tcp to aiohttp server, or just put it in a file
    #   * aiohttp passes it on, should push chunks instead of getting?
    #   * Or we read a file, then poll when we're at the end <--- TRYING THIS NOW

    # concat with re, infinite loop (but should be able to end?)
    # -re is too slow to start
    # Need more granular control I think, try pyav again?

    # With pyav:
    # - Need to play synced video+audio
    # - audio needs to line up exactly
    # - video needs to be a keyframe, at least. But it may be more complicated, so easiest to make multiple files?
    #   * Or make sure it's encoded with friendly settings: No B-frames, no referring to frames before the last keyframe
    # - We can probably afford to reencode the audio on the fly, but probably not the video
    #
    # Sketch (one video file):
    # - Assume friendly file
    # - Get two very exact timestamps to loop between
    #   * Can be changed with an action
    # - When reaching the (packet containing the) loop-end in the audio stream:
    #   * Decode the packet
    #   * Cut it so it only contains audio up to the loop-end
    #   * Re-encode and send
    #   * seek to the (packet containing the) loop-start
    #   * Cut it so it only contains audio after the loop-start
    #   * Re-encode and send
    #   * Continue re-encoding until the next keyframe?
    # - In the video stream:
    #   * Same thing, but the frames won't line up with the audio
    #   * We shorten the duration of the current frame, both before and after
    #   * Try re-encoding the video too, until the next keyframe. Test it on a weak laptop.
