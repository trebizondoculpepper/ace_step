#!/usr/bin/env python3
"""Turn a render into a seamless loop, optionally extended to a video length.

  .venv/bin/python work/bin/loop.py <render.wav> [--trim 8] [--xfade 6] \
      [--minutes M] [--lufs -18] [--fade 4]

Steps:
  1. Trim --trim seconds off both ends (drops ACE-Step's intro swell / ending fade).
  2. Seamless loop: the last --xfade seconds are equal-power crossfaded into the first
     --xfade seconds, and the head is dropped, so end -> start is continuous.
  3. Gain to --lufs integrated loudness (static gain, peak-limited to -1 dBTP headroom).
     -18 LUFS suits a bed under voice; YouTube normalises music to about -14.
Writes <stem>_loop.wav next to the input; with --minutes also <stem>_<M>min.wav
(loop repeated to length, with --fade s fade in/out).
Given a *_loop.wav, it skips steps 1-3 and only extends: loop.py x_loop.wav --minutes 10
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

SR = 48000


def load_stereo(path: Path) -> np.ndarray:
    """Decode to float32 stereo at 48 kHz, shape (samples, 2)."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def save_wav(x: np.ndarray, path: Path) -> None:
    """Write float32 stereo as 24-bit WAV."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-c:a", "pcm_s24le", str(path)],
        input=x.astype(np.float32).tobytes(), check=True,
    )


def make_loop(x: np.ndarray, xfade_s: float) -> np.ndarray:
    """Equal-power crossfade the tail into the head; result loops seamlessly."""
    n = int(xfade_s * SR)
    if len(x) < 3 * n:
        raise ValueError("audio too short for this crossfade")
    t = np.linspace(0, np.pi / 2, n, dtype=np.float32)[:, None]
    blended = x[-n:] * np.cos(t) + x[:n] * np.sin(t)
    return np.concatenate([x[n:-n], blended])


def integrated_lufs(path: Path) -> float:
    """Measure integrated loudness with ffmpeg's loudnorm analyser."""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "loudnorm=print_format=json",
         "-f", "null", "-"], capture_output=True, text=True, check=True,
    ).stderr
    stats, _ = json.JSONDecoder().raw_decode(err[err.rindex("{"):])
    return float(stats["input_i"])


def apply_gain(x: np.ndarray, current_lufs: float, target_lufs: float) -> np.ndarray:
    """Static gain to the target loudness, capped so peaks stay below -1 dBFS."""
    gain_db = target_lufs - current_lufs
    peak = float(np.abs(x).max()) + 1e-9
    gain_db = min(gain_db, -1.0 - 20 * np.log10(peak))
    return x * (10 ** (gain_db / 20))


def extend(loop: np.ndarray, minutes: float, fade_s: float) -> np.ndarray:
    """Repeat the loop to the requested length and apply fade in/out."""
    n = int(minutes * 60 * SR)
    out = np.tile(loop, (n // len(loop) + 1, 1))[:n].copy()
    f = int(fade_s * SR)
    ramp = np.linspace(0, 1, f, dtype=np.float32)[:, None]
    out[:f] *= ramp
    out[-f:] *= ramp[::-1]
    return out


def main() -> int:
    """Build the loop (and optional extended bed) and report what was written."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("render")
    ap.add_argument("--trim", type=float, default=8.0)
    ap.add_argument("--xfade", type=float, default=6.0)
    ap.add_argument("--minutes", type=float)
    ap.add_argument("--lufs", type=float, default=-18.0)
    ap.add_argument("--fade", type=float, default=4.0)
    a = ap.parse_args()

    src = Path(a.render)
    if src.stem.endswith("_loop"):
        # Already a finished loop: extend it as-is (no re-trim, re-crossfade or re-gain).
        if not a.minutes:
            raise SystemExit("Input is already a loop; pass --minutes to extend it.")
        loop, stem = load_stereo(src), src.stem[: -len("_loop")]
    else:
        x = load_stereo(src)
        k = int(a.trim * SR)
        loop = make_loop(x[k:len(x) - k], a.xfade)
        out = src.with_name(f"{src.stem}_loop.wav")
        save_wav(loop, out)
        loop = apply_gain(loop, integrated_lufs(out), a.lufs)
        save_wav(loop, out)
        print(f"{out.name}: {len(loop) / SR:.1f}s loop, {integrated_lufs(out):.1f} LUFS")
        stem = src.stem

    if a.minutes:
        bed = src.with_name(f"{stem}_{a.minutes:g}min.wav")
        save_wav(extend(loop, a.minutes, a.fade), bed)
        print(f"{bed.name}: {a.minutes:g} min, fades {a.fade:g}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
