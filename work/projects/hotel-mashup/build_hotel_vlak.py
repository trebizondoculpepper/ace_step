"""Mix Hotel California instrumental stems with Vlak's real, selectively tuned vocals.

Run offline with cached librosa: uv run --offline --no-project --python 3.11
--with librosa python work/projects/hotel-mashup/build_hotel_vlak.py.
Writes corrected and unshifted private WAV/MP3 comparisons, about three minutes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from audio_master import normalize_master
from harmony_pitch import correct_file
from number_renders import number_renders

HERE = Path(__file__).resolve().parent
STEMS = HERE / "logs" / "demucs" / "htdemucs_6s"
INSTR = ("drums", "bass", "guitar", "other", "piano")
VERSE = ("Bm", "F#", "A", "E", "G", "D", "Em", "F#")
CHORUS = ("G", "D", "F#", "Bm", "G", "D", "Em", "F#")
# HC backing start/length, Vlak vocal start/length, backing chords.
SECTIONS = [
    (39.36, 13.05, None, 0, ()),
    (52.41, 52.15, 0.0, 59.07, VERSE),
    (104.56, 26.10, 59.07, 28.68, CHORUS),
    (130.66, 26.08, 87.75, 29.56, VERSE[:4]),
    (182.83, 26.08, 117.31, 28.67, CHORUS),
    (104.56, 26.10, 59.07, 28.68, CHORUS),
    (208.91, 13.05, None, 0, ()),
]


def prepare_band() -> Path:
    """Mix only Hotel California's five non-vocal stems."""
    output = HERE / "logs" / "hotel-only-band.wav"
    args = []
    for stem in INSTR:
        args += ["-i", str(STEMS / "hotel-california_original" / f"{stem}.wav")]
    graph = "".join(f"[{i}:a]" for i in range(len(INSTR)))
    graph += f"amix=inputs={len(INSTR)}:normalize=0[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(output)],
                   check=True)
    return output


def prepare_section(index: int, band: Path) -> tuple[Path, Path, Path]:
    """Cut HC backing and stretch the matching Vlak vocal; then tune sustained notes."""
    hc_start, length, vocal_start, vocal_length, chords = SECTIONS[index]
    backing = HERE / "logs" / f"hotel-vlak-{index}-band.wav"
    raw = HERE / "logs" / f"hotel-vlak-{index}-raw.wav"
    tuned = HERE / "logs" / f"hotel-vlak-{index}-tuned.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(hc_start), "-t", str(length),
                    "-i", str(band), "-af", "afade=t=in:d=0.02,afade=t=out:st="
                    f"{length - .02}:d=0.02", "-c:a", "pcm_f32le", str(backing)], check=True)
    if vocal_start is None:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=stereo", "-t", str(length), str(raw)], check=True)
        return backing, raw, raw
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(vocal_start),
                    "-t", str(vocal_length), "-i", str(STEMS / "vlak_original" / "vocals.wav"),
                    "-af", f"atempo={vocal_length / length},apad,atrim=duration={length}",
                    "-ar", "48000", "-c:a", "pcm_f32le", str(raw)], check=True)
    print(f"Section {index}: {length:.2f}s, Vlak vocals against {chords}", flush=True)
    correct_file(raw, tuned, chords)
    return backing, raw, tuned


def master(sections: list[tuple[Path, Path, Path]], corrected: bool) -> None:
    """Concatenate section mixes and master to WAV plus iPhone-compatible MP3."""
    args, graph = [], ""
    for index, (band, raw, tuned) in enumerate(sections):
        args += ["-i", str(band), "-i", str(tuned if corrected else raw)]
        graph += (f"[{index * 2}:a]volume=0.7[b{index}];"
                  f"[{index * 2 + 1}:a]acompressor=threshold=0.025:ratio=2.5:attack=10:"
                  f"release=100:makeup=1.5,volume=3.0[v{index}];"
                  f"[b{index}][v{index}]amix=inputs=2:normalize=0:duration=first[s{index}];")
    duration = sum(section[1] for section in SECTIONS)
    graph += "".join(f"[s{i}]" for i in range(len(sections)))
    graph += (f"concat=n={len(sections)}:v=0:a=1,afade=t=out:st={duration - 3}:d=3[out]")
    label = "hotel-band-vlak-vocals" + ("_master" if corrected else "_unshifted")
    output = HERE / "renders" / f"{label}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(output)],
                   check=True)
    normalize_master(output)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(output), "-c:a", "libmp3lame",
                    "-b:a", "320k", str(output.with_suffix(".mp3"))], check=True)
    renamed = number_renders(output.parent)
    output = output.with_name(renamed.get(output.name, output.name))
    print(f"Wrote {output.name} and .mp3 ({duration:.2f}s)", flush=True)


def main() -> None:
    """Prepare the band and vocal sections and write both comparisons."""
    band = prepare_band()
    sections = [prepare_section(index, band) for index in range(len(SECTIONS))]
    master(sections, corrected=True)
    master(sections, corrected=False)


if __name__ == "__main__":
    main()
