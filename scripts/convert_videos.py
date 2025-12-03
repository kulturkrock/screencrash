import argparse
import logging
import time
from pathlib import Path
import shutil
import subprocess

from read_csv import read_csv, Id, TARGET_SUFFIXES
from read_csv import STATISTICS, error

TARGET = "video"
OUT_SUFFIX = ".webm"

def convert_video(id: Id, filename: Path, outdir: Path, fadein: float, fadeout: float, silent: bool, progress: str, force: bool = False):
    outfile = (outdir / filename.name).with_suffix(OUT_SUFFIX)
    infile = None
    for suffix in TARGET_SUFFIXES[TARGET]:
        if suffix != OUT_SUFFIX:
            infile = filename.with_suffix(suffix)
            if infile.is_file():
                break
    else:
        error(id, f"Video doesn't exist: {filename}")
        return

    length: dict[str, float] = {}
    for type in ["video", "audio"]:
        cmd = ["ffprobe", "-loglevel", "error", "-select_streams", type[0]+":0", "-show_entries", "stream=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(infile)]
        length[type] = float(subprocess.run(cmd, capture_output=True).stdout or 0)

    if not silent and not length["audio"]:
        error(id, f"Empty audio track, but video is not marked as silent")
        return

    if outfile.is_file() and not force:
        if infile.stat().st_mtime < outfile.stat().st_mtime:
            logging.info(f"Video {progress} already converted, skipping: {infile}")
            return

    logging.warning(f"Converting video {progress}: {infile} --> {outfile} ({length['video']} s)")
    video_filter: list[str] = []
    if fadein:
        start = 0
        logging.info(f"Fade-in: {start} --[{fadein}]--> {start + fadein}")
        video_filter.append(f"fade=in:st={start}:d={fadein}:alpha=1")
    if fadeout:
        start = length["video"] - fadeout
        logging.info(f"Fade-out: {start} --[{fadeout}]--> {start + fadeout}")
        video_filter.append(f"fade=out:st={start}:d={fadeout}:alpha=1")
    video_filter.append("format=yuva420p")

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y"]
    cmd += ["-i", str(infile), "-filter:v", ",".join(video_filter)]
    cmd += ["-map", "0:v", "-c:v", "libvpx-vp9"]
    if not silent:
        cmd += ["-map", "0:a", "-c:a", "libopus"]
    cmd += ["-auto-alt-ref", "0", "-shortest", str(outfile)]
    try:
        print("#", " ".join(repr(c) if ' ' in c else c for c in cmd))
        subprocess.run(cmd)
    except:
        outfile.unlink(missing_ok=True)
        raise


def copy_asset(filename: Path, target: str, outdir: Path, progress: str, force: bool = False):
    infile = None
    for suffix in TARGET_SUFFIXES[target]:
        infile = filename.with_suffix(suffix)
        if infile.is_file():
            break
    else:
        error(filename, f"Asset {target!r} doesn't exist: {filename}")
        return
    outfile = outdir / infile.name
    if outfile.is_file() and not force:
        if infile.stat().st_mtime < outfile.stat().st_mtime:
            logging.info(f"Asset {progress} already copied, skipping: {infile}")
            return
    logging.info(f"Copying asset {progress}: {infile} --> {outfile}")
    shutil.copy(infile, outfile)


def main(args: argparse.Namespace):
    rows = read_csv(args.input, args.raw_dir)
    stime = time.time()
    logging.info("")
    for n, row in enumerate(rows, 1):
        if row.filename:
            progress = f"{n}/{len(rows)}"
            if row.target == TARGET:
                convert_video(row.id, row.filename, args.assets_dir, row.fadein, row.fadeout, row.silent, progress, args.force)
                if row.filename2:
                    convert_video(row.id, row.filename2, args.assets_dir, 0, 0, row.silent, progress+"[b]", args.force)
            else:
                copy_asset(row.filename, row.target, args.assets_dir, progress, args.force)
                if row.filename2:
                    copy_asset(row.filename2, row.target, args.assets_dir, progress+"[b]", args.force)
            logging.info("")
    logging.info(f"TIME: {(time.time()-stime)/60:.1f} min")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to convert videos to .webm according to a CSV",
    )
    parser.add_argument(
        "--input", "-i", required=True, type=Path,
        help="CSV file exported from Google Sheets (File -> Download -> Comma Separated Values)",
    )
    parser.add_argument(
        "--raw-dir", "-r", required=True, type=Path,
        help="Directory with original (raw) assets",
    )
    parser.add_argument(
        "--assets-dir", "-d", required=True, type=Path,
        help="Directory for resulting assets, should be in the same directory as the output YAML file",
    )
    parser.add_argument(
        '--quiet', '-q', action="store_const", dest="loglevel",
        const=logging.ERROR, default=logging.WARNING,
        help="Silent mode, only show errors",
    )
    parser.add_argument(
        '--verbose', '-v', action="store_const", dest="loglevel",
        const=logging.INFO, default=logging.WARNING,
        help="Verbose mode",
    )
    parser.add_argument(
        '--force', action="store_true",
        help="Force convert all videos",
    )
    args = parser.parse_args()
    logging.basicConfig(format="{message}", style="{", level=args.loglevel)
    main(args)
    print(f"Finished    | {STATISTICS['errors']} errors, {STATISTICS['warnings']} warnings")
