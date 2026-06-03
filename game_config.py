#!/usr/bin/env python3

import json
import os
from copy import deepcopy
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LEVELS_PATH = BASE_DIR / "levels" / "levels.json"
BLOCK_SIDE = 64

DEFAULT_PROGRESS = {
    "sizeX": 1024,
    "sizeY": 768,
    "FPS": 60,
    "level": 1,
    "P1_keyboard": True,
    "P2_keyboard": True,
    "P1_keys": [
        "K_a",
        "K_d",
        "K_SPACE",
        "K_g",
        "K_p",
        "K_r",
        "K_t",
        "K_v",
        "K_ESCAPE",
        "K_1",
        "K_2",
        "K_d",
        "K_a",
        "K_w",
        "K_s",
    ],
    "P2_keys": [
        "K_KP1",
        "K_KP2",
        "K_KP0",
        "K_KP3",
        "K_KP4",
        "K_KP5",
        "K_KP6",
        "K_KP7",
        "K_z",
        "K_KP8",
        "K_KP9",
        "K_RIGHT",
        "K_LEFT",
        "K_UP",
        "K_DOWN",
    ],
    "multiplayer": False,
    "music": True,
}

TILE_TYPES = {
    "g": "ground",
    "p": "platform",
    "w": "wall",
    "s": "slime",
    "h": "heal",
    "d": "door",
    "e": "goal",
    "m": "mage",
}
BLOCK_TYPES = {"ground", "platform", "wall", "heal", "door", "goal"}


def configured_progress_path():
    explicit_path = os.environ.get("MEGA_GAME_PROGRESS")
    if explicit_path:
        return Path(explicit_path).expanduser()

    data_dir = os.environ.get("MEGA_GAME_DATA_DIR")
    if data_dir:
        return Path(data_dir).expanduser() / "progress.json"

    return BASE_DIR / "progress.json"


def save_progress(progress, path=None):
    path = Path(path or configured_progress_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as progress_file:
        json.dump(progress, progress_file, indent=2, sort_keys=True)
        progress_file.write("\n")
    tmp_path.replace(path)


def load_progress(path=None):
    path = Path(path or configured_progress_path())
    progress = {}
    changed = True

    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as progress_file:
                progress = json.load(progress_file)
            changed = False
        except (OSError, json.JSONDecodeError, TypeError):
            broken_path = path.with_suffix(path.suffix + ".broken")
            try:
                path.replace(broken_path)
            except OSError:
                pass

    for key, value in DEFAULT_PROGRESS.items():
        if key not in progress:
            progress[key] = deepcopy(value)
            changed = True

    for key in ("sizeX", "sizeY", "FPS", "level"):
        try:
            progress[key] = int(progress[key])
        except (TypeError, ValueError):
            progress[key] = DEFAULT_PROGRESS[key]
            changed = True

    for key in ("P1_keyboard", "P2_keyboard", "multiplayer", "music"):
        progress[key] = bool(progress[key])

    for key in ("P1_keys", "P2_keys"):
        if not isinstance(progress[key], list) or len(progress[key]) != 15:
            progress[key] = deepcopy(DEFAULT_PROGRESS[key])
            changed = True

    if changed:
        save_progress(progress, path)

    return progress, path


def load_level_rows():
    with LEVELS_PATH.open("r", encoding="utf-8") as levels_file:
        payload = json.load(levels_file)
    return payload["levels"]


def available_levels():
    return sorted(int(level_number) for level_number in load_level_rows())


def next_level(current_level):
    levels = available_levels()
    for level_number in levels:
        if level_number > int(current_level):
            return level_number
    return levels[0]


def build_level(level_number, size_y, block_side=BLOCK_SIDE):
    levels = load_level_rows()
    rows = levels.get(str(level_number))
    if rows is None:
        raise ValueError(f"Level {level_number} is not defined in {LEVELS_PATH}")

    floor_y = int(size_y) - block_side / 2
    blocks = []
    foes = []
    background = []

    for line, row in enumerate(reversed(rows)):
        if isinstance(row, list):
            row = row[0]
        for column, tile in enumerate(row):
            thing = TILE_TYPES.get(tile)
            if thing is None:
                continue

            x = column * block_side
            y = floor_y - line * block_side

            if thing in BLOCK_TYPES:
                blocks.append((thing, x, y))
            elif thing == "slime":
                foes.append((thing, x, y))
            elif thing == "mage":
                background.append((thing, x, y))

    return blocks, foes, background
