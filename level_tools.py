#!/usr/bin/env python3

from game_config import DEFAULT_PROGRESS, available_levels, build_level


def summarize_level(level_number, size_y=DEFAULT_PROGRESS["sizeY"]):
    blocks, foes, background = build_level(level_number, size_y)
    print(
        f"Level {level_number}: "
        f"{len(blocks)} blocks, {len(foes)} foes, {len(background)} background sprites"
    )


def summarize_all_levels(size_y=DEFAULT_PROGRESS["sizeY"]):
    for level_number in available_levels():
        summarize_level(level_number, size_y)


if __name__ == "__main__":
    summarize_all_levels()
