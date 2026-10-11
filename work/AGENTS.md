# work/ — personal music workspace (not part of the repo)

`work/` is versioned on our fork (`origin` = trebizondoculpepper/ace_step, `upstream` =
ace-step/ACE-Step-1.5; commit to `main`, pull updates with `git pull upstream main`).
Only scripts, docs, notes and `timings.csv` are committed; audio and run logs are ignored by
`work/.gitignore`. Repo-wide rules in `../AGENTS.md` (contribution policy) do not apply here.

## Layout

```
work/
  AGENTS.md                 this file
  bin/server.sh             start|status|stop the local ACE-Step API server
  bin/generate.py           one generation job (text2music or cover) with ETA + elapsed
  bin/melody_check.py       score how closely renders follow the source melody
  bin/describe_audio.py     section timeline (loudness, brightness, bass, onsets) + tempo/key
  bin/drone_score.py        screen renders: drone-like? and originality vs references
  bin/loop.py               seamless loop + extend to N minutes + loudness to target LUFS
  logs/server.log           API server log
  logs/timings.csv          every timed run; feeds ETA estimates
  projects/<project>/       one folder per piece of work (kebab-case name)
    NOTES.md                brief, source URL, settings tried, verdicts
    source/original.*       untouched download
    source/trimmed.wav      prepared input (48 kHz stereo WAV)
    renders/<label>_<n>.wav outputs
    logs/<label>.json       exact request payload for that label
```

## Tools

