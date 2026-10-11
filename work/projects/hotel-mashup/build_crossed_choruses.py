"""Build private chorus guides with wordless vocal pitches and the opposite lyrics.

Run locally with cached librosa: uv run --offline --no-project --python 3.11
--with librosa python work/projects/hotel-mashup/build_crossed_choruses.py.
The synthesized lead removes source phonetics while retaining its pitch contour.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
SR = 16000
HOP = 256
STRETCH = 0.906 / 0.8155


def cut_audio(source: Path, output: Path, start: float, length: float,
              stretch: float = 1.0) -> None:
    """Cut a source section and optionally change tempo without changing pitch."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(length),
                    "-i", str(source), "-af", f"atempo={stretch}", "-ar", str(SR),
                    "-ac", "1", str(output)], check=True)


def synthesize_pitch(source: Path, output: Path) -> None:
    """Render the vocal pitch contour as a harmonic tone with the vocal envelope."""
    audio, _ = sf.read(source)
    pitch, voiced, _ = librosa.pyin(audio, sr=SR, fmin=75, fmax=850,
                                   frame_length=1024, hop_length=HOP)
    frames = np.arange(len(pitch)) * HOP
    samples = np.arange(len(audio))
    good = np.isfinite(pitch)
    if not np.any(good):
        raise ValueError(f"No voiced pitches detected: {source}")
    frequencies = np.interp(samples, frames[good], pitch[good])
    envelope = librosa.feature.rms(y=audio, frame_length=1024, hop_length=HOP)[0]
    amplitude = np.interp(samples, frames, envelope[:len(frames)] * voiced)
    phase = 2 * np.pi * np.cumsum(frequencies) / SR
    tone = sum(np.sin(n * phase) / n for n in range(1, 5)) * amplitude
    peak = np.max(np.abs(tone))
    sf.write(output, tone / max(peak, 1e-9) * 0.35, SR)


def build_chorus(name: str, song: str, source_start: float, source_length: float,
                 slot_start: float, slot_length: float, stretch: float) -> None:
    """Combine a wordless melody guide with its matching instrumental section."""
    logs = HERE / "logs"
    vocal = logs / f"{name}-vocal.wav"
    tone = logs / f"{name}-pitch.wav"
    band = logs / f"{name}-band.wav"
    cut_audio(logs / "demucs" / "htdemucs_6s" / song / "vocals.wav",
              vocal, source_start, source_length, stretch)
    synthesize_pitch(vocal, tone)
    cut_audio(HERE / "source" / "swap_instrumental.wav", band, slot_start, slot_length)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(band), "-i", str(tone),
                    "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0",
                    "-ar", "48000", "-ac", "2", str(HERE / "source" / f"{name}.wav")],
                   check=True)
    print(f"Built {name}: {slot_length:.1f}s wordless melody guide", flush=True)


def main() -> None:
    """Prepare both crossed chorus guides and private lyric files."""
    lyrics = (HERE / "source" / "swap_lyrics.txt").read_text()
    for name, tag in [("cross-vlak-words", "Chorus 1"), ("cross-hotel-words", "Chorus 2")]:
        lines = lyrics.split(f"[{tag}]", 1)[1].split("[", 1)[0].strip()
        (HERE / "source" / f"{name}.txt").write_text(f"[Chorus]\n{lines}\n")
    build_chorus("cross-vlak-words", "hotel-california_original", 104.56, 26.10,
                 42.1, 26.1, 1.0)
    build_chorus("cross-hotel-words", "vlak_original", 59.07, 28.68,
                 98.1, 25.8, STRETCH)


if __name__ == "__main__":
    main()
