#!/usr/bin/env python3
"""Generate the Idea Grabber chiptune bank: one text2music job (batch 2) per brief.

  python3 work/projects/idea-grabber-bgm/generate_bank.py [--only bgm-01,bgm-02] [--duration 32]

Skips briefs whose renders already exist. Renders: renders/<id>_1.wav, <id>_2.wav.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE = ("goofy joyful chiptune video game music, retro game console sound chip, instrumental, "
         "catchy memorable melody, starts immediately, clean full-quality mix, tidy ending")


def main() -> int:
    """Run generate.py for each pending brief."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--duration", type=int, default=32)
    a = ap.parse_args()
    briefs = json.loads((HERE / "briefs.json").read_text())
    wanted = [w for w in a.only.split(",") if w]
    for b in briefs:
        if wanted and not any(b["id"].startswith(w) for w in wanted):
            continue
        if (HERE / "renders" / f"{b['id']}_2.wav").exists():
            continue
        print(f"=== {b['id']}", flush=True)
        subprocess.run([sys.executable, str(HERE.parents[1] / "bin" / "generate.py"),
                        HERE.name, b["id"], f"{b['caption']}, {STYLE}", "--task", "text2music",
                        "--duration", str(a.duration), "--batch", "2", "--seed", "11",
                        "--bpm", str(b["bpm"]), "--key", b["key"].replace("♭", "b")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
