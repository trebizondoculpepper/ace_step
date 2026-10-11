"""Conservatively move sustained vocal notes onto backing-chord tones.

Passing notes and brief syllables stay intact. This offline phase-vocoder method
preserves words but can produce artifacts; it is not a formant-preserving vocoder.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

ANALYSIS_SR = 16000
HOP = 256
CHORDS = {"Bm": (11, 2, 6), "F#": (6, 10, 1), "A": (9, 1, 4), "E": (4, 8, 11),
          "G": (7, 11, 2), "D": (2, 6, 9), "Em": (4, 7, 11)}


def nearest_shift(note: int, chord: str) -> int:
    """Return the smallest change to a chord tone, limited to two semitones."""
    options = [step for step in (0, -1, 1, -2, 2) if (note + step) % 12 in CHORDS[chord]]
    return options[0] if options else 0


def correction_curve(audio: np.ndarray, sr: int, chords: tuple[str, ...]) -> np.ndarray:
    """Find sustained voiced notes and return a sparse frame-wise semitone correction."""
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    analysis = librosa.resample(mono, orig_sr=sr, target_sr=ANALYSIS_SR)
    pitch, voiced, probability = librosa.pyin(analysis, sr=ANALYSIS_SR, fmin=75, fmax=850,
                                             frame_length=1024, hop_length=HOP)
    notes = np.round(librosa.hz_to_midi(np.nan_to_num(pitch, nan=440))).astype(int)
    times = np.arange(len(notes)) * HOP / ANALYSIS_SR
    duration = len(audio) / sr
    indices = np.minimum((times / duration * len(chords)).astype(int), len(chords) - 1)
    reliable = voiced & (probability >= 0.5)
    shifts = np.zeros(len(notes))
    start = 0
    while start < len(notes):
        end = start + 1
        while (end < len(notes) and notes[end] == notes[start]
               and indices[end] == indices[start] and reliable[end] == reliable[start]):
            end += 1
        if reliable[start] and (end - start) * HOP / ANALYSIS_SR >= 0.18:
            shifts[start:end] = nearest_shift(int(notes[start]), chords[indices[start]])
        start = end
    voiced_count = max(int(np.sum(reliable)), 1)
    print(f"Corrected {np.sum(shifts != 0) / voiced_count:.1%} of reliable voiced frames",
          flush=True)
    return np.interp(np.arange(len(audio)) / sr, times, shifts)


def shift_windows(audio: np.ndarray, sr: int, shifts: np.ndarray) -> np.ndarray:
    """Pitch-shift overlapping windows, preserving duration and unchanged windows."""
    mono = audio.ndim == 1
    data = audio[:, None] if mono else audio
    width = 8192 if sr >= 32000 else 4096
    hop, padding = width // 4, width // 2
    padded = np.pad(data, ((padding, padding), (0, 0)))
    result, weights = np.zeros_like(padded), np.zeros(len(padded))
    window = np.hanning(width)
    for start in range(0, len(data), hop):
        chunk = padded[start:start + width]
        if len(chunk) != width:
            break
        shift = float(shifts[min(start, len(shifts) - 1)])
        if shift:
            chunk = librosa.effects.pitch_shift(chunk.T, sr=sr, n_steps=shift,
                                                n_fft=2048).T
        result[start:start + width] += chunk * window[:, None]
        weights[start:start + width] += window
    result = (result / np.maximum(weights[:, None], 1e-8))[padding:padding + len(data)]
    return result[:, 0] if mono else result


def correct_file(source: Path, output: Path, chords: tuple[str, ...]) -> None:
    """Write corrected vocals at the original sample rate and channel count."""
    audio, sr = sf.read(source)
    shifts = correction_curve(audio, sr, chords)
    result = shift_windows(audio, sr, shifts)
    peak = float(np.max(np.abs(result)))
    if peak > 0.99:
        result *= 0.99 / peak
    sf.write(output, result, sr, subtype="PCM_24")
