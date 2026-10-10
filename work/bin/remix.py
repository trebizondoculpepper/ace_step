#!/usr/bin/env python3
"""Run one ACE-Step cover (remix) job for a work/ project, with ETA + elapsed feedback.

Talks to the local API directly (stdlib only) so every melody-related knob is reachable:

  python3 work/bin/remix.py <project> <label> "<caption>" \
      [--strength 0.9] [--noise 0.4] [--batch 2] [--seed N] [--thinking] [--source REL]

  --strength  audio_cover_strength: fraction of denoising steps that see the source
              structure (1.0 = all). Keep high (0.8-1.0) to preserve the tune.
  --noise     cover_noise_strength ("melody retention"): 0 = start from pure noise,
              1 = start at the source audio. 0.3-0.6 keeps melody while changing timbre.
  --thinking  let the 5Hz LM rewrite caption/metadata (off by default: it drifts).

Outputs: work/projects/<project>/renders/<label>_<n>.wav, params in logs/<label>.json,
timing appended to work/logs/timings.csv (feeds the next estimate).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "http://127.0.0.1:8001"
REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "work"
TIMINGS = WORK / "logs" / "timings.csv"


def api(path: str, payload: dict | None = None) -> dict:
    """POST (or GET when payload is None) JSON to the local API and return the parsed body."""
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def audio_duration(path: Path) -> float:
    """Return the duration of an audio file in seconds via ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def estimate_seconds(workload: float) -> tuple[float, int] | None:
    """Average seconds per generated audio-second over past cover runs, scaled to workload."""
    if not TIMINGS.exists():
        return None
    rates = [
        float(r["elapsed_s"]) / (float(r["duration_s"]) * float(r["batch"]))
        for r in csv.DictReader(TIMINGS.open())
        if r["task"] == "cover" and float(r["duration_s"]) * float(r["batch"]) > 0
    ]
    return (sum(rates) / len(rates) * workload, len(rates)) if rates else None


def fmt(seconds: float) -> str:
    """Format seconds as XmYYs."""
    return f"{int(seconds) // 60}m{int(seconds) % 60:02d}s"


def main() -> int:
    """Parse args, submit the job, poll with feedback, file outputs and record timing."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project"); p.add_argument("label"); p.add_argument("caption")
    p.add_argument("--strength", type=float, default=0.9)
    p.add_argument("--noise", type=float, default=0.4)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--thinking", action="store_true")
    p.add_argument("--source", help="repo-relative source path (default: <project>/source/trimmed.wav)")
    a = p.parse_args()

    pdir = WORK / "projects" / a.project
    src_rel = a.source or f"work/projects/{a.project}/source/trimmed.wav"
    if not (REPO / src_rel).exists():
        sys.exit(f"Source not found: {src_rel}")
    try:
        if not api("/health")["data"]["models_initialized"]:
            sys.exit("Server up but models not loaded. Run: work/bin/server.sh start")
    except OSError:
        sys.exit("Server not running. Run: work/bin/server.sh start")
    (pdir / "renders").mkdir(parents=True, exist_ok=True)
    (pdir / "logs").mkdir(parents=True, exist_ok=True)

    dur = round(audio_duration(REPO / src_rel))
    est = estimate_seconds(dur * a.batch)
    if est:
        print(f"Estimate: ~{fmt(est[0])} for {dur}s x {a.batch} takes (avg of {est[1]} past runs)")
    else:
        print("Estimate: no timing history yet; this run will calibrate future estimates.")

    payload = {
        "task_type": "cover",
        "src_audio_path": src_rel,
        "prompt": a.caption,
        "lyrics": "[Instrumental]",
        "audio_duration": dur,
        "batch_size": a.batch,
        "audio_cover_strength": a.strength,
        "cover_noise_strength": a.noise,
        "thinking": a.thinking,
        "use_cot_caption": a.thinking,
        "use_cot_language": False,
        "use_random_seed": a.seed < 0,
        "seed": a.seed,
        "audio_format": "wav",
    }
    (pdir / "logs" / f"{a.label}.json").write_text(json.dumps(payload, indent=2))
    print(f"Submitting {a.label}: strength={a.strength} noise={a.noise} batch={a.batch} "
          f"thinking={a.thinking}")

    start = time.time()
    resp = api("/release_task", payload)
    task_id = (resp.get("data") or {}).get("task_id")
    if not task_id:
        sys.exit(f"Failed to create job: {resp}")

    stop = threading.Event()
    threading.Thread(
        target=lambda: [print(f"  ...{fmt(time.time() - start)} elapsed", flush=True)
                        for _ in iter(lambda: stop.wait(30), True)],
        daemon=True,
    ).start()

    while True:
        time.sleep(3)
        item = api("/query_result", {"task_id_list": [task_id]})["data"][0]
        if item["status"] == 1:
            break
        if item["status"] == 2:
            stop.set()
            sys.exit(f"FAILED after {fmt(time.time() - start)}: {item.get('result') or item}")
    stop.set()

    results = json.loads(item["result"]) if isinstance(item["result"], str) else item["result"]
    files = []
    for n, r in enumerate(results, 1):
        out = pdir / "renders" / f"{a.label}_{n}.wav"
        urllib.request.urlretrieve(API + r["file"], out)
        files.append(out.name)
    elapsed = time.time() - start

    with TIMINGS.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                a.project, a.label, "cover", dur, a.batch, round(elapsed)])
    print(f"Done in {fmt(elapsed)}: {', '.join(files)} -> {pdir.relative_to(REPO)}/renders/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