Installed with Homebrew: `ffmpeg`, `yt-dlp`, `deno` (yt-dlp's YouTube JS runtime), `jq`.
Python tools run with the repo venv (`.venv/bin/python`, has numpy); `generate.py` is stdlib-only
and runs on system `python3` (3.9). Install anything else with `brew install`.
- `music.youtube.com` URLs can 403 in yt-dlp; use the `www.youtube.com/watch?v=` form.

## Process

1. **Create project**: `mkdir -p work/projects/<name>/{source,renders,logs}` and a `NOTES.md`
   with the brief and source URL.
2. **Fetch**: `yt-dlp -x --audio-format wav -o "work/projects/<name>/source/original.%(ext)s" <URL>`
3. **Prepare**: find silence with
   `ffmpeg -i original.wav -af silencedetect=n=-45dB:d=1 -f null -`, then trim/convert:
   `ffmpeg -ss <start> -t <len> -i original.wav -ar 48000 -ac 2 trimmed.wav`
4. **Server**: `work/bin/server.sh start` — loads models up front and reports load time.
5. **Generate**: `python3 work/bin/generate.py <name> <label> "<caption>" --task cover --strength S --noise N --batch B [--seed 42]`
   - Labels encode the settings, e.g. `reggae-s090-n040` (strength 0.90, noise 0.40).
   - To compare settings, use batch 1 and a fixed `--seed` so only the knob changes.
   - Then batch 2+ with random seeds on the winning setting.

### Keeping the original melody (same tune, new instruments)

Learned on bbc-news-24-remix: strength 0.45 / noise 0 / thinking on lost the tune entirely.
- `--strength` (`audio_cover_strength`) = fraction of denoising steps conditioned on the
  source structure. Keep 0.8–1.0 for "same tune"; the 0.3–0.5 genre-change advice in the
  docs trades away the melody.
- `--noise` (`cover_noise_strength`, the UI's "Melody Retention") = how much of the source
  audio the denoiser starts from. 0 = pure noise. 0.3–0.6 keeps melody; too high keeps
  the original instruments too.
  Before our fix (2026-10-10) the MLX DiT backend silently ignored this setting; if renders
  with different `--noise` come out identical, check `Cover mode` appears in `logs/server.log`.
- `--noise` is **quantised** to the turbo model's 8-step schedule (shift 3:
  1.0, .955, .9, .833, .75, .643, .5, .3). It snaps 1−noise to the nearest step, so the only
  distinct levels are ≈0.25 (4 steps left), ≈0.36 (3), 0.45–0.6 (2, identical output), ≥0.65
  (1 step: very close to the source). Don't sweep values that land on the same step.
- Leave `--thinking` off: the LM rewrites the caption and metadata and drifts.
- Name the lead instruments that should carry the melody in the caption.
- Not yet tried: flow-edit morph (`flow_edit_morph`, Gradio UI / Python only, not exposed
  by the HTTP API) — designed for "keep the source, change the style".
6. **Score** each render: `.venv/bin/python work/bin/melody_check.py <source> <renders...>`
   (1.0 = identical tune, ~0.43 = tune lost). Report scores with the listening request.
7. **Record** what was tried and the verdict in the project's `NOTES.md`.
8. **Stop the server at the end of every batch** (`work/bin/server.sh stop`), unprompted —
   user preference (2026-10-10). It holds a lot of memory and restarts in ~25 s.

## Time feedback (required)

Always tell the user how long something will take **before** starting it, and report actual
time when it finishes.

- `generate.py` prints an estimate from `logs/timings.csv` (avg seconds per generated
  audio-second × duration × batch) and an elapsed tick every 30 s.
- `server.sh start` prints load progress; model load is ~30 s with the 1.7B LM (2026-10-10).
- Run anything over ~1 min in the background and check in with the user, rather than
  blocking silently.
- If a step will download something, say so and estimate size/time first.

## Gotchas (learned the hard way)

- **Don't let the server auto-pick the LM.** On this 25 GB Mac it picks
  `acestep-5Hz-lm-4B`, which is not installed and triggers a multi-GB download at
  <1 MB/s (≈1–2 h). `server.sh` pins `acestep-5Hz-lm-1.7B` and sets `HF_HUB_OFFLINE=1`.
  Installed LMs: 0.6B, 1.7B. DiT: `acestep-v15-turbo`.
- **The skill's default config points at the hosted `api.acemusic.ai`.**
  `.claude/skills/acestep/scripts/config.json` is now set to `http://127.0.0.1:8001`,
  `api_mode: native`, `audio_format: wav`. That file is gitignored, so on a fresh clone run
  `bash .claude/skills/acestep/scripts/acestep.sh config --set api_url http://127.0.0.1:8001`
  (and `api_mode native`, `generation.audio_format wav`).
- **The API rejects absolute audio paths** (outside the system temp dir). Pass paths relative
  to the repo root, e.g. `work/projects/<name>/source/trimmed.wav`.
- `start_api_server_macos.sh` retries in offline mode when killed. Use `server.sh stop`,
  not `pkill` on the wrapper.
- The skill script `acestep.sh` can't set `cover_noise_strength` and forces `thinking`; use
  `generate.py` instead. System `python3` is 3.9 (keep `from __future__ import annotations`).
- The shell is zsh: unquoted `$VAR` does NOT word-split. Never store a command or arg list in
  a variable (`G="python3 x.py"; $G ...` fails with exit 127); write commands out in full.
- Source material is often copyrighted (e.g. the BBC News theme): keep remixes private.

## Drone beds for YouTube (project: drones)

Goal: original background drones inspired by references the user likes.
1. **Reference**: download, find the drone section with `describe_audio.py`, cut it to
   `source/<name>_<section>.wav` (48 kHz). Run ACE-Step `full_analysis_only` for a caption,
   but verify it against the measurements (it called a Gong drone "epic orchestral").
2. **Style card** in `NOTES.md`: timbre, register, movement, tonal centre, space.
3. **Generate**: `generate.py --task text2music --duration 140 --ref <reference clip>`. The
   reference is a light, time-averaged timbre hint (no melody/rhythm). Never use `--task cover`
   on references for publishable work: it reproduces their notes (Content ID risk).
4. **Screen**: `drone_score.py --ref <refs...> <renders...>` — want DRONE and no COPY? flag.
5. **Loop/extend**: `loop.py <render> [--minutes M] [--lufs -18]` → `_loop.wav`, `_<M>min.wav`.
ACE-Step is MIT; its README asks users to verify originality and disclose AI involvement.
