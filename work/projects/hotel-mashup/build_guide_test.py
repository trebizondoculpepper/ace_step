"""Check layout routing without reading stems or running ffmpeg."""

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("build_guide", Path(__file__).with_name("build_guide.py"))
GUIDE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUIDE)


class TestLayoutRouting(unittest.TestCase):
    """Ensure swap variants share sections and keep the original layout intact."""

    def run_layout(self, layout: str) -> list:
        """Return mocked build calls for the requested CLI layout."""
        with patch("sys.argv", ["build_guide.py", "--layout", layout]), \
                patch.object(GUIDE, "build") as build, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GUIDE.main(), 0)
        return build.call_args_list

    def test_instrumental_swap_removes_only_vocals(self) -> None:
        """The fallback keeps swap timing and uses only instrumental stems."""
        calls = self.run_layout("swap-instrumental")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args, (GUIDE.SWAP_SECTIONS, GUIDE.INSTR,
                                       GUIDE.HERE / "source" / "swap_instrumental.wav"))
        self.assertNotIn("vocals", calls[0].args[1])

    def test_full_swap_retains_vocals(self) -> None:
        """Full-mix swap still includes the vocal stem."""
        calls = self.run_layout("swap")
        self.assertEqual(calls[0].args, (GUIDE.SWAP_SECTIONS, GUIDE.ALL,
                                       GUIDE.HERE / "source" / "swap_full.wav"))

    def test_original_mashup_outputs_are_preserved(self) -> None:
        """The original mashup still builds separate band and vocal tracks."""
        calls = self.run_layout("mashup")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args, (GUIDE.SECTIONS, GUIDE.INSTR,
                                       GUIDE.HERE / "source" / "guide.wav"))
        self.assertEqual(calls[1].args, (GUIDE.SECTIONS, ("vocals",),
                                       GUIDE.HERE / "source" / "vocals.wav"))


if __name__ == "__main__":
    unittest.main()
