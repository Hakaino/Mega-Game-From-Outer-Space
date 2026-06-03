#!/usr/bin/env python3

import argparse
from copy import deepcopy

from game_config import DEFAULT_PROGRESS, load_progress, save_progress


def parse_args():
    parser = argparse.ArgumentParser(description="Edit Mega Game progress.json")
    parser.add_argument("--reset", action="store_true", help="restore default progress")
    parser.add_argument("--level", type=int, choices=(1, 2), help="level to start on")
    parser.add_argument("--width", type=int, help="window width")
    parser.add_argument("--height", type=int, help="window height")
    parser.add_argument("--fps", type=int, help="frame cap")
    parser.add_argument("--music", dest="music", action="store_true", help="enable music")
    parser.add_argument("--no-music", dest="music", action="store_false", help="disable music")
    parser.add_argument(
        "--multiplayer",
        dest="multiplayer",
        action="store_true",
        help="enable two players",
    )
    parser.add_argument(
        "--single-player",
        dest="multiplayer",
        action="store_false",
        help="disable two-player mode",
    )
    parser.set_defaults(music=None, multiplayer=None)
    return parser.parse_args()


def main():
    args = parse_args()
    progress, progress_file = load_progress()

    if args.reset:
        progress = deepcopy(DEFAULT_PROGRESS)

    if args.level is not None:
        progress["level"] = args.level
    if args.width is not None:
        progress["sizeX"] = args.width
    if args.height is not None:
        progress["sizeY"] = args.height
    if args.fps is not None:
        progress["FPS"] = args.fps
    if args.music is not None:
        progress["music"] = args.music
    if args.multiplayer is not None:
        progress["multiplayer"] = args.multiplayer

    save_progress(progress, progress_file)
    print(f"Progress saved to {progress_file}")


if __name__ == "__main__":
    main()
