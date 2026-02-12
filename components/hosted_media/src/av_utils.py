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


def convert_to_av_time_base(time: int, from_time_base: Fraction) -> int:

    # This looks off, but remember: from_time_base is of the form 1/x and av.time_base is of the form x
    converted_time = time * from_time_base * av.time_base

    if converted_time.is_integer():
        return converted_time.numerator
    else:
        raise RuntimeError(
            f"Cannot convert from time base {from_time_base} to av.time_base"
        )


def packet_fully_before_timestamp(
    packet: av.Packet, timestamp_in_av_time_base: int
) -> bool:
    assert packet.pts is not None
    assert packet.duration is not None
    packet_end = packet.pts + packet.duration
    # This looks off, but remember: packet.time_base is of the form 1/x and av.time_base is of the form x
    packet_end_in_av_time_base = packet_end * packet.time_base * av.time_base

    return packet_end_in_av_time_base <= timestamp_in_av_time_base


def stitch_audio_frames(
    first_frame_interleaved: av.AudioFrame,
    second_frame_interleaved: av.AudioFrame,
    first_frame_end: int,  # In av.time_base
    second_frame_start: int,  # In av.time_base
) -> av.AudioFrame:
    planar_resampler = av.audio.resampler.AudioResampler("s32p", "stereo")
    resampled_frames = planar_resampler.resample(second_frame_interleaved)
    assert len(resampled_frames) == 1
    second_frame = resampled_frames[0]
    assert second_frame.pts is not None
    assert second_frame.time_base is not None
    second_frame_array = second_frame.to_ndarray()

    resampled_frames = planar_resampler.resample(first_frame_interleaved)
    assert len(resampled_frames) == 1
    first_frame = resampled_frames[0]
    assert first_frame.pts is not None
    assert first_frame.time_base is not None
    first_frame_array = first_frame.to_ndarray()

    sample_duration = av.time_base / first_frame.sample_rate
    first_array_cutoff_index = math.floor(
        (
            first_frame_end
            - convert_to_av_time_base(
                first_frame.pts,
                first_frame.time_base,
            )
        )
        / sample_duration
    )

    second_array_cutoff_index = math.ceil(
        (
            second_frame_start
            - convert_to_av_time_base(
                second_frame.pts,
                second_frame.time_base,
            )
        )
        / sample_duration
    )
    stitched_array = numpy.concatenate(
        [
            first_frame_array[:, :first_array_cutoff_index],
            second_frame_array[:, second_array_cutoff_index:],
        ],
        axis=1,
        dtype=first_frame_array.dtype,
    )

    # _plot_stitched_packet(
    #     loop_start_frame,
    #     loop_end_frame,
    #     loop_start_array,
    #     loop_end_array,
    #     stitched_array,
    #     start_array_cutoff_index,
    #     end_array_cutoff_index,
    # )

    stitched_frame = av.AudioFrame.from_ndarray(
        stitched_array,  # pyright: ignore -- We know it's a supported dtype since we got it from another frame
        format=first_frame.format.name,
    )
    stitched_frame.pts = (
        first_frame.pts
    )  # Will be overwritten as the function is used at time of writing, but just to be safe
    stitched_frame.sample_rate = first_frame.sample_rate
    stitched_frame.time_base = first_frame.time_base

    interleaved_resampler = av.audio.resampler.AudioResampler("s32", "stereo")
    resampled_frames = interleaved_resampler.resample(stitched_frame)
    assert len(resampled_frames) == 1
    frame = resampled_frames[0]
    return frame


def _plot_stitched_packet(
    loop_start_frame: av.AudioFrame,
    loop_end_frame: av.AudioFrame,
    loop_start_array: numpy.ndarray,
    loop_end_array: numpy.ndarray,
    stitched_array: numpy.ndarray,
    start_array_cutoff_index: int,
    end_array_cutoff_index: int,
):
    assert loop_start_frame.pts is not None
    assert loop_start_frame.time_base is not None
    assert loop_end_frame.pts is not None
    assert loop_end_frame.time_base is not None
    loop_start_timestamps = numpy.linspace(
        convert_to_av_time_base(
            loop_start_frame.pts,
            loop_start_frame.time_base,
        ),
        convert_to_av_time_base(
            loop_start_frame.pts,
            loop_start_frame.time_base,
        )
        + convert_to_av_time_base(
            loop_start_frame.duration,
            loop_start_frame.time_base,
        ),
        loop_start_array.shape[1],
    )

    loop_end_timestamps = numpy.linspace(
        convert_to_av_time_base(
            loop_end_frame.pts,
            loop_end_frame.time_base,
        ),
        convert_to_av_time_base(
            loop_end_frame.pts,
            loop_end_frame.time_base,
        )
        + convert_to_av_time_base(
            loop_end_frame.duration,
            loop_end_frame.time_base,
        ),
        loop_end_array.shape[1],
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
    pyplot.show()
