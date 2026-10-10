"""Tests for MLX cover-noise initialisation (parity with PyTorch generate_audio)."""

import unittest

import numpy as np

from acestep.models.mlx.cover_noise_init import apply_cover_noise_init

SCHEDULE = [1.0, 0.9545, 0.9, 0.8333, 0.75, 0.6429, 0.5, 0.3]


class ApplyCoverNoiseInitTest(unittest.TestCase):
    """Behaviour of ``apply_cover_noise_init``."""

    def setUp(self):
        """Create deterministic noise/source arrays."""
        self.noise = np.full((1, 4, 2), 2.0, dtype=np.float32)
        self.src = np.zeros((1, 4, 2), dtype=np.float32)

    def test_zero_strength_is_noop(self):
        """Strength 0 returns the original noise and full schedule (non-target default path)."""
        xt, sched = apply_cover_noise_init(SCHEDULE, self.noise, self.src, 0.0)
        self.assertIs(xt, self.noise)
        self.assertEqual(sched, SCHEDULE)

    def test_missing_source_is_noop(self):
        """Without source latents the call is a no-op even with strength > 0."""
        xt, sched = apply_cover_noise_init(SCHEDULE, self.noise, None, 0.5)
        self.assertIs(xt, self.noise)
        self.assertEqual(sched, SCHEDULE)

    def test_blends_and_truncates_at_nearest_timestep(self):
        """Strength 0.5 starts at t=0.5: xt = 0.5*noise + 0.5*src and schedule from 0.5."""
        xt, sched = apply_cover_noise_init(SCHEDULE, self.noise, self.src, 0.5)
        self.assertEqual(sched, [0.5, 0.3])
        np.testing.assert_allclose(xt, np.full((1, 4, 2), 1.0))

    def test_strength_changes_output(self):
        """Regression: different strengths must yield different starts (was ignored on MLX)."""
        xt_a, _ = apply_cover_noise_init(SCHEDULE, self.noise, self.src, 0.4)
        xt_b, _ = apply_cover_noise_init(SCHEDULE, self.noise, self.src, 0.6)
        self.assertFalse(np.allclose(xt_a, xt_b))


if __name__ == "__main__":
    unittest.main()
