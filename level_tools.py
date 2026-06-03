#!/usr/bin/env python3

from game_config import DEFAULT_PROGRESS, available_levels, build_level


def count_label(count, singular, plural=None):
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"


def summarize_level(level_number, size_y=DEFAULT_PROGRESS["sizeY"]):
    blocks, foes, background = build_level(level_number, size_y)
    goals = sum(1 for block in blocks if block[0] == "goal")
    print(
        f"Level {level_number}: "
        f"{count_label(len(blocks), 'block')}, {count_label(len(foes), 'foe', 'foes')}, "
        f"{count_label(len(background), 'background sprite')}, {count_label(goals, 'exit')}"
    )


def summarize_all_levels(size_y=DEFAULT_PROGRESS["sizeY"]):
    for level_number in available_levels():
        summarize_level(level_number, size_y)


if __name__ == "__main__":
    summarize_all_levels()
