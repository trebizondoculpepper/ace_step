"""Focused tests for conservative vocal harmony corrections."""

import unittest
from unittest.mock import patch

import numpy as np

from harmony_pitch import correction_curve, nearest_shift, shift_windows


class TestHarmonyPitch(unittest.TestCase):
    """Check note selection, preservation of passing notes, and audio duration."""

    def test_chord_tone_is_unchanged(self) -> None:
        """A D in B minor needs no shift."""
        self.assertEqual(nearest_shift(62, "Bm"), 0)

    def test_clashing_note_moves_by_one_semitone(self) -> None:
        """A D over F-sharp major moves down to C-sharp."""
        self.assertEqual(nearest_shift(62, "F#"), -1)

    def test_corrections_stay_within_two_semitones(self) -> None:
        """Every correction must stay within the intended conservative bound."""
        for note in range(60, 72):
            self.assertLessEqual(abs(nearest_shift(note, "A")), 2)

    def test_passing_notes_are_preserved(self) -> None:
        """A short non-chord note should remain unchanged."""
        pitch = np.full(63, 293.6648)
        pitch[4:9] = 329.6276
        data = np.zeros(16000)
        with patch("harmony_pitch.librosa.pyin", return_value=(
                pitch, np.ones(63, dtype=bool), np.ones(63))):
            curve = correction_curve(data, 16000, ("Bm",))
        np.testing.assert_array_equal(curve, 0)

    def test_sustained_clashing_note_is_corrected(self) -> None:
        """A confident held D over F-sharp major should shift to C-sharp."""
        with patch("harmony_pitch.librosa.pyin", return_value=(
                np.full(63, 293.6648), np.ones(63, dtype=bool), np.ones(63))):
            curve = correction_curve(np.zeros(16000), 16000, ("F#",))
        np.testing.assert_array_equal(curve, -1)

    def test_no_shift_preserves_samples_and_duration(self) -> None:
        """Window overlap must reconstruct unchanged audio, including both edges."""
        data = np.random.default_rng(7).normal(0, 0.1, (16000, 2))
        result = shift_windows(data, 16000, np.zeros(16000))
        np.testing.assert_allclose(result, data, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
