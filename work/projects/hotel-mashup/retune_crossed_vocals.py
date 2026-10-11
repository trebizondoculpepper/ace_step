"""Retune the original chorus words toward the other chorus's vocal pitch contour.

This local fallback preserves the source words. Short overlapping pitch-shifted
windows approximate the other melody; expect processed vocals and imperfect phrasing.
Run with cached librosa using uv --offline --no-project --python 3.11 --with librosa.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from number_renders import number_renders

HERE = Path(__file__).resolve().parent
SR = 16000
HOP = 256


def pitch_curve(audio: np.ndarray, length: int) -> np.ndarray:
    """Interpolate voiced pitches to a continuous sample-wise curve of given length."""
    pitch, _, _ = librosa.pyin(audio, sr=SR, fmin=75, fmax=850,
                              frame_length=1024, hop_length=HOP)
    voiced = np.isfinite(pitch)
    if not voiced.any():
        raise ValueError("No vocal pitch found")
    times = np.arange(len(pitch)) * HOP / max(len(audio) - 1, 1)
    return np.interp(np.linspace(0, 1, length), times[voiced], pitch[voiced])


def retune(source: Path, target: Path, output: Path) -> None:
    """Stretch source words to target length and retune overlapping vocal windows."""
    voice, _ = sf.read(source)
    guide, _ = sf.read(target)
    voice = librosa.effects.time_stretch(voice, rate=len(voice) / len(guide))
    voice = librosa.util.fix_length(voice, size=len(guide))
    original = pitch_curve(voice, len(voice))
    desired = pitch_curve(guide, len(voice))
    # Keep each singer's register while using the other melody's pitch classes.
    octave = round(np.log2(np.median(original) / np.median(desired)))
    shifts = 12 * np.log2(desired * 2 ** octave / original)
    shifts = np.clip(shifts, -12, 12)
    width, hop = 4096, 1024
    padding = width // 2
    padded = np.pad(voice, (padding, padding))
    result, weights = np.zeros_like(padded), np.zeros_like(padded)
    window = np.hanning(width)
    for start in range(0, len(voice), hop):
        center = min(start, len(shifts) - 1)
        shift = float(np.median(shifts[max(0, center - hop // 2):center + hop // 2 + 1]))
        chunk = padded[start:start + width]
        if len(chunk) != width:
            break
        shifted = librosa.effects.pitch_shift(chunk, sr=SR, n_steps=shift, n_fft=1024)
        result[start:start + width] += shifted * window
        weights[start:start + width] += window
    result = (result / np.maximum(weights, 1e-8))[padding:padding + len(voice)]
    peak = np.max(np.abs(result))
    sf.write(output, result / max(peak, 1e-9) * 0.8, SR, subtype="PCM_24")
    # This measures pitch agreement only, not word alignment or listening quality.
    rendered = pitch_curve(result, len(result))
    cents = 1200 * np.log2(rendered / (desired * 2 ** octave))
    print(f"{output.name}: {len(result) / SR:.2f}s; median pitch error "
          f"{np.median(np.abs(cents)):.0f} cents", flush=True)


def main() -> None:
    """Write the two crossed original-vocal chorus tracks for mixing."""
    hc = HERE / "logs" / "cross-vlak-words-vocal.wav"
    vlak = HERE / "logs" / "cross-hotel-words-vocal.wav"
    retune(vlak, hc, HERE / "renders" / "retuned-vlak-words-hotel-tune.wav")
    retune(hc, vlak, HERE / "renders" / "retuned-hotel-words-vlak-tune.wav")
    for name in number_renders(HERE / "renders").values():
        print(name, flush=True)


if __name__ == "__main__":
    main()
