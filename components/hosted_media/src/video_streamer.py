from pathlib import Path
import tempfile
from collections.abc import Callable
from fractions import Fraction
import matplotlib.pyplot as plt
import numpy as np
import asyncio
import av
import av.container
import av.subtitles.stream
import av.packet


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
        self.latest_audio_time = 0  # in av.time_base
        self.latest_audio_duration = 0

    def start(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
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
        return self.latest_audio_time / av.time_base

    def _init_from_input_container(
        self,
        input_container: av.container.InputContainer,
        output_container: av.container.OutputContainer,
    ) -> dict[int, int]:
        if input_container.duration is None:
            raise RuntimeError("container.duration is None")
        self.duration = input_container.duration / av.time_base
        self.effect_changed_callback()  # To let people know the actual duration
        stream_offset: dict[int, int] = {}
        for stream in input_container.streams:
            if (
                isinstance(stream, av.VideoStream)
                or isinstance(stream, av.AudioStream)
                # We're not using subtitles, but since it's supported we may as well add it
                or isinstance(stream, av.subtitles.stream.SubtitleStream)
            ):
                out_stream = output_container.add_stream_from_template(stream)
                stream_offset[out_stream.index] = 0
        return stream_offset

    def _seek_exact(
        self, time: int, input_container: av.container.InputContainer
    ) -> int:
        input_container.seek(time)
        offset = 0  # self.latest_audio_time + self.latest_audio_duration - time
        return offset

    async def _stream(self) -> None:
        if self.output_video_file_path is None:
            raise RuntimeError("VideoStreamer never started")
        with av.open(
            self.output_video_file_path, "w", format="webm"
        ) as output_container:
            with av.open(self.input_video_file_path, "r") as input_container:
                self._init_from_input_container(input_container, output_container)
                offset = 0
                all_audio_times = []
                all_video_times = []
                clip_start = 10_000_000
                clip_end = 15_000_000
                for _ in range(5):
                    offset = self._seek_exact(clip_start, input_container)

                    for packet in input_container.demux():
                        if packet.pts is not None:
                            if packet.duration is None:
                                raise RuntimeError("packet.duration is None")
                            if packet.dts is None:
                                raise RuntimeError("packet.dts is None")
                            packet.pts += _convert_time_base(
                                offset, av.time_base, packet.time_base
                            )
                            packet.dts += _convert_time_base(
                                offset, av.time_base, packet.time_base
                            )

                            if packet.stream.type == "audio":
                                self.latest_audio_time = _convert_time_base(
                                    packet.pts, packet.time_base, av.time_base
                                )
                                self.latest_audio_duration = _convert_time_base(
                                    packet.duration, packet.time_base, av.time_base
                                )
                                all_audio_times.append(self.latest_audio_time)
                                if self.latest_audio_time > clip_end:
                                    output_container.mux(av.packet.Packet(input=None))
                                    break
                            if packet.stream.type == "video":
                                latest_video_time = _convert_time_base(
                                    packet.pts, packet.time_base, av.time_base
                                )
                                all_video_times.append(latest_video_time)

                        output_container.mux(packet)

                diffs = np.diff(all_audio_times)
                plt.plot(range(len(diffs)), diffs)
                plt.show()

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
