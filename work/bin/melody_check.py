#!/usr/bin/env python3
"""Score how closely renders follow the source's melody/harmony (pitch-class content over time).

  .venv/bin/python work/bin/melody_check.py <source.wav> <render.wav> [<render.wav> ...]

Computes a 12-bin chroma (pitch-class) profile every ~0.19 s with numpy, then the mean
frame-wise cosine similarity between source and render (best over a +/-0.5 s lag).
Timbre-independent, so a reggae band playing the same tune should still score high.

Reference points printed for scale:
  self      = source vs itself (1.0)
  unrelated = source vs a time-shifted copy of itself (same key/instruments, wrong notes)
A render near or below "unrelated" has lost the tune.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 22050
HOP = 4096
FMIN, FMAX = 65.0, 2100.0  # C2..C7: covers bass lines through lead melodies


def load_mono(path: Path) -> np.ndarray:
    """Decode any audio file to mono float32 at SR via ffmpeg."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def chroma(x: np.ndarray) -> np.ndarray:
    """Return an L2-normalised (frames, 12) pitch-class energy matrix."""
    n_fft = HOP * 2
    win = np.hanning(n_fft).astype(np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::HOP] * win
    mag = np.abs(np.fft.rfft(frames, axis=1))
    freqs = np.fft.rfftfreq(n_fft, 1 / SR)
    band = (freqs >= FMIN) & (freqs <= FMAX)
    pc = np.round(12 * np.log2(freqs[band] / 440.0)).astype(int) % 12
    out = np.zeros((mag.shape[0], 12), dtype=np.float32)
    for k in range(12):
        out[:, k] = mag[:, band][:, pc == k].sum(axis=1)
    out = np.log1p(out)
    out -= out.mean(axis=1, keepdims=True)  # remove broadband loudness; keep pitch shape
    return out / (np.linalg.norm(out, axis=1, keepdims=True) + 1e-9)


def similarity(a: np.ndarray, b: np.ndarray, max_lag: int = 3) -> float:
    """Mean frame-wise cosine similarity, best over small time lags."""
    best = -1.0
    for lag in range(-max_lag, max_lag + 1):
        x, y = (a[lag:], b) if lag >= 0 else (a, b[-lag:])
        n = min(len(x), len(y))
        best = max(best, float((x[:n] * y[:n]).sum(axis=1).mean()))
    return best


def main() -> int:
    """Print melody-similarity scores for each render against the source."""
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = chroma(load_mono(Path(sys.argv[1])))
    shift = len(src) // 3
    print(f"{'self':<28} {similarity(src, src):.3f}")
    print(f"{'unrelated (shifted source)':<28} {similarity(src[shift:], src[:-shift], 0):.3f}")
    for r in sys.argv[2:]:
        print(f"{Path(r).name:<28} {similarity(src, chroma(load_mono(Path(r)))):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
