from pathlib import Path
import tempfile
from collections.abc import Callable
from fractions import Fraction
from datetime import datetime

import asyncio
import av
import av.container
from typing import cast


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
    ) -> tuple[av.VideoStream, av.AudioStream, int]:

        if len(input_container.streams.video) != 1:
            raise RuntimeError(
                f"Expected 1 video stream, found {len(input_container.streams.video)}"
            )
        in_video_stream = input_container.streams.video[0]

        if len(input_container.streams.audio) != 1:
            raise RuntimeError(
                f"Expected 1 audio stream, found {len(input_container.streams.audio)}"
            )
        in_audio_stream = input_container.streams.audio[0]

        if input_container.duration is None:
            raise RuntimeError("container.duration is None")
        duration = input_container.duration

        return in_video_stream, in_audio_stream, duration

    def _set_duration_and_broadcast_change(self, duration_in_av_time_base: int):
        self.duration = duration_in_av_time_base / av.time_base
        self.effect_changed_callback()  # To let people know the actual duration

    def _init_output_container(
        self,
        output_container: av.container.OutputContainer,
    ) -> tuple[av.VideoStream, av.AudioStream]:

        out_video_stream = output_container.add_stream("vp9")
        assert isinstance(out_video_stream, av.VideoStream)
        out_audio_stream = output_container.add_stream("opus")
        assert isinstance(out_audio_stream, av.AudioStream)
        return out_video_stream, out_audio_stream

    async def _stream(self) -> None:
        if self.output_video_file_path is None:
            raise RuntimeError("VideoStreamer never started")
        with (
            av.open(self.input_video_file_path, "r") as input_container,
            av.open(
                self.output_video_file_path, "w", format="webm"
            ) as output_container,
        ):
            _, _, duration = self._extract_from_input_container(input_container)
            out_video_stream, out_audio_stream = self._init_output_container(
                output_container
            )

            self._set_duration_and_broadcast_change(duration)

            for in_packet in input_container.demux():
                for frame in in_packet.decode():
                    frame = cast(
                        av.VideoFrame | av.AudioFrame, frame
                    )  # type hints from pyav claim it's a SubtitleSet, but that's not true
                    if isinstance(frame, av.VideoFrame):
                        out_packets = out_video_stream.encode(frame)
                        output_container.mux(out_packets)
                    elif isinstance(frame, av.AudioFrame):
                        out_packets = out_audio_stream.encode(frame)
                        output_container.mux(out_packets)
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


def _convert_time_base(
    time: int, from_time_base: int | Fraction, to_time_base: int | Fraction
) -> int:
    # If a time_base is an int, assume it's av.time_base and convert it to the same form
    # as other time_bases
    if isinstance(from_time_base, int):
        from_time_base = Fraction(1, from_time_base)
    if isinstance(to_time_base, int):
        to_time_base = Fraction(1, to_time_base)

    converted_time = time * from_time_base / to_time_base

    if converted_time.is_integer():
        return converted_time.numerator
    else:
        raise RuntimeError(
            f"Cannot convert from time base {from_time_base} to {to_time_base}"
        )

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
