"""Apply measured two-pass loudness mastering to private local WAV renders."""

import json
import subprocess
from pathlib import Path


def normalize_master(path: Path) -> None:
    """Replace a WAV with a 48 kHz/24-bit master targeting -14 LUFS and -1 dBTP."""
    settings = "loudnorm=I=-14:TP=-1:LRA=11"
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                             settings + ":print_format=json", "-f", "null", "-"],
                            capture_output=True, text=True, check=True)
    stats, _ = json.JSONDecoder().raw_decode(result.stderr[result.stderr.rfind("{"):])
    measured = (f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
                f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
                f":offset={stats['target_offset']}:linear=true")
    temporary = path.with_name(path.stem + "_normalizing.wav")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-af",
                        settings + measured + ",aresample=192000,"
                        "alimiter=limit=0.84:level=false:latency=true,aresample=48000",
                        "-ar", "48000", "-c:a", "pcm_s24le",
                        str(temporary)], check=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
