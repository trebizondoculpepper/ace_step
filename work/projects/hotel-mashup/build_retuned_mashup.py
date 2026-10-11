"""Build a private 2:56 crossed-lyric arrangement with an overlapping chorus.

Uses the original separated voices, locally retuned toward opposite melodies.
The approximation changes pitch and timing and can introduce audible artifacts.
Run with cached librosa using uv --offline --no-project --python 3.11 --with librosa.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from build_crossed_choruses import HERE, STRETCH, cut_audio
from number_renders import find_render, number_renders
from retune_crossed_vocals import retune

STEMS = HERE / "logs" / "demucs" / "htdemucs_6s"
HC = STEMS / "hotel-california_original" / "vocals.wav"
VLAK = STEMS / "vlak_original" / "vocals.wav"


def prepare_verse(label: str, hc_start: float, hc_length: float,
                  vlak_start: float, vlak_length: float) -> Path:
    """Retune an English verse excerpt toward the corresponding Vlak verse."""
    source = HERE / "logs" / f"{label}-words.wav"
    target = HERE / "logs" / f"{label}-tune.wav"
    output = HERE / "renders" / f"{label}.wav"
    cut_audio(HC, source, hc_start, hc_length)
    cut_audio(VLAK, target, vlak_start, vlak_length, STRETCH)
    retune(source, target, output)
    return output


def prepare_outro() -> Path:
    """Repeat the second English chorus ending and retune it to Vlak's chorus."""
    source = HERE / "logs" / "outro-words.wav"
    repeated = HERE / "logs" / "outro-words-repeat.wav"
    target = HERE / "logs" / "outro-tune.wav"
    output = HERE / "renders" / "retuned-outro.wav"
    cut_audio(HC, source, 195.52, 13.39)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "1", "-i", str(source),
                    "-t", "26.78", str(repeated)], check=True)
    cut_audio(VLAK, target, 117.31, 28.67, STRETCH)
    retune(repeated, target, output)
    return output


def mix_arrangement(verse1: Path, verse2: Path, outro: Path) -> None:
    """Mix crossed verses and choruses, overlapping both parts in chorus three."""
    serbian = find_render("retuned-vlak-words-hotel-tune.wav")
    english = find_render("retuned-hotel-words-vlak-tune.wav")
    tracks = [(verse1, 13.05, 0), (serbian, 42.115, 0), (verse2, 68.215, 0),
              (english, 98.080, 0), (serbian, 123.895, -0.35),
              (english, 123.895, 0.35), (outro, 149.975, 0)]
    args = ["-i", str(HERE / "source" / "swap_instrumental.wav")]
    graph = "[0:a]volume=0.6[band];"
    for index, (path, start, pan) in enumerate(tracks, 1):
        args += ["-i", str(path)]
        left, right = (1 - pan) / 2, (1 + pan) / 2
        graph += (f"[{index}:a]pan=stereo|c0={left}*c0|c1={right}*c0,"
                  "acompressor=threshold=0.15:ratio=3:attack=10:release=100,"
                  f"volume=0.8,adelay={round(start * 1000)}:all=1[v{index}];")
    graph += "[band]" + "".join(f"[v{i}]" for i in range(1, len(tracks) + 1))
    graph += (f"amix=inputs={len(tracks) + 1}:normalize=0:duration=first,"
              "afade=t=out:st=173.3:d=2.5,loudnorm=I=-14:TP=-1:LRA=11[out]")
    output = HERE / "renders" / "crossed-overlap_master.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s24le", str(output)],
                   check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(output), "-c:a", "libmp3lame",
                    "-b:a", "320k", str(output.with_suffix(".mp3"))], check=True)
    renamed = number_renders(output.parent)
    output = output.with_name(renamed.get(output.name, output.name))
    print(f"Wrote {output.name} and .mp3", flush=True)


def main() -> None:
    """Prepare the remaining crossed vocals and write the mastered arrangement."""
    verse1 = prepare_verse("retuned-verse1", 52.41, 24.97, 26.78, 32.29)
    verse2 = prepare_verse("retuned-verse2", 77.38, 26.28, 84.13, 33.18)
    outro = prepare_outro()
    mix_arrangement(verse1, verse2, outro)


if __name__ == "__main__":
    main()
