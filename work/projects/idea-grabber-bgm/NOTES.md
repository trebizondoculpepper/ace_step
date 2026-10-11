# idea-grabber-bgm

Soundtrack bank for the Idea Grabber browser game (repo `/Users/sal/PycharmProjects/idea_grabber`).
Brief: `idea_grabber/docs/prompts/music-generation.md`; delivery proposal:
`idea_grabber/doc/prompts/music-delivery.md` (2026-10-10). 40 goofy chiptune snippets, 20–40 s,
each an **original-melody pastiche** of one 1980s–90s game theme (user confirmed: original
pastiche melody, not the theme itself).

## Pipeline

1. `briefs.json` — id, game/theme, target bpm + key, genre, musical caption (describes the theme's
   groove/harmony/instrumentation; never names the game, so nothing to imitate note-for-note).
2. `python3 work/projects/idea-grabber-bgm/generate_bank.py [--only bgm-01,...]` — text2music,
   32 s, batch 2, seed 11, bpm/key metadata. ~52 s per brief (fixed overhead dominates).
3. `.venv/bin/python work/projects/idea-grabber-bgm/deliver.py` — pick take (tempo match, then
   length), trim trailing silence + 0.5 s fade, two-pass loudnorm −16 LUFS / −1.5 dBTP,
   write WAV master (24-bit) + MP3 192k CBR + `manifest.json` (with `genre`, as user asked).

Observations: ACE-Step obeys the bpm hint (±1–2 BPM measured); takes start with music
immediately and end naturally with 2–5 s of silence, which deliver.py trims. Key hint is
looser (bgm-09 asked E minor, measured ~C/G).

## Runs

(see `logs/bank.log` and `work/logs/timings.csv`)
Generated 2026-10-10: 40 briefs in ~35 min; deliver.py 2 min. All 26–32 s, −16.0 to −16.4 LUFS,
TP ≤ −1.0 dBTP. bpm null for bgm-12, bgm-28 (measure ~161 vs 120: shuffle/4:3 feel).
User approved the first takes ("these are all fine… ship it").
