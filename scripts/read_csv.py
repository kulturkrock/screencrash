
import argparse
import logging
from pathlib import Path
import csv
from dataclasses import dataclass
from typing import Any
import string
import re

YamlDict = dict[str, Any]

ID = "Rad"
KILL = "Dödas"
CUE = "Stickreplik"
TARGET = "Filtyp"
FILENAME = "Filnamn"
FILENAME2 = "Filnamn2"
FADEIN = "Fade-in"
FADEOUT = "Fade-out"
LOOP = "Loop"
SILENT = "Tyst"
HOTKEY = "Snabbval"

TARGET_ALIASES = {
    "image": ["bild", "img"],
    "video": ["film"],
    "audio": ["ljud"],
    "ignore": ["?", "ignorera"]
}

TARGET_SUFFIXES: dict[str, list[str]] = {
    "image": [".jpg", ".gif", ".png"],
    "video": [".webm", ".mp4", ".mov"],
    "audio": [".wav", ".mp3"],
}

ALLOWED_HOTKEYS = set(string.ascii_lowercase + string.digits) - set("asqwert")
HOTKEY_MODIFIERS = {"shift", "ctrl", "alt"}

STATISTICS = {
    "warnings": 0,
    "errors": 0,
}


@dataclass(frozen=True, order=True)
class Id:
    row: int
    suffix: str
    def __init__(self, id: str):
        assert re.match(r"^\d+[a-z]?$", id)
        object.__setattr__(self, "row", int(re.sub(r"\D", "", id)))
        object.__setattr__(self, "suffix", re.sub(r"\d", "", id))
    def __str__(self) -> str:
        return f"{self.row}{self.suffix}"



@dataclass
class CsvRow:
    id: Id
    kill: Id | None
    cue: str
    target: str
    filename: Path | None
    filename2: Path | None
    fadein: float
    fadeout: float
    loop: int | None
    silent: bool
    hotkey: list[str]

    def __init__(self, row: dict[str, str], dir: Path):
        self.id = Id(row[ID])
        self.kill = Id(row[KILL]) if row[KILL] else None
        self.cue = re.sub(r"\s*\n\s*", "<br>", row[CUE])
        self.target = row[TARGET].lower()
        self.filename = Path(row[FILENAME]) if row[FILENAME] else None
        self.filename2 = Path(row[FILENAME2]) if row[FILENAME2] else None
        self.fadein = float(row[FADEIN] or 0)
        self.fadeout = float(row[FADEOUT] or 0)
        self.loop = 0 if row[LOOP].upper() == "L" else int(row[LOOP]) if row[LOOP] else None
        self.silent = row[SILENT].upper() in ["S", "T", "SILENT", "TYST"]
        self.hotkey = (row.get(HOTKEY) or "").lower().replace("+", " ").split()

        if self.kill:
            if self.kill < self.id:
                error(self.id, f"Kill row cannot come before id ({self.kill})")

        for target, aliases in TARGET_ALIASES.items():
            if self.target in aliases:
                self.target = target

        if self.target == "ignore":
            return

        if self.target not in TARGET_ALIASES:
            if self.target:
                error(self.id, f"Invalid target: {self.target!r}")
            elif self.filename:
                error(self.id, f"Empty target should not have a file ({self.filename})")
        elif not self.filename:
            warning(self.id, f"Missing file for target {self.target!r}")
        else:
            self.filename = dir / self.filename.parent / f"{self.id} {self.filename.name}"
            if not any(self.filename.with_suffix(suf).is_file() for suf in TARGET_SUFFIXES[self.target]):
                warning(self.id, f"Target '{self.target}' file does not exist ({self.filename})")

        if self.loop is not None:
            if self.target not in ["audio", "video"]:
                error(self.id, f"Looping only allowed for audios or videos, not {self.target!r}")
                self.loop = None

        if not self.silent:
            if row[SILENT]:
                error(self.id, f"Unknown specifier for silence: {row[SILENT]}")

        if self.filename2:
            if self.target not in ["audio", "video"]:
                error(self.id, f"Filename2 only allowed for audios or videos, not {self.target!r}")
                self.filename2 = None
            else:
                self.filename2 = dir / self.filename2.parent / f"{self.id}-2 {self.filename2.name}"
                if not any(self.filename2.with_suffix(suf).is_file() for suf in TARGET_SUFFIXES[self.target]):
                    warning(self.id, f"Target '{self.target}' file does not exist ({self.filename2})")

        if self.hotkey:
            if self.target not in TARGET_SUFFIXES:
                error(self.id, f"Shortcut cannot be used for target {self.target!r}")
                self.hotkey = []
            elif (self.hotkey[-1] not in ALLOWED_HOTKEYS
                  or set(self.hotkey[:-1]) - HOTKEY_MODIFIERS):
                error(self.id, f"Illegal shortcut hotkey ({self.hotkey})")
                self.hotkey = []


def warning(id: Any, msg: Any):
    logging.warning(f"{str(id):11s} | {msg}")
    STATISTICS["warnings"] += 1

def error(id: Any, msg: Any):
    logging.error(f"ERROR {str(id):5s} | {msg}")
    STATISTICS["errors"] += 1


def read_csv(file: Path, dir: Path) -> list[CsvRow]:
    csv_rows: list[CsvRow] = []
    ids: set[Id] = set()
    with open(file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k: v.strip() for k, v in row.items()}
            if not any(row.values()): continue
            try:
                crow = CsvRow(row, dir)
                if crow.target == "ignore":
                    warning(crow.id, f"Ignoring row")
                    continue
                if crow.id in ids:
                    error(crow.id, f"Id already exists")
                if ids and crow.id <= max(ids):
                    error(crow.id, f"Order mismatch: row should come before {max(ids)}")
                ids.add(crow.id)
                csv_rows.append(crow)
            except ValueError as err:
                print(row)
                error(row.get(ID), f"{err.__class__.__name__}: {err}")
    for crow in csv_rows:
        if crow.kill and crow.kill not in ids:
            error(crow.id, f"Killing id doesn't exist: {crow.kill}")
    return csv_rows


def main(args: argparse.Namespace):
    read_csv(args.input, args.assets_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to test that a script CSV is correct",
    )
    parser.add_argument(
        "--input", "-i", required=True, type=Path,
        help="CSV file exported from Google Sheets (File -> Download -> Comma Separated Values)",
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
