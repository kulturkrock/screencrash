import argparse
from pathlib import Path
import csv
from dataclasses import dataclass
import yaml
from typing import Any, Optional
import string
import os.path


@dataclass
class CsvRow:
    line_number: int
    cue: str
    filename: Optional[str]
    fade: Optional[int]


def get_free_id(line_number: int, nodes: dict):
    new_id = str(line_number)
    alphabet = list(string.ascii_lowercase)
    while new_id in nodes:
        new_id = str(line_number) + alphabet.pop(0)
    return new_id


def get_actions(
    filename: str,
    fade: Optional[int],
    asset_dirname: str,
    node_id: str,
    last_image_id: str,
    node_index: int,
):
    extension = filename.split(".")[-1]
    if extension in ["png"]:
        target = "image"
    elif extension in ["mp4"]:
        target = "video"
    elif extension in ["wav", "mp3"]:
        target = "audio"
    else:
        raise RuntimeError(f"Unknown filetype '{extension}'")

    if target == "image" and last_image_id is not None:
        if fade is not None:
            remove_action = {
                "target": "image",
                "cmd": "fade",
                "params": {
                    "entityId": last_image_id,
                    "target": 0,
                    "time": fade,
                    "stopOnDone": True,
                },
            }
        else:
            remove_action = {
                "target": "image",
                "cmd": "destroy",
                "params": {
                    "entityId": last_image_id,
                },
            }
    else:
        remove_action = None

    entity_id = f"{node_id}_{filename}"
    if target == "image":
        params = {
            "entityId": entity_id,
            "visible": True,
            "layer": 9999 - node_index,
        }
        if (
            fade is not None and remove_action is None
        ):  # If we have a previous image we fade that out instead
            params["fadeIn"] = {"from": 0, "to": 1, "time": fade}
    elif target == "video":
        params = {"entityId": entity_id, "visible": True, "layer": 10000}
        if fade is not None:
            params["fadeIn"] = {"from": 0, "to": 1, "time": fade}
    elif target == "audio":
        params = {"entityId": entity_id}
    else:
        raise RuntimeError(f"Somehow unknown target '{target}'")

    create_action = {
        "target": target,
        "cmd": "create",
        "assets": [{"path": os.path.join(asset_dirname, filename)}],
        "params": params,
    }

    image_id_to_remove = entity_id if target == "image" else None

    if remove_action is not None:
        return [create_action, remove_action], image_id_to_remove
    else:
        return [create_action], image_id_to_remove


def convert_opus(
    csv_rows: list[CsvRow], script_filename: str, asset_dirname: str
) -> dict[str, Any]:
    nodes = {}
    start_node = None
    last_id = None
    last_image_id = None

    for i, row in enumerate(csv_rows):
        current_id = get_free_id(row.line_number, nodes)

        node = {"prompt": row.cue}

        if row.filename is not None:
            actions, image_id_to_remove = get_actions(
                row.filename, row.fade, asset_dirname, current_id, last_image_id, i
            )
            node["actions"] = actions
            if image_id_to_remove is not None:
                last_image_id = image_id_to_remove

        nodes[current_id] = node

        if last_id is not None:
            nodes[last_id]["next"] = current_id
        else:
            start_node = current_id
        last_id = current_id
    nodes[last_id]["next"] = start_node

    if start_node is None:
        raise RuntimeError(
            "Start node was never set. Does your csv file have any rows?"
        )

    return {
        "startNode": start_node,
        "nodes": nodes,
        "action_templates": {},
        "assets": {"script": {"path": script_filename}},
        "ui": {"shortcuts": []},
    }


def main(input_file: Path, output_file: Path, script_filename: str, asset_dirname: str):
    csv_rows: list[CsvRow] = []
    with open(input_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_rows.append(
                CsvRow(
                    line_number=int(row["Radnummer"]),
                    cue=row["Stickreplik"],
                    filename=row["Filnamn"] or None,
                    fade=(
                        int(row["Fade-in-tid i sekunder"])
                        if row["Fade-in-tid i sekunder"]
                        else None
                    ),
                )
            )

    opus = convert_opus(csv_rows, script_filename, asset_dirname)

    with open(output_file, "w") as f:
        yaml.safe_dump(opus, f, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to convert an exported Google sheet to YAML opus format"
    )
    parser.add_argument(
        "input_file",
        help="CSV file exported from Google Sheets (File -> Download -> Comma Separated Values)",
    )
    parser.add_argument("output_file", help="Path to output file")
    parser.add_argument(
        "--script-filename",
        default="Vintergatan_20250202.pdf",
        help="The script (manus) PDF file. Assumed to be next to opus.",
    )
    parser.add_argument(
        "--asset-dirname",
        default="Till föreställningen",
        help="Directory name for assets. Assumed to be next to opus.",
    )
    args = parser.parse_args()
    main(
        Path(args.input_file),
        Path(args.output_file),
        args.script_filename,
        args.asset_dirname,
    )
