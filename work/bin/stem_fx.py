#!/usr/bin/env python3
"""Per-instrument 60s effects on a render: Demucs stems -> fuzz/echo per stem -> remix.

  python3 work/bin/stem_fx.py <render.wav> [--preset medium|heavy|all] [--lufs -14]
      [--stems DIR]   (default: <project>/logs/demucs/htdemucs_6s/<render stem>/)

Run Demucs first: demucs -n htdemucs_6s -d mps -o <project>/logs/demucs <render.wav>
Stems used: guitar (fuzz + tape slapback), bass (valve grit), drums (saturation + room
echo in medium, 1.2 s convolution room reverb in heavy).
vocals/other/piano are dropped. Each processed stem is set to a target mean level taken from
the original's balance (--balance <original stems dir>; default Velvet Opera Intro:
bass -19.5, drums -17.7, guitar -21.8 dB), then the mix is
loudness-normalised. Writes <render stem>_fx-<preset>.wav next to the render.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

TARGET_DB = {"bass": -19.5, "drums": -17.7, "guitar": -21.8}

PRESETS = {
    "medium": {
        "guitar": "highpass=f=120,volume=16dB,asoftclip=type=atan:oversample=4,volume=8dB,"
                  "asoftclip=type=hard:threshold=0.8:oversample=4,equalizer=f=1200:t=q:w=1:g=3,"
                  "lowpass=f=5000,aecho=0.9:0.8:120|240:0.35|0.15",
        "bass": "volume=8dB,asoftclip=type=tanh:oversample=4,lowpass=f=3500",
        "drums": "volume=4dB,asoftclip=type=tanh:oversample=4,aecho=0.9:0.8:45|90:0.2|0.1",
    },
    "heavy": {
        "guitar": "highpass=f=140,volume=24dB,asoftclip=type=atan:oversample=4,volume=12dB,"
                  "asoftclip=type=hard:threshold=0.7:oversample=4,equalizer=f=1000:t=q:w=1:g=5,"
                  "lowpass=f=4500,aecho=0.9:0.85:180|360:0.45|0.25",
        "bass": "volume=14dB,asoftclip=type=atan:oversample=4,lowpass=f=3000",
        # (chain, (reverb seconds, wet dB)) — user: heavy echo on drums too much, use reverb
        "drums": ("volume=8dB,asoftclip=type=atan:oversample=4", (1.2, -10.0)),
    },
}


def mean_db(path: Path) -> float:
    """Mean volume (dB) via ffmpeg volumedetect."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    return float(re.search(r"mean_volume: ([-0-9.]+) dB", err).group(1))


def ffmpeg(args: list[str]) -> None:
    """Run ffmpeg quietly, raising on failure."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def make_ir(path: Path, seconds: float) -> None:
    """Synthesise a stereo room impulse response: decaying, band-limited, decorrelated noise."""
    ffmpeg(["-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=pink:a=0.5:seed=1",
            "-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=pink:a=0.5:seed=2",
            "-filter_complex", f"[0][1]amerge=inputs=2,afade=t=out:st=0:d={seconds}:curve=exp,"
            "highpass=f=250,lowpass=f=7000", "-ar", "48000", "-c:a", "pcm_f32le", str(path)])


def process_stem(src: Path, spec: str | tuple, target_db: float, out: Path) -> None:
    """Apply an effects chain (+ optional convolution reverb), then gain to the target level."""
    chain, reverb = (spec, None) if isinstance(spec, str) else spec
    if reverb is None:
        ffmpeg(["-i", str(src), "-af", chain, "-c:a", "pcm_f32le", str(out)])
    else:
        seconds, wet_db = reverb
        ir = out.with_name(f"ir_{seconds:g}s.wav")
        make_ir(ir, seconds)
        ffmpeg(["-i", str(src), "-i", str(ir), "-filter_complex",
                f"[0:a]{chain},aformat=channel_layouts=stereo,asplit[d][w];"
                f"[w][1:a]afir=irnorm=1[r];[r]volume={wet_db}dB[rw];"
                f"[d][rw]amix=inputs=2:normalize=0:duration=first",
                "-c:a", "pcm_f32le", str(out)])
    gain = target_db - mean_db(out)
    ffmpeg(["-i", str(out), "-af", f"volume={gain:.2f}dB", "-c:a", "pcm_f32le", str(out) + ".tmp.wav"])
    Path(str(out) + ".tmp.wav").replace(out)


def render(render_path: Path, stems: Path, preset: str, lufs: float, targets: dict) -> Path:
    """Process the three stems for a preset and mix them to one file."""
    tmp = []
    for name, chain in PRESETS[preset].items():
        out = stems / f"{name}_fx-{preset}.wav"
        process_stem(stems / f"{name}.wav", chain, targets[name], out)
        tmp.append(out)
    final = render_path.with_name(f"{render_path.stem}_fx-{preset}.wav")
    inputs = [arg for p in tmp for arg in ("-i", str(p))]
    ffmpeg([*inputs, "-filter_complex",
            f"amix=inputs={len(tmp)}:normalize=0,loudnorm=I={lufs}:TP=-1:LRA=11",
            "-ar", "48000", "-c:a", "pcm_s24le", str(final)])
    return final


def main() -> int:
    """Render the requested preset(s)."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("render")
    ap.add_argument("--preset", default="all", choices=[*PRESETS, "all"])
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--stems")
    ap.add_argument("--balance", help="dir of the ORIGINAL song's stems; match their levels "
                    "(default: Velvet Opera Intro balance)")
    a = ap.parse_args()
    targets = ({n: mean_db(Path(a.balance) / f"{n}.wav") for n in TARGET_DB}
               if a.balance else TARGET_DB)
    print("stem targets (dB):", {n: round(v, 1) for n, v in targets.items()})
    src = Path(a.render)
    stems = Path(a.stems) if a.stems else src.parents[1] / "logs" / "demucs" / "htdemucs_6s" / src.stem
    for preset in PRESETS if a.preset == "all" else [a.preset]:
        print(render(src, stems, preset, a.lufs, targets).name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
