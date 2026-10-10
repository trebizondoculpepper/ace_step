#!/usr/bin/env python3
"""Describe an audio file numerically: a section timeline plus global tempo and key.

  .venv/bin/python work/bin/describe_audio.py <audio> [--start S] [--end S] [--window 15]

Per window: loudness (RMS dBFS), brightness (spectral centroid Hz), bass/mid/high energy
share, onset rate (rhythmic busyness, onsets/s) and dominant pitch classes.
Global: tempo estimate (onset autocorrelation) and key (Krumhansl profile match).
numpy + ffmpeg only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np

SR = 22050
N_FFT = 2048
HOP = 512
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def load(path: Path, start: float, end: float | None) -> np.ndarray:
    """Decode a time range of an audio file to mono float32 at SR."""
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if end is not None:
        cmd += ["-t", str(end - start)]
    cmd += ["-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def spectrogram(x: np.ndarray) -> np.ndarray:
    """Magnitude STFT, shape (frames, bins)."""
    frames = np.lib.stride_tricks.sliding_window_view(x, N_FFT)[::HOP] * np.hanning(N_FFT)
    return np.abs(np.fft.rfft(frames, axis=1)).astype(np.float32)


def onset_envelope(mag: np.ndarray) -> np.ndarray:
    """Half-wave-rectified log spectral flux per frame."""
    logm = np.log1p(mag)
    return np.maximum(np.diff(logm, axis=0), 0).sum(axis=1)


def count_onsets(env: np.ndarray) -> int:
    """Count local peaks above an adaptive threshold."""
    if len(env) < 16:
        return 0
    thr = np.convolve(env, np.ones(16) / 16, mode="same") * 1.5 + 1e-6
    peaks = (env[1:-1] > env[:-2]) & (env[1:-1] >= env[2:]) & (env[1:-1] > thr[1:-1])
    return int(peaks.sum())


def tempo(env: np.ndarray) -> float:
    """Tempo in BPM from onset-envelope autocorrelation (60-180 BPM)."""
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    fps = SR / HOP
    lags = np.arange(int(fps * 60 / 180), int(fps * 60 / 60))
    return 60 * fps / lags[np.argmax(ac[lags])]


def chroma(mag: np.ndarray) -> np.ndarray:
    """Total energy per pitch class (12,) over 55 Hz - 2 kHz."""
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    band = (freqs >= 55) & (freqs <= 2000)
    pc = np.round(12 * np.log2(freqs[band] / 440.0)).astype(int) % 12 + 9
    out = np.zeros(12)
    np.add.at(out, pc % 12, mag[:, band].sum(axis=0))
    return out


def key(ch: np.ndarray) -> tuple[str, float]:
    """Best-matching major/minor key and its correlation."""
    best = ("?", -1.0)
    for i in range(12):
        for name, prof in (("major", MAJOR), ("minor", MINOR)):
            r = float(np.corrcoef(ch, np.roll(prof, i))[0, 1])
            if r > best[1]:
                best = (f"{NOTES[i]} {name}", r)
    return best


def band_shares(mag: np.ndarray) -> tuple[float, float, float]:
    """Energy share below 250 Hz, 250 Hz-4 kHz, above 4 kHz."""
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    p = (mag ** 2).sum(axis=0)
    tot = p.sum() + 1e-12
    return p[freqs < 250].sum() / tot, p[(freqs >= 250) & (freqs < 4000)].sum() / tot, p[freqs >= 4000].sum() / tot


def mmss(t: float) -> str:
    """Seconds -> M:SS."""
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def main() -> int:
    """Print the section timeline and global descriptors."""
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--window", type=float, default=15.0)
    a = ap.parse_args()

    x = load(Path(a.audio), a.start, a.end)
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    w = int(a.window * SR)
    print(f"{'time':>11}  {'dBFS':>5}  {'bright':>6}  {'bass/mid/high %':>15}  {'onsets/s':>8}  top notes")
    for i in range(0, len(x) - N_FFT, w):
        seg = x[i:i + w]
        if len(seg) < N_FFT * 2:
            break
        mag = spectrogram(seg)
        rms = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
        cent = float((mag * freqs).sum() / (mag.sum() + 1e-9))
        lo, mid, hi = band_shares(mag)
        rate = count_onsets(onset_envelope(mag)) / (len(seg) / SR)
        top = " ".join(NOTES[k] for k in np.argsort(chroma(mag))[::-1][:3])
        t0 = a.start + i / SR
        print(f"{mmss(t0):>5}-{mmss(t0 + len(seg) / SR):<5}  {rms:5.1f}  {cent:6.0f}  "
              f"{lo * 100:4.0f}/{mid * 100:3.0f}/{hi * 100:3.0f}       {rate:8.2f}  {top}")
    mag = spectrogram(x)
    k, r = key(chroma(mag))
    print(f"\nRange {mmss(a.start)}-{mmss(a.start + len(x) / SR)}: tempo ~{tempo(onset_envelope(mag)):.0f} BPM, "
          f"key ~{k} (r={r:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
