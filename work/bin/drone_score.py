#!/usr/bin/env python3
"""Screen generated drones: is it drone-like, and is it original vs the references?

  .venv/bin/python work/bin/drone_score.py --ref <ref.wav> [--ref ...] <render.wav> [...]

Per render:
  onsets/s   note/hit attacks per second (drone target: < ~1)
  dyn dB     std-dev of 1 s loudness (drone target: < ~6 dB; real refs measure ~4)
  bass %     energy share below 250 Hz
  bright     spectral centroid (Hz)
  vs <ref>   melody_check similarity to each reference. LOW is good here: it means the
             render does not reproduce the reference's notes (originality). For scale,
             ~0.4 is "same piece, wrong moment"; > ~0.7 means it is following it.
Verdict: DRONE if onsets/s < 1.0 and dyn < 6 dB; COPY? if any ref similarity > 0.6.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from describe_audio import SR, band_shares, count_onsets, load, onset_envelope, spectrogram  # noqa: E402
from melody_check import chroma as melody_chroma, load_mono, similarity  # noqa: E402


def loudness_spread(x: np.ndarray) -> float:
    """Std-dev in dB of 1-second RMS loudness, ignoring the first/last 3 s (fades)."""
    sec = x[: len(x) // SR * SR].reshape(-1, SR)[3:-3]
    db = 20 * np.log10(np.sqrt((sec ** 2).mean(axis=1)) + 1e-9)
    return float(db.std()) if len(db) else 0.0


def best_similarity(src: np.ndarray, render: np.ndarray) -> float:
    """Max chroma similarity over the reference's timeline (render may align anywhere)."""
    n = len(render)
    if len(src) <= n:
        return similarity(src, render)
    step = max(1, n // 4)
    return max(similarity(src[i:i + n], render) for i in range(0, len(src) - n + 1, step))


def main() -> int:
    """Print the screening table."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("renders", nargs="+")
    a = ap.parse_args()

    refs = [(Path(r).stem[:18], melody_chroma(load_mono(Path(r)))) for r in a.ref]
    head = f"{'render':<28} {'onsets/s':>8} {'dyn dB':>6} {'bass%':>5} {'bright':>6}"
    print(head + "".join(f"  {'vs ' + n:>21}" for n, _ in refs) + "  verdict")
    for r in a.renders:
        x = load(Path(r), 0.0, None)
        mag = spectrogram(x)
        rate = count_onsets(onset_envelope(mag)) / (len(x) / SR)
        dyn = loudness_spread(x)
        lo, _, _ = band_shares(mag)
        freqs = np.fft.rfftfreq(2048, 1 / SR)
        cent = float((mag * freqs).sum() / (mag.sum() + 1e-9))
        rc = melody_chroma(load_mono(Path(r)))
        sims = [best_similarity(c, rc) for _, c in refs]
        verdict = "DRONE" if rate < 1.0 and dyn < 6.0 else "busy"
        if any(s > 0.6 for s in sims):
            verdict += " COPY?"
        print(f"{Path(r).name:<28} {rate:8.2f} {dyn:6.1f} {lo * 100:5.0f} {cent:6.0f}"
              + "".join(f"  {s:21.2f}" for s in sims) + f"  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
