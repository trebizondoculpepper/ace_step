"""Test render ordering, shared format numbers, and preservation of existing versions."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from number_renders import find_render, number_renders


class TestNumberRenders(unittest.TestCase):
    """Exercise numbering using small fake audio files without audio dependencies."""

    def test_formats_share_number_and_oldest_mix_is_first(self) -> None:
        """A late MP3 conversion belongs to its earlier WAV render."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, timestamp in [("old.wav", 10), ("new.wav", 20), ("old.mp3", 30)]:
                path = root / name
                path.write_bytes(name.encode())
                os.utime(path, (timestamp, timestamp))
            mapping = number_renders(root)
            self.assertEqual(mapping, {"old.wav": "0001_old.wav", "old.mp3": "0001_old.mp3",
                                       "new.wav": "0002_new.wav"})
            self.assertEqual((root / "0001_old.wav").read_bytes(), b"old.wav")
            self.assertEqual(number_renders(root), {})

    def test_new_version_gets_next_number_and_latest_lookup(self) -> None:
        """Rerenders preserve the old version and become the latest lookup match."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "renders"
            root.mkdir()
            (root / "0012_mix.wav").write_bytes(b"old")
            (root / "mix.wav").write_bytes(b"new")
            self.assertEqual(number_renders(root), {"mix.wav": "0013_mix.wav"})
            self.assertEqual((root / "0012_mix.wav").read_bytes(), b"old")
            with patch("number_renders.HERE", root.parent):
                self.assertEqual(find_render("mix.wav"), root / "0013_mix.wav")
                with self.assertRaises(FileNotFoundError):
                    find_render("missing.wav")


if __name__ == "__main__":
    unittest.main()
