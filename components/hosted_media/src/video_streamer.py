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
import av.audio.frame

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
        in_video_stream: av.VideoStream,
        in_audio_stream: av.AudioStream,
    ) -> tuple[av.VideoStream, av.AudioStream]:

        out_video_stream = output_container.add_stream_from_template(in_video_stream)
        assert isinstance(out_video_stream, av.VideoStream)
        out_audio_stream = output_container.add_stream(
            "flac",
            # bit_rate=128_000,
        )
        assert isinstance(out_audio_stream, av.AudioStream)
        return out_video_stream, out_audio_stream

        # We are now on a keyframe before the position we wanted to seek to
        # Sketch:
        # - Assume forced keyframe after timestamp
        # - When we reach the packet *containing* the end time:
        #   - Decode, truncate, shorten duration, encode, send
        #   - Seek to time before start time
        #   - Drop all packets until the one containing the start time
        #   - Decode, truncate, shorten duration, encode, send
        #   - Drop all video packets until we get a keyframe

    async def _stream(self) -> None:
        if self.output_video_file_path is None:
            raise RuntimeError("VideoStreamer never started")
        with (
            av.open(self.input_video_file_path, "r") as input_container,
            av.open(self.output_video_file_path, "w", format="mp4") as output_container,
        ):
            in_video_stream, in_audio_stream, duration = (
                self._extract_from_input_container(input_container)
            )
            _, out_audio_stream = self._init_output_container(
                output_container, in_video_stream, in_audio_stream
            )

            self._set_duration_and_broadcast_change(duration)

            tmp_seeked_1 = 0
            tmp_seeked_2 = 0

            packet_iterator = input_container.demux()
            next_video_timestamp = None
            next_audio_timestamp = None
            drop_video_until_keyframe = False
            jumping_to = None
            jumping_from = None
            partial_loop_end_packet = None
            while True:
                try:
                    packet = next(packet_iterator)
                except StopIteration:  # End of file
                    break

                # After looping, we may be too early and should drop packets
                if jumping_to is not None:
                    if not _timestamp_in_packet(jumping_to, packet):
                        continue

                # Dummy packet, just pass it through
                if packet.pts is None:
                    output_container.mux(packet)
                    continue
                if packet.duration is None:
                    # If it's not a dummy, duration shouldn't be None
                    raise RuntimeError("Packet duration is None")

                # Video packet, modify timestamp and pass through
                # Or drop, if we're waiting for a keyframe after seeking
                if packet.stream.type == "video":
                    if next_video_timestamp is not None:
                        packet.pts = next_video_timestamp
                        packet.dts = next_video_timestamp
                    next_video_timestamp = packet.pts + packet.duration
                    if packet.is_keyframe:
                        drop_video_until_keyframe = False
                    if drop_video_until_keyframe:
                        continue  # Drop the frame, but still calculate next_video_pts
                    output_container.mux(packet)
                    continue

                # Audio packet, re-encode so we can stitch them together when seeking/looping
                if packet.stream.type == "audio":
                    # Loop if we're supposed to
                    # tmp implementation
                    loop_1_start = 1_212_720
                    loop_1_end = 3_612_920

                    loop_2_start = 27_054_200
                    loop_2_end = 32_793_060
                    if tmp_seeked_1 < 5 and _timestamp_in_packet(loop_1_end, packet):
                        jumping_to = loop_1_start
                        jumping_from = loop_1_end
                        partial_loop_end_packet = packet
                        packet_duration = _convert_time_base(
                            packet.duration, packet.time_base, av.time_base
                        )
                        seek_to = (
                            jumping_to - 5 * packet_duration
                        )  # To have some margin
                        if seek_to < -7000:
                            seek_to = -7000
                        input_container.seek(seek_to, any_frame=True)
                        drop_video_until_keyframe = True
                        tmp_seeked_1 += 1
                        continue
                    elif tmp_seeked_2 < 5 and _timestamp_in_packet(loop_2_end, packet):
                        jumping_to = loop_2_start
                        jumping_from = loop_2_end
                        partial_loop_end_packet = packet
                        packet_duration = _convert_time_base(
                            packet.duration, packet.time_base, av.time_base
                        )
                        input_container.seek(
                            jumping_to - 5 * packet_duration
                        )  # To have some margin
                        drop_video_until_keyframe = True
                        tmp_seeked_2 += 1
                        continue

                    # If this is the first audio packet after looping, stitch it together with the one we saved
                    if partial_loop_end_packet is not None:
                        assert jumping_from is not None
                        assert jumping_to is not None
                        loop_start_frames = packet.decode()
                        assert len(loop_start_frames) == 1
                        loop_start_frame_interleaved = typing.cast(
                            av.AudioFrame, loop_start_frames[0]
                        )
                        resampler = av.audio.resampler.AudioResampler("s32p", "stereo")
                        resampled_frames = resampler.resample(
                            loop_start_frame_interleaved
                        )
                        assert len(resampled_frames) == 1
                        loop_start_frame = resampled_frames[0]
                        assert loop_start_frame.pts is not None
                        assert loop_start_frame.time_base is not None
                        loop_start_array = loop_start_frame.to_ndarray()

                        loop_end_frames = partial_loop_end_packet.decode()
                        assert len(loop_end_frames) == 1
                        loop_end_frame_interleaved = typing.cast(
                            av.AudioFrame, loop_end_frames[0]
                        )
                        resampled_frames = resampler.resample(
                            loop_end_frame_interleaved
                        )
                        assert len(resampled_frames) == 1
                        loop_end_frame = resampled_frames[0]
                        assert loop_end_frame.pts is not None
                        assert loop_end_frame.time_base is not None
                        loop_end_array = loop_end_frame.to_ndarray()

                        loop_start_timestamps = numpy.linspace(
                            _convert_time_base(
                                loop_start_frame.pts,
                                loop_start_frame.time_base,
                                av.time_base,
                            ),
                            _convert_time_base(
                                loop_start_frame.pts,
                                loop_start_frame.time_base,
                                av.time_base,
                            )
                            + _convert_time_base(
                                loop_start_frame.duration,
                                loop_start_frame.time_base,
                                av.time_base,
                            ),
                            loop_start_array.shape[1],
                        )

                        loop_end_timestamps = numpy.linspace(
                            _convert_time_base(
                                loop_end_frame.pts,
                                loop_end_frame.time_base,
                                av.time_base,
                            ),
                            _convert_time_base(
                                loop_end_frame.pts,
                                loop_end_frame.time_base,
                                av.time_base,
                            )
                            + _convert_time_base(
                                loop_end_frame.duration,
                                loop_end_frame.time_base,
                                av.time_base,
                            ),
                            loop_end_array.shape[1],
                        )

                        sample_duration = av.time_base / loop_end_frame.sample_rate
                        end_array_cutoff_index = math.floor(
                            (
                                jumping_from
                                - _convert_time_base(
                                    loop_end_frame.pts,
                                    loop_end_frame.time_base,
                                    av.time_base,
                                )
                            )
                            / sample_duration
                        )

                        start_array_cutoff_index = math.ceil(
                            (
                                jumping_to
                                - _convert_time_base(
                                    loop_start_frame.pts,
                                    loop_start_frame.time_base,
                                    av.time_base,
                                )
                            )
                            / sample_duration
                        )
                        stitched_array = numpy.concatenate(
                            [
                                loop_end_array[:, :end_array_cutoff_index],
                                loop_start_array[:, start_array_cutoff_index:],
                            ],
                            axis=1,
                            dtype=loop_end_array.dtype,
                        )
                        track = 0
                        limit = 0.6
                        pyplot.subplot(3, 1, 1)
                        # pyplot.ylim(-limit, limit)
                        pyplot.plot(
                            range(stitched_array.shape[1])[:end_array_cutoff_index],
                            stitched_array[track][:end_array_cutoff_index],
                            "b.-",
                        )
                        pyplot.plot(
                            range(stitched_array.shape[1])[end_array_cutoff_index:],
                            stitched_array[track][end_array_cutoff_index:],
                            "r.-",
                        )
                        pyplot.axhline(y=0, linewidth=1, color="k")
                        pyplot.subplot(3, 1, 2)
                        # pyplot.ylim(-limit, limit)
                        pyplot.plot(
                            loop_end_timestamps[:end_array_cutoff_index],
                            loop_end_array[track][:end_array_cutoff_index],
                            "b.-",
                        )
                        pyplot.plot(
                            loop_end_timestamps[end_array_cutoff_index:],
                            loop_end_array[track][end_array_cutoff_index:],
                            "r.-",
                        )
                        pyplot.axhline(y=0, linewidth=1, color="k")
                        pyplot.subplot(3, 1, 3)
                        # pyplot.ylim(-limit, limit)
                        pyplot.plot(
                            loop_start_timestamps[start_array_cutoff_index:],
                            loop_start_array[track][start_array_cutoff_index:],
                            "b.-",
                        )
                        pyplot.plot(
                            loop_start_timestamps[:start_array_cutoff_index],
                            loop_start_array[track][:start_array_cutoff_index],
                            "r.-",
                        )
                        pyplot.axhline(y=0, linewidth=1, color="k")
                        # pyplot.show()

                        stitched_frame = av.AudioFrame.from_ndarray(
                            stitched_array,  # pyright: ignore -- We know it's a supported dtype since we got it from another frame
                            format=loop_end_frame.format.name,
                        )
                        stitched_frame.pts = (
                            loop_start_frame.pts
                        )  # Will be overwritten, but maybe needed for encode()?
                        stitched_frame.sample_rate = loop_end_frame.sample_rate
                        stitched_frame.time_base = loop_end_frame.time_base

                        resampler2 = av.audio.resampler.AudioResampler("s32", "stereo")
                        resampled_frames = resampler2.resample(stitched_frame)
                        assert len(resampled_frames) == 1
                        stitched_frame_interleaved = resampled_frames[0]

                        out_packets = out_audio_stream.encode(
                            stitched_frame_interleaved
                        )
                        jumping_to = None
                        partial_loop_end_packet = None
                        jumping_from = None
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


def _timestamp_in_packet(timestamp_in_av_time_base: int, packet: av.Packet) -> bool:
    if packet.pts is None:
        return False  # Dummy packet
    if packet.duration is None:
        raise RuntimeError("Packet has no duration")
    timestamp_in_packet_time_base = _convert_time_base_inexact(
        timestamp_in_av_time_base, av.time_base, packet.time_base
    )
    return (
        timestamp_in_packet_time_base >= packet.pts
        and timestamp_in_packet_time_base < packet.pts + packet.duration
    )


def _convert_time_base_inexact(
    time: int, from_time_base: int | Fraction, to_time_base: int | Fraction
) -> float:
    # If a time_base is an int, assume it's av.time_base and convert it to the same form
    # as other time_bases
    if isinstance(from_time_base, int):
        from_time_base = Fraction(1, from_time_base)
    if isinstance(to_time_base, int):
        to_time_base = Fraction(1, to_time_base)

    converted_time = time * from_time_base / to_time_base

    return converted_time.numerator / converted_time.denominator

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
