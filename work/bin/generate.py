#!/usr/bin/env python3
"""Run one ACE-Step generation job for a work/ project, with ETA + elapsed feedback.

Talks to the local API directly (stdlib only). Two tasks:

  # text-to-music, optionally with a reference for timbre/mix/atmosphere only
  python3 work/bin/generate.py <project> <label> "<caption>" --task text2music \
      --duration 130 [--ref REL] [--batch 4] [--seed N] [--bpm 140] [--key "C major"]

  # cover/remix of a source (keeps the source's notes and structure)
  python3 work/bin/generate.py <project> <label> "<caption>" --task cover \
      [--source REL] [--strength 0.9] [--noise 0.4] [--batch 2] [--seed N]

  --ref       reference_audio: time-averaged global timbre/mix/atmosphere hint. Does not
              carry melody or rhythm (docs/en/Tutorial.md "Reference Audio").
  --strength  (cover) audio_cover_strength: fraction of denoising steps that see the source.
  --noise     (cover) cover_noise_strength ("melody retention"): 0 = pure noise start.
  --thinking  let the 5Hz LM rewrite caption/metadata (off by default: it drifts).

Paths are repo-relative (the API rejects absolute paths).
Outputs: work/projects/<project>/renders/<label>_<n>.wav, params in logs/<label>.json,
timing appended to work/logs/timings.csv (feeds the next estimate, per task).
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


def estimate_seconds(task: str, workload: float) -> tuple[float, int] | None:
    """Average seconds per generated audio-second over past runs of a task, scaled to workload."""
    if not TIMINGS.exists():
        return None
    rates = [
        float(r["elapsed_s"]) / (float(r["duration_s"]) * float(r["batch"]))
        for r in csv.DictReader(TIMINGS.open())
        if r["task"] == task and float(r["duration_s"]) * float(r["batch"]) > 0
    ]
    return (sum(rates) / len(rates) * workload, len(rates)) if rates else None


def fmt(seconds: float) -> str:
    """Format seconds as XmYYs."""
    return f"{int(seconds) // 60}m{int(seconds) % 60:02d}s"


def main() -> int:
    """Parse args, submit the job, poll with feedback, file outputs and record timing."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project"); p.add_argument("label"); p.add_argument("caption")
    p.add_argument("--task", choices=["cover", "text2music"], default="cover")
    p.add_argument("--duration", type=int, help="seconds (text2music; cover uses source length)")
    p.add_argument("--ref", help="repo-relative reference audio (timbre/atmosphere hint)")
    p.add_argument("--strength", type=float, default=0.9)
    p.add_argument("--noise", type=float, default=0.4)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--thinking", action="store_true")
    p.add_argument("--bpm", type=int, help="tempo metadata (text2music)")
    p.add_argument("--key", help='key metadata, e.g. "C major"')
    p.add_argument("--source", help="repo-relative source path (default: <project>/source/trimmed.wav)")
    a = p.parse_args()

    pdir = WORK / "projects" / a.project
    src_rel = None
    if a.task == "cover":
        src_rel = a.source or f"work/projects/{a.project}/source/trimmed.wav"
        if not (REPO / src_rel).exists():
            sys.exit(f"Source not found: {src_rel}")
    elif not a.duration:
        sys.exit("--duration is required for text2music")
    if a.ref and not (REPO / a.ref).exists():
        sys.exit(f"Reference not found: {a.ref}")
    try:
        if not api("/health")["data"]["models_initialized"]:
            sys.exit("Server up but models not loaded. Run: work/bin/server.sh start")
    except OSError:
        sys.exit("Server not running. Run: work/bin/server.sh start")
    (pdir / "renders").mkdir(parents=True, exist_ok=True)
    (pdir / "logs").mkdir(parents=True, exist_ok=True)

    dur = round(audio_duration(REPO / src_rel)) if src_rel else a.duration
    est = estimate_seconds(a.task, dur * a.batch)
    basis = f"{a.task} runs"
    if not est:
        est, basis = estimate_seconds("cover", dur * a.batch), "cover runs; no history for this task"
    if est:
        print(f"Estimate: ~{fmt(est[0])} for {dur}s x {a.batch} takes (avg of {est[1]} {basis})")
    else:
        print("Estimate: no timing history yet; this run will calibrate future estimates.")

    payload = {
        "task_type": a.task,
        "prompt": a.caption,
        "lyrics": "[Instrumental]",
        "audio_duration": dur,
        "batch_size": a.batch,
        "thinking": a.thinking,
        "use_cot_caption": a.thinking,
        "use_cot_language": False,
        "use_random_seed": a.seed < 0,
        "seed": a.seed,
        "audio_format": "wav",
    }
    if a.task == "cover":
        payload.update(src_audio_path=src_rel, audio_cover_strength=a.strength,
                       cover_noise_strength=a.noise)
    if a.ref:
        payload["reference_audio_path"] = a.ref
    if a.bpm:
        payload["bpm"] = a.bpm
    if a.key:
        payload["key_scale"] = a.key
    (pdir / "logs" / f"{a.label}.json").write_text(json.dumps(payload, indent=2))
    knobs = f"strength={a.strength} noise={a.noise} " if a.task == "cover" else ""
    print(f"Submitting {a.label} ({a.task}, {dur}s): {knobs}ref={a.ref or '-'} batch={a.batch} "
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
                                a.project, a.label, a.task, dur, a.batch, round(elapsed)])
    print(f"Done in {fmt(elapsed)}: {', '.join(files)} -> {pdir.relative_to(REPO)}/renders/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
