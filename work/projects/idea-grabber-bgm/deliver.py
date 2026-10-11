#!/usr/bin/env python3
"""Pick a take per brief, master it and deliver it to the Idea Grabber repo.

  .venv/bin/python work/projects/idea-grabber-bgm/deliver.py [--dest /path/to/idea_grabber]

Per brief: choose the take whose measured tempo best matches the requested BPM (ties: more
music before the trailing silence), trim to the last audible sound + 0.25 s with a 0.5 s fade,
two-pass loudnorm to -16 LUFS / -1.5 dBTP (headroom for MP3), then write
  assets/audio-masters/bgm/<id>.wav  (PCM 24-bit, 48 kHz stereo)
  public/audio/bgm/<id>.mp3          (192 kbps CBR, 48 kHz stereo)
  public/audio/bgm/manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "bin"))
from describe_audio import load, onset_envelope, spectrogram, tempo  # noqa: E402

LUFS, TP = -16.0, -1.5


def run(args: list[str]) -> str:
    """Run ffmpeg/ffprobe and return stderr (where ffmpeg reports analysis)."""
    return subprocess.run(args, capture_output=True, text=True, check=True).stderr


def music_end(path: Path) -> float:
    """Time where the final stretch of silence (< -45 dB) begins, or the file length."""
    err = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
               "silencedetect=n=-45dB:d=0.3", "-f", "null", "-"])
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()[2])
    starts = [float(s) for s in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = re.findall(r"silence_end: ([\d.]+)", err)
    trailing = starts and (len(ends) < len(starts) or float(ends[-1]) >= dur - 0.05)
    return starts[-1] if trailing else dur


def folded_bpm(path: Path, target: int) -> float:
    """Measured tempo, folded by octaves (x2 / /2) towards the requested tempo."""
    bpm = tempo(onset_envelope(spectrogram(load(path, 0, None))))
    while bpm < target / 1.41:
        bpm *= 2
    while bpm > target * 1.41:
        bpm /= 2
    return bpm


def choose(brief: dict) -> tuple[Path, float, float]:
    """Return (take, folded bpm, music end) of the best take."""
    takes = sorted((HERE / "renders").glob(f"{brief['id']}_*.wav"))
    scored = []
    for t in takes:
        bpm, end = folded_bpm(t, brief["bpm"]), music_end(t)
        ok_len = 20.0 <= end <= 40.0
        scored.append((not ok_len, round(abs(bpm - brief["bpm"]) / brief["bpm"], 2), -end, t, bpm, end))
    best = min(scored)
    return best[3], best[4], best[5]


def master(src: Path, end: float, wav: Path, mp3: Path) -> None:
    """Trim + fade, loudness-normalise (two-pass), write the WAV master and MP3."""
    cut = min(end + 0.25, 40.0)
    pre = f"atrim=0:{cut:.3f},afade=t=out:st={cut - 0.5:.3f}:d=0.5"
    err = run(["ffmpeg", "-hide_banner", "-i", str(src), "-af",
               f"{pre},loudnorm=I={LUFS}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"])
    m, _ = json.JSONDecoder().raw_decode(err[err.rindex("{\n"):])
    ln = (f"loudnorm=I={LUFS}:TP={TP}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
          f":offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"{pre},{ln}", "-ar", "48000",
         "-ac", "2", "-c:a", "pcm_s24le", str(wav)])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k",
         "-ar", "48000", "-ac", "2", str(mp3)])


def measure(path: Path) -> tuple[float, float, float]:
    """(duration s, integrated LUFS, true peak dBTP)."""
    err = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true",
               "-f", "null", "-"])
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(path)], capture_output=True, text=True,
                               check=True).stdout)
    summary = err[err.rindex("Summary:"):]
    i = float(re.search(r"I:\s+([-\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+([-\d.]+) dBFS", summary).group(1))
    return dur, i, peak


def title(stem: str) -> str:
    """'bgm-01-neon-roadtrip' -> 'Neon Roadtrip'."""
    return " ".join(w.capitalize() for w in stem.split("-")[2:])


def main() -> int:
    """Master every brief and write the manifest."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="/Users/sal/PycharmProjects/idea_grabber")
    a = ap.parse_args()
    pub = Path(a.dest) / "public" / "audio" / "bgm"
    mas = Path(a.dest) / "assets" / "audio-masters" / "bgm"
    pub.mkdir(parents=True, exist_ok=True)
    mas.mkdir(parents=True, exist_ok=True)
    tracks = []
    for b in json.loads((HERE / "briefs.json").read_text()):
        if not list((HERE / "renders").glob(f"{b['id']}_*.wav")):
            print(f"{b['id']:32s} MISSING (no renders)")
            continue
        take, bpm, end = choose(b)
        wav, mp3 = mas / f"{b['id']}.wav", pub / f"{b['id']}.mp3"
        master(take, end, wav, mp3)
        dur, lufs, peak = measure(mp3)
        good_bpm = abs(bpm - b["bpm"]) / b["bpm"] <= 0.06
        print(f"{b['id']:32s} {take.stem[-1]} {dur:5.1f}s {lufs:6.1f} LUFS {peak:5.1f} dBTP "
              f"bpm {bpm:5.1f}/{b['bpm']}{'' if good_bpm else '  -> null'}", flush=True)
        tracks.append({
            "id": b["id"], "title": title(b["id"]), "genre": b["genre"],
            "file": mp3.name, "masterFile": wav.name, "durationSeconds": round(dur, 1),
            "bpm": round(bpm) if good_bpm else None,
            "pasticheOfGame": b["game"], "pasticheOfTheme": b["theme"], "notes": b["notes"],
        })
    (pub / "manifest.json").write_text(
        json.dumps({"version": 1, "tracks": tracks}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"manifest: {len(tracks)} tracks -> {pub / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
