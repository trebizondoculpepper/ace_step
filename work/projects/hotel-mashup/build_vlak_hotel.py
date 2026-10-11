"""Build the inverse mash-up: Vlak's band with Hotel California's real vocals.

Use system Python: python3 work/projects/hotel-mashup/build_vlak_hotel.py.
Vocals are time-stretched without pitch changes, matching the preferred unshifted mix.
Add --original-choruses to retain Vlak's original chorus vocals and use HC only in verses.
All stem processing and mastering stay local; no generation server is needed.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from audio_master import normalize_master

HERE = Path(__file__).resolve().parent
STEMS = HERE / "logs" / "demucs" / "htdemucs_6s"
INSTR = ("drums", "bass", "guitar", "other", "piano")
# Vlak backing start/length, HC vocal start/length.
SECTIONS = [
    (145.98, 7.17, None, 0.0),
    (0.0, 59.07, 50.0, 53.66),
    (59.07, 28.68, 103.66, 24.82),
    (87.75, 29.56, 128.48, 27.26),
    (117.31, 28.67, 182.83, 26.08),
    (59.07, 28.68, None, 0.0),
]


def build_band() -> Path:
    """Mix Vlak's instrumental stems while excluding its vocal stem."""
    output = HERE / "logs" / "vlak-only-band.wav"
    inputs = []
    for stem in INSTR:
        inputs += ["-i", str(STEMS / "vlak_original" / f"{stem}.wav")]
    graph = "".join(f"[{i}:a]" for i in range(len(INSTR)))
    graph += f"amix=inputs={len(INSTR)}:normalize=0[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(output)],
                   check=True)
    return output


def build_section(index: int, band: Path,
                  original_choruses: bool = False) -> tuple[Path, Path]:
    """Cut backing and fit HC vocals, optionally retaining Vlak's untouched choruses."""
    start, length, vocal_start, vocal_length = SECTIONS[index]
    prefix = "vlak-hotel-hybrid" if original_choruses else "vlak-hotel"
    backing = HERE / "logs" / f"{prefix}-{index}-band.wav"
    vocal = HERE / "logs" / f"{prefix}-{index}-vocal.wav"
    fades = f"afade=t=in:d=0.02,afade=t=out:st={length - 0.02}:d=0.02"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(length),
                    "-i", str(band), "-af", fades, "-c:a", "pcm_f32le", str(backing)],
                   check=True)
    if vocal_start is None:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=stereo", "-t", str(length), str(vocal)], check=True)
    elif original_choruses and index in (2, 4):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start),
                        "-t", str(length), "-i", str(STEMS / "vlak_original" / "vocals.wav"),
                        "-af", fades, "-ar", "48000", "-c:a", "pcm_f32le", str(vocal)],
                       check=True)
    else:
        # Leave a small tail after chorus one rather than include the next verse's pickup.
        rate = 66.3 / 73.6 if index == 2 else vocal_length / length
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(vocal_start),
                        "-t", str(vocal_length), "-i",
                        str(STEMS / "hotel-california_original" / "vocals.wav"),
                        "-af", f"atempo={rate},apad,atrim=duration={length},{fades}",
                        "-ar", "48000", "-c:a", "pcm_f32le", str(vocal)], check=True)
    return backing, vocal


def mix_and_master(sections: list[tuple[Path, Path]],
                   original_choruses: bool = False) -> Path:
    """Mix stems, preserving original chorus balance when requested, and master locally."""
    inputs, graph = [], ""
    for index, (band, vocal) in enumerate(sections):
        inputs += ["-i", str(band), "-i", str(vocal)]
        # Balance the complete band sections, including Vlak's sparse verse opening.
        vocal_filter = ("volume=1.4" if original_choruses and index in (2, 4) else
                        "acompressor=threshold=0.08:ratio=2.5:attack=10:release=100:makeup=1.2")
        graph += (f"[{2 * index}:a]volume=1.4[b{index}];"
                  f"[{2 * index + 1}:a]{vocal_filter}[v{index}];"
                  f"[b{index}][v{index}]amix=inputs=2:normalize=0:duration=first[s{index}];")
    duration = sum(section[1] for section in SECTIONS)
    graph += "".join(f"[s{i}]" for i in range(len(sections)))
    graph += f"concat=n={len(sections)}:v=0:a=1,afade=t=out:st={duration - 3}:d=3[out]"
    label = ("vlak-hotel-verses-original-choruses" if original_choruses else
             "vlak-band-hotel-vocals_unshifted")
    output = HERE / "renders" / f"{label}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(output)],
                   check=True)
    normalize_master(output)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(output), "-c:a", "libmp3lame",
                    "-b:a", "320k", str(output.with_suffix(".mp3"))], check=True)
    return output


def main() -> None:
    """Build the requested vocal arrangement and report duration and processing time."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-choruses", action="store_true",
                        help="Keep Vlak's original choruses; replace only verse vocals with HC")
    options = parser.parse_args()
    started = time.monotonic()
    band = build_band()
    sections = [build_section(index, band, options.original_choruses)
                for index in range(len(SECTIONS))]
    output = mix_and_master(sections, options.original_choruses)
    print(f"Wrote {output.name} and .mp3; {sum(s[1] for s in SECTIONS):.2f}s audio; "
          f"{time.monotonic() - started:.1f}s processing", flush=True)


if __name__ == "__main__":
    main()
