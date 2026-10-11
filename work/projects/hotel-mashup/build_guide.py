#!/usr/bin/env python3
"""Assemble the verse/chorus mash-up: an instrumental guide + a matching vocal track.

  python3 work/projects/hotel-mashup/build_guide.py [--layout mashup|swap|swap-instrumental]

Same cuts for both outputs (so vocals stay aligned with anything rendered from the guide):
  source/guide.wav   instrumental stems (drums, bass, guitar, other, piano) per section
  source/vocals.wav  vocal stem per section
Vlak sections are time-stretched (pitch kept) to Hotel California's 73.6 BPM.
"""

from __future__ import annotations

import argparse
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
# Lyric swap: each slot keeps its melody, and the other song's words are sung over it.
SWAP_SECTIONS = [
    (HC, 39.36, 52.41, "intro"),
    (VLAK, 26.78, 59.07, "verse 1 (Vlak tune, HC words)"),
    (HC, 104.56, 130.66, "chorus 1 (HC tune, Vlak words)"),
    (VLAK, 84.13, 117.31, "verse 2 (Vlak tune, HC words)"),
    (VLAK, 59.07, 87.75, "chorus 2 (Vlak tune, HC words)"),
    (HC, 182.83, 208.91, "chorus 3 (HC tune, Vlak words)"),
    (VLAK, 117.31, 145.98, "outro (Vlak tune, HC words)"),
]
INSTR = ("drums", "bass", "guitar", "other", "piano")
ALL = (*INSTR, "vocals")


def section_filter(n: int, song: str, start: float, end: float, inputs: dict) -> str:
    """Filter chain that trims one section, stretches Vlak, and adds 20 ms edge fades."""
    tempo = f",atempo={STRETCH:.4f}" if song == VLAK else ""
    length = (end - start) / (STRETCH if song == VLAK else 1.0)
    return (f"[{inputs[song]}]atrim={start}:{end},asetpts=PTS-STARTPTS{tempo},"
            f"afade=t=in:d=0.02,afade=t=out:st={length - 0.02:.3f}:d=0.02[s{n}];")


def build(sections: list, stems: tuple[str, ...], out: Path) -> None:
    """Mix the given stems per song, cut the sections and concatenate them."""
    args, graph = [], ""
    for idx, song in enumerate((HC, VLAK)):
        for s in stems:
            args += ["-i", str(STEMS / song / f"{s}.wav")]
        first = idx * len(stems)
        refs = "".join(f"[{first + k}]" for k in range(len(stems)))
        mine = [n for n, sec in enumerate(sections) if sec[0] == song]
        graph += (f"{refs}amix=inputs={len(stems)}:normalize=0,asplit={len(mine)}"
                  + "".join(f"[{song}{n}]" for n in mine) + ";")
    for n, (song, start, end, _) in enumerate(sections):
        graph += section_filter(n, song, start, end, {song: f"{song}{n}"})
    graph += "".join(f"[s{n}]" for n in range(len(sections)))
    graph += f"concat=n={len(sections)}:v=0:a=1[cat];"
    graph += "[cat]areverse,afade=t=in:d=2.5,areverse[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s16le", str(out)], check=True)


def main() -> int:
    """Write the layout's audio files and print its section timeline."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", choices=["mashup", "swap", "swap-instrumental"],
                    default="mashup", help="mashup: guide + vocals; swap: full mix; "
                    "swap-instrumental: swap sections without vocals")
    a = ap.parse_args()
    sections = SECTIONS if a.layout == "mashup" else SWAP_SECTIONS
    t = 0.0
    for song, start, end, label in sections:
        length = (end - start) / (STRETCH if song == VLAK else 1.0)
        print(f"{int(t // 60)}:{t % 60:04.1f}  {label:31s} {'Vlak' if song == VLAK else 'Hotel California'}")
        t += length
    print(f"total {int(t // 60)}:{t % 60:04.1f}")
    if a.layout == "mashup":
        build(sections, INSTR, HERE / "source" / "guide.wav")
        build(sections, ("vocals",), HERE / "source" / "vocals.wav")
    elif a.layout == "swap":
        build(sections, ALL, HERE / "source" / "swap_full.wav")
    else:
        build(sections, INSTR, HERE / "source" / "swap_instrumental.wav")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
