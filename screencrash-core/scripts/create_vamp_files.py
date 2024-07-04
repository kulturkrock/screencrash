import argparse
import pyaudacity as pa
import json
import pathlib
import os
import re
import subprocess
from typing import Union
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("-w", "--workdir", default="vamp_work")
parser.add_argument("-p", "--prefix")
parser.add_argument("-a", "--from-audacity", action="store_true")
parser.add_argument("-v", "--video-file")
parser.add_argument("-o", "--output-dir")

def main(prefix: str, work_dir: pathlib.Path, from_audacity: bool, input_video_file: Union[pathlib.Path, None], out_dir: pathlib.Path):
    os.makedirs(work_dir, exist_ok=True)
    if from_audacity: # Else assume we have already done it, maybe manually
        res = pa.do('GetInfo: Type="Tracks" Format="JSON"')
        tracks = json.loads(res.replace("BatchCommand finished: OK",""))
        num_tracks = len(tracks)
        for i in range(num_tracks):
            pa.do(f'SelectTracks: Track={i}')
            pa.curs_track_end()
            pa.sel_prev_clip()
            pa.export(work_dir / f"{prefix}_part{i+1}_beforestretch.wav", num_channels=2, allow_overwrite=True)

    before_stretch_files = filter(lambda path: re.match(f"{prefix}_part[0-9]+_beforestretch.wav", path.name), work_dir.iterdir())
    sorted_files = sorted(before_stretch_files)
    if input_video_file is None:
        print("No video file provided, just splitting audio")
        for before_stretch_file in sorted_files:
            output_audio_file = out_dir / before_stretch_file.name.replace("_beforestretch.wav", ".wav")
            shutil.copy(before_stretch_file, output_audio_file)
        return
    
    fps = 25
    prev_files_duration = 0
    for i, before_stretch_file in enumerate(sorted_files):
        # Stretch audio files
        output = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", before_stretch_file
        ])
        initial_duration = float(output)
        target_duration = round(initial_duration*fps)/fps
        output_audio_file = out_dir / before_stretch_file.name.replace("_beforestretch.wav", ".wav")
        subprocess.check_call([
            "rubberband", "--ignore-clipping", "-D", str(target_duration), before_stretch_file, output_audio_file
        ])
        # Cut video file
        if i != len(sorted_files)-1:
            subprocess.check_call([
                "ffmpeg", "-y", "-i", input_video_file, "-ss", str(prev_files_duration),
                "-t", str(target_duration), output_audio_file.with_suffix(".webm")
            ])
        else:
            # Last file, let's go to the end
            subprocess.check_call([
                "ffmpeg", "-y", "-i", input_video_file, "-ss", str(prev_files_duration),
                output_audio_file.with_suffix(".webm")
            ])

        prev_files_duration += target_duration
        print(f"{output_audio_file.name}: {initial_duration} -> {target_duration}")
    


if __name__ == "__main__":
    args = parser.parse_args()
    prefix = args.prefix
    work_dir = pathlib.Path(args.workdir)
    from_audacity = args.from_audacity
    video_file = pathlib.Path(args.video_file) if args.video_file is not None else None
    out_dir = pathlib.Path(args.output_dir) if args.output_dir is not None else work_dir
    main(prefix, work_dir, from_audacity, video_file, out_dir)

# Behavior:
# Take in a video of some type
# - Extract fps
# Take in an audacity project
# - Extract clip boundaries
# - Extract clips
# Adjust clip boundaries to be on whole frames
# Stretch audio to new boundaries
# Export split audio based on new boundaries
# Export split video based on new boundaries