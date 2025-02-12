import argparse
import logging
from pathlib import Path
import csv
from dataclasses import dataclass
import yaml
from typing import Any
import string

YamlDict = dict[str, Any]

ROWNR = "Radnummer"
CUE = "Stickreplik"
TARGET = "Filtyp"
FILENAME = "Filnamn"
FADE = "Fade-in"

TARGET_ALIASES = {
    "clear": ["x", "-", "–", "—", "rensa"],
    "image": ["bild", "img"],
    "video": ["film"],
    "audio": ["ljud"],
}

TARGET_SUFFIXES: dict[str, list[str]] = {
    "clear": [],
    "image": [".jpg", ".png"],
    "video": [".mp4"],
    "audio": [".mp3", ".wav"],
}

STATISTICS = {
    "warnings": 0,
    "errors": 0,
}

MAX_LEVEL = 10_000

@dataclass
class CsvRow:
    rownr: int
    cue: str
    target: str
    filename: Path
    fade: int

    def __init__(self, row: dict[str, str]):
        self.rownr = int(row[ROWNR].strip())
        self.cue = row[CUE].strip()
        self.target = row[TARGET].strip().lower()
        self.filename = Path(row[FILENAME].strip())
        self.fade = int(row[FADE].strip() or 0)

        for target, aliases in TARGET_ALIASES.items():
            if self.target in aliases:
                self.target = target

        if self.target not in TARGET_ALIASES:
            if self.target:
                error(self.rownr, f"Invalid target: {self.target}")
            elif self.filename != Path():
                error(self.rownr, f"Empty target should not have a file ({self.filename})")
        elif self.target == "clear":
            if self.filename != Path():
                error(self.rownr, f"Target '{self.target}' should not have a file ({self.filename})")
        elif self.filename == Path():
            warning(self.rownr, f"Missing file for target '{self.target}'")
        else:
            if not self.filename.suffix:
                self.filename = self.filename.with_suffix(TARGET_SUFFIXES[self.target][0])
            if self.filename.suffix not in TARGET_SUFFIXES[self.target]:
                error(self.rownr, f"Unrecognised file extension ({self.filename.suffix}) for target '{self.target}'")


def warning(rownr: Any, msg: Any):
    logging.warning(f"[row {rownr}] {msg}")
    STATISTICS["warnings"] += 1

def error(rownr: Any, msg: Any):
    logging.error(f"[ERROR in row {rownr}] {msg}")
    STATISTICS["errors"] += 1


def get_free_id(line: int, nodes: YamlDict) -> str:
    for letter in string.ascii_lowercase:
        new_id = f"{line}{letter}"
        if new_id not in nodes:
            return new_id
    raise RuntimeError("Couldn't find free id")


def get_actions(
    row: CsvRow,
    assets_dir: Path,
    node_id: str,
    last_image_id: str,
    node_index: int,
) -> tuple[list[YamlDict], str]:

    actions: list[YamlDict] = []
    if row.target in ["clear", "image"] and last_image_id:
        if row.fade > 0:
            actions.append({
                "target": "image",
                "cmd": "fade",
                "params": {
                    "entityId": last_image_id,
                    "target": 0,
                    "time": row.fade,
                    "stopOnDone": True,
                },
            })
        else:
            actions.append({
                "target": "image",
                "cmd": "destroy",
                "params": {
                    "entityId": last_image_id,
                },
            })

    entity_id = f"{node_id} - {row.filename}"
    if row.target in ["image", "video", "audio"]:
        params: YamlDict = {"entityId": entity_id}
        if row.target in ["image", "video"]:
            params["visible"] = True
            params["layer"] = MAX_LEVEL-node_index-1 if row.target == "image" else MAX_LEVEL
            if row.fade and not actions:
                # If we already have an action, then we know it's a previous image
                # that will be removed, so we don't have to fade this one in.
                params["fadeIn"] = {"from": 0, "to": 1, "time": row.fade}
        actions.insert(0, {
            "target": row.target,
            "cmd": "create",
            "assets": [{"path": str(assets_dir / row.filename)}],
            "params": params,
        })

    image_id_to_remove = entity_id if row.target == "image" else ""
    return actions, image_id_to_remove


def convert_opus(csv_rows: list[CsvRow], script: Path, assets_dir: Path) -> YamlDict:
    nodes: YamlDict = {}
    start_node = ""
    last_id = ""
    last_image_id = ""

    for node_index, row in enumerate(csv_rows):
        current_id = get_free_id(row.rownr, nodes)
        node: YamlDict = {"prompt": row.cue}

        if row.filename:
            actions, image_id_to_remove = get_actions(
                row, assets_dir, current_id, last_image_id, node_index
            )
            node["actions"] = actions
            if image_id_to_remove:
                last_image_id = image_id_to_remove

        nodes[current_id] = node

        if last_id:
            nodes[last_id]["next"] = current_id
        else:
            start_node = current_id
        last_id = current_id

    nodes[last_id]["next"] = start_node
    if not start_node:
        error(0, "Start node was never set. Does your csv file have any rows?")

    return {
        "startNode": start_node,
        "nodes": nodes,
        "action_templates": {},
        "assets": {"script": {"path": str(script)}},
        "ui": {"shortcuts": []},
    }


def main(args: argparse.Namespace):
    csv_rows: list[CsvRow] = []
    with open(args.input, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                csv_rows.append(CsvRow(row))
            except ValueError as err:
                error(row.get(ROWNR), f"{err.__class__.__name__}: {err}")

    script = args.script.relative_to(args.output.parent)
    assets_dir = args.assets_dir.relative_to(args.output.parent)
    opus = convert_opus(csv_rows, script, assets_dir)

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
    print("Done...", STATISTICS)
