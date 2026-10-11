#!/usr/bin/env python3
"""Assemble the verse/chorus mash-up: an instrumental guide + a matching vocal track.

  python3 work/projects/hotel-mashup/build_guide.py

Same cuts for both outputs (so vocals stay aligned with anything rendered from the guide):
  source/guide.wav   instrumental stems (drums, bass, guitar, other, piano) per section
  source/vocals.wav  vocal stem per section
Vlak sections are time-stretched (pitch kept) to Hotel California's 73.6 BPM.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEMS = HERE / "logs" / "demucs" / "htdemucs_6s"
HC, VLAK = "hotel-california_original", "vlak_original"
STRETCH = 0.906 / 0.8155  # Vlak beat period / Hotel California beat period
SECTIONS = [  # (song, start s, end s, label)
    (HC, 39.36, 52.41, "intro"),
    (VLAK, 26.78, 59.07, "verse 1"),
    (HC, 104.56, 130.66, "chorus 1"),
    (VLAK, 84.13, 117.31, "verse 2"),
    (HC, 182.83, 208.91, "chorus 2"),
    (VLAK, 145.98, 181.81, "verse 3"),
    (HC, 104.56, 130.66, "chorus 1 (out)"),
]
INSTR = ("drums", "bass", "guitar", "other", "piano")


def section_filter(n: int, song: str, start: float, end: float, inputs: dict) -> str:
    """Filter chain that trims one section, stretches Vlak, and adds 20 ms edge fades."""
    tempo = f",atempo={STRETCH:.4f}" if song == VLAK else ""
    length = (end - start) / (STRETCH if song == VLAK else 1.0)
    return (f"[{inputs[song]}]atrim={start}:{end},asetpts=PTS-STARTPTS{tempo},"
            f"afade=t=in:d=0.02,afade=t=out:st={length - 0.02:.3f}:d=0.02[s{n}];")


def build(stems: tuple[str, ...], out: Path) -> None:
    """Mix the given stems per song, cut the sections and concatenate them."""
    args, graph, inputs = [], "", {}
    for idx, song in enumerate((HC, VLAK)):
        for s in stems:
            args += ["-i", str(STEMS / song / f"{s}.wav")]
        first = idx * len(stems)
        refs = "".join(f"[{first + k}]" for k in range(len(stems)))
        mine = [n for n, sec in enumerate(SECTIONS) if sec[0] == song]
        graph += (f"{refs}amix=inputs={len(stems)}:normalize=0,asplit={len(mine)}"
                  + "".join(f"[{song}{n}]" for n in mine) + ";")
    for n, (song, start, end, _) in enumerate(SECTIONS):
        graph += section_filter(n, song, start, end, {song: f"{song}{n}"})
    graph += "".join(f"[s{n}]" for n in range(len(SECTIONS)))
    graph += f"concat=n={len(SECTIONS)}:v=0:a=1[cat];"
    graph += "[cat]areverse,afade=t=in:d=2.5,areverse[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s16le", str(out)], check=True)


def main() -> int:
    """Write guide.wav and vocals.wav and print the section timeline."""
    t = 0.0
    for song, start, end, label in SECTIONS:
        length = (end - start) / (STRETCH if song == VLAK else 1.0)
        print(f"{int(t // 60)}:{t % 60:04.1f}  {label:15s} {'Vlak' if song == VLAK else 'Hotel California'}")
        t += length
    print(f"total {int(t // 60)}:{t % 60:04.1f}")
    build(INSTR, HERE / "source" / "guide.wav")
    build(("vocals",), HERE / "source" / "vocals.wav")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
