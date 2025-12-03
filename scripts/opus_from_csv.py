import argparse
import logging
from pathlib import Path
import yaml
from typing import Any
import subprocess

from read_csv import read_csv, Id, CsvRow, TARGET_SUFFIXES
from read_csv import STATISTICS, warning, error

YamlDict = dict[str, Any]

START_LEVEL = {
    "image": 1_000,
    "video": 1_000,
}

FILE_TYPES = ["image", "audio", "video"]


def get_layer(row: CsvRow, prev: CsvRow) -> int:
    if row.cue == "[BYT]":
        layer = 1000 + 10 * prev.id.row - 5
    else:
        layer = 1000 + 10 * row.id.row
    return layer


def get_file(target: str, filename: Path | None) -> Path | None:
    if filename:
        for suffix in TARGET_SUFFIXES[target]:
            if filename.with_suffix(suffix).is_file():
                return filename.with_suffix(suffix)
    return None


def get_entity_id(row: CsvRow) -> str:
    if row.filename and row.filename.name.startswith(str(row.id)):
        return f"{row.filename.name} - {row.target}"
    else:
        return f"{row.id} - {row.target}"



def convert_opus(csv_rows: list[CsvRow], script: Path, output_dir: Path) -> YamlDict:
    nodes: dict[Id, YamlDict] = {}

    # Creating entities
    for n, row in enumerate(csv_rows):
        assert row.id not in nodes
        nodes[row.id] = {
            "prompt": row.cue,
            "actions": [],
        }
        if row.target not in FILE_TYPES:
            continue

        filename = get_file(row.target, row.filename)
        if not filename:
            warning(row.id, f"Missing {row.target} file: {row.filename}")
            continue

        params: YamlDict = {"entityId": get_entity_id(row)}
        if row.target in ["image", "video"]:
            params["visible"] = True
            params["layer"] = get_layer(row, csv_rows[n-1])
            if row.loop is not None:
                params["looping"] = row.loop
                params["seamless"] = True

        if row.target == "video":
            if filename.suffix == ".webm":
                cmd = ["ffprobe", "-loglevel", "error", "-show_entries", "stream=codec_name",
                       "-of", "default=noprint_wrappers=1:nokey=1", str(filename)]
                codecs = subprocess.run(cmd, capture_output=True, encoding="utf-8").stdout
                codecs = ", ".join(codecs.split())
                warning(row.id, f"Codecs = {codecs}")
                params["mimeCodec"] = f'video/webm; codecs="{codecs}"'
        elif row.target == "image":
            if row.fadein:
                params["fadeIn"] = {"from": 0, "to": 1, "time": row.fadein}
        elif row.target == "audio":
            pass

        nodes[row.id]["actions"].append({
            "target": row.target,
            "cmd": "create",
            "assets": [{"path": str(filename.relative_to(output_dir))}],
            "params": params,
        })

        if row.filename2:
            filename2 = get_file(row.target, row.filename2)
            if not filename2:
                warning(row.id, f"Missing {row.target}: {row.filename2}")
            else:
                nodes[row.id]["actions"].append({
                    "target": row.target,
                    "cmd": "set_next_file",
                    "assets": [{"path": str(filename2.relative_to(output_dir))}],
                    "params": {"entityId": get_entity_id(row)},
                })

    # Destroying entities
    for row in csv_rows:
        if not row.kill:
            continue
        if row.kill not in nodes:
            error(row.id, f"Missing kill row: {row.kill}")
            continue
        if row.target not in FILE_TYPES:
            error(row.id, f"Cannot kill target {row.target!r} (kill row {row.kill})")
            continue
        if row.target == "image" and row.fadeout:
            nodes[row.kill]["actions"].append({
                "target": row.target,
                "cmd": "fade",
                "params": {
                    "entityId": get_entity_id(row),
                    "target": 0,
                    "time": row.fadeout,
                    "stopOnDone": True,
                },
            })
        else:
            nodes[row.kill]["actions"].append({
                "target": row.target,
                "cmd": "destroy",
                "params": {
                    "entityId": get_entity_id(row),
                },
            })

    # Hotkeys
    shortcuts: list[YamlDict] = []
    # for row in csv_rows:
    #     if row.hotkey:
    #         shortcuts.append({
    #             "title": f"create: {row.filename} ({'+'.join(row.hotkey).upper()})",
    #             "actions": [actions[0]],
    #             "hotkey": {
    #                 "key": row.hotkey[-1],
    #                 "modifiers": row.hotkey[:-1],
    #             },
    #         })

    node_ids = sorted(nodes)
    start_id = node_ids[0]
    for id, next_id in zip(node_ids, node_ids[1:] + [start_id]):
        nodes[id]["next"] = str(next_id)

    return {
        "startNode": str(start_id),
        "nodes": {str(k): v for k, v in nodes.items()},
        "action_templates": {},
        "assets": {"script": {"path": str(script.relative_to(output_dir))}},
        "ui": {"shortcuts": shortcuts},
    }


def main(args: argparse.Namespace):
    rows = read_csv(args.input, args.assets_dir)
    opus = convert_opus(rows, args.script, args.output.parent)
    with open(args.output, "w") as f:
        yaml.safe_dump(opus, f, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to convert an exported Google sheet to YAML opus format",
    )
    parser.add_argument(
        "--input", "-i", required=True, type=Path,
        help="CSV file exported from Google Sheets (File -> Download -> Comma Separated Values)",
    )
    parser.add_argument(
        "--output", "-o", required=True, type=Path,
        help="Path to output YAML file",
    )
    parser.add_argument(
        "--script", "-s", required=True, type=Path,
        help="The script (manus) PDF file, should be in the same directory as the output YAML file",
    )
    parser.add_argument(
        "--assets-dir", "-d", required=True, type=Path,
        help="Directory name for assets, should be in the same directory as the output YAML file",
    )
    parser.add_argument(
        '--quiet', '-q', action="store_const", dest="loglevel",
        const=logging.ERROR, default=logging.INFO,
        help="Silent mode, only show errors",
    )
    args = parser.parse_args()
    logging.basicConfig(format="{message}", style="{", level=args.loglevel)
    main(args)
    print(f"Finished    | {STATISTICS['errors']} errors, {STATISTICS['warnings']} warnings")
