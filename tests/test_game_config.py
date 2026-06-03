import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from game_config import (
    DEFAULT_PROGRESS,
    available_levels,
    build_level,
    load_progress,
    next_level,
    save_progress,
)
from level_tools import summarize_level


class GameConfigTests(unittest.TestCase):
    def test_build_level_finds_expected_content(self):
        blocks, foes, background = build_level(2, 768)

        self.assertGreater(len(blocks), 300)
        self.assertEqual(len(foes), 3)
        self.assertEqual(len(background), 2)
        self.assertEqual(blocks[0][0], "ground")

    def test_next_level_wraps(self):
        levels = available_levels()

        self.assertEqual(next_level(levels[-1]), levels[0])

    def test_load_progress_repairs_invalid_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            progress_path = Path(temp_dir) / "progress.json"
            progress_path.write_text(
                json.dumps(
                    {
                        "sizeX": "tiny",
                        "sizeY": 100,
                        "FPS": 999,
                        "level": 999,
                        "P1_keyboard": "false",
                        "P2_keyboard": "true",
                        "P1_keys": [],
                        "P2_keys": DEFAULT_PROGRESS["P2_keys"],
                        "multiplayer": "yes",
                        "music": "no",
                    }
                ),
                encoding="utf-8",
            )

            progress, _ = load_progress(progress_path)

            self.assertEqual(progress["sizeX"], DEFAULT_PROGRESS["sizeX"])
            self.assertEqual(progress["sizeY"], 480)
            self.assertEqual(progress["FPS"], 240)
            self.assertEqual(progress["level"], available_levels()[0])
            self.assertFalse(progress["P1_keyboard"])
            self.assertTrue(progress["P2_keyboard"])
            self.assertEqual(progress["P1_keys"], DEFAULT_PROGRESS["P1_keys"])
            self.assertTrue(progress["multiplayer"])
            self.assertFalse(progress["music"])

    def test_save_progress_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            progress_path = Path(temp_dir) / "nested" / "progress.json"

            save_progress(DEFAULT_PROGRESS, progress_path)

            self.assertTrue(progress_path.exists())

    def test_level_summary_uses_json_levels(self):
        output = StringIO()

        with redirect_stdout(output):
            summarize_level(1)

        self.assertIn("Level 1: 243 blocks, 2 foes, 0 background sprites", output.getvalue())


if __name__ == "__main__":
    unittest.main()
