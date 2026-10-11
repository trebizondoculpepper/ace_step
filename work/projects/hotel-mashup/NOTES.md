# hotel-mashup

Experimental mash-up, **not for release** (2026-10-11): verses from Zana – "Vlak", choruses from
Eagles – "Hotel California", real vocals (Demucs stems) over newly generated music.

## Sources

| file | track | URL | measured |
|---|---|---|---|
| `vlak_original.wav` | Zana – Vlak, 4:18 | https://www.youtube.com/watch?v=xm5BRAB8Voc | 66.3 BPM (beat 0.906 s), B minor/D major; verses F#–Bm–G–D, refrain Bm–D loop |
| `hotel-california_original.wav` | Eagles – Hotel California (2013 Remaster), 6:31 | https://www.youtube.com/watch?v=BciS5krYL80 | 73.6 BPM (beat 0.8155 s), B minor; verse 0:52.4, chorus 1 1:44.6–2:10.7, chorus 2 3:02.8–3:28.9 |

Same key (B minor) — no pitch shift. Vlak stretched ×1.111 (atempo, pitch kept).
Sections found by librosa beat tracking + chord-per-bar matching (scratch script; run with
`uv run --no-project --with librosa`, keeps the ACE-Step venv untouched).

## Pipeline

1. Demucs htdemucs_6s on both (46 s).
2. `python3 work/projects/hotel-mashup/build_guide.py` — identical cuts to `source/guide.wav`
   (instrumental stems) and `source/vocals.wav` (vocal stems): intro (HC) – V1 (Vlak) – C1 (HC) –
   V2 (Vlak) – C2 (HC) – V3 (Vlak) – C1 (HC) + 2.5 s fade = 3:02.5.
3. Cover the guide (strength 1.0, seed 7): new band, same chords + timing.
4. Mix: band −20 LUFS, vocals compressed −19 LUFS, master −14 LUFS / −1 dBTP.

Timing check: onset cross-correlation guide vs render = 0 lag at start/middle/end (±23 ms).

| label | noise | time | harmony vs guide | output |
|---|---|---|---|---|
| band-n036 | 0.36 (3 steps) | 1m21s | 0.784 | `renders/mashup-n036.wav` (listen) |
| band-n025 | 0.25 (4 steps) | 1m24s | 0.680 | `renders/mashup-n025.wav` (listen) looser band |

Caption: 1980s new wave rock band, chorus guitars, 12-string strumming, synth pads, melodic bass,
punchy live drums, atmospheric reverb.
