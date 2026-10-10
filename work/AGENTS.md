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
  bin/remix.sh              run one cover/remix job with ETA + elapsed feedback
  logs/server.log           API server log
  logs/timings.csv          every timed run; feeds ETA estimates
  projects/<project>/       one folder per piece of work (kebab-case name)
    NOTES.md                brief, source URL, settings tried, verdicts
    source/original.*       untouched download
    source/trimmed.wav      prepared input (48 kHz stereo WAV)
    renders/<label>_<n>.wav outputs; <label>.json = generation metadata
    logs/<label>.log        per-run client log
```

## Tools

Installed with Homebrew: `ffmpeg`, `yt-dlp`, `deno` (yt-dlp's YouTube JS runtime).
Install anything else needed with `brew install`, not pip/system packages.

## Process

1. **Create project**: `mkdir -p work/projects/<name>/{source,renders,logs}` and a `NOTES.md`
   with the brief and source URL.
2. **Fetch**: `yt-dlp -x --audio-format wav -o "work/projects/<name>/source/original.%(ext)s" <URL>`
3. **Prepare**: find silence with
   `ffmpeg -i original.wav -af silencedetect=n=-45dB:d=1 -f null -`, then trim/convert:
   `ffmpeg -ss <start> -t <len> -i original.wav -ar 48000 -ac 2 trimmed.wav`
4. **Server**: `work/bin/server.sh start` — loads models up front and reports load time.
5. **Generate**: `work/bin/remix.sh <name> <label> <strength> <batch> "<caption>"`
   - Use labels that describe the setting, e.g. `reggae-s045`, `steelpan-s050`.
   - Cover strength: 0.3–0.5 big genre change, 0.5–0.7 moderate, 0.7–0.9 subtle.
   - Batch 2 per idea; pick a winner, then refine strength/caption.
6. **Record** what was tried and the verdict in the project's `NOTES.md`.
7. **Stop** the server when done (`work/bin/server.sh stop`) — it holds a lot of memory.

## Time feedback (required)

Always tell the user how long something will take **before** starting it, and report actual
time when it finishes.

- `remix.sh` prints an estimate from `logs/timings.csv` (avg seconds per generated
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
- `.claude/skills/acestep/scripts/acestep.sh` is not executable; call it with `bash`.
- Source material is often copyrighted (e.g. the BBC News theme): keep remixes private.
