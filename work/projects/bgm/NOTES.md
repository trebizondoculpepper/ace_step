# bgm

Generic background music for YouTube productions. First brief (2026-10-10): **high-energy
intros** — full-length instrumental versions (no vocals) of 1960s tracks, keeping the rough
1960s studio feel. Private use / user decides on publishing (see risk note).

## Sources

| file | track | URL | measured |
|---|---|---|---|
| `velvet-opera-intro_*` | Elmer Gantry's Velvet Opera – Intro (album, 1968), 1:01 | https://www.youtube.com/watch?v=UwXH_kL9kys (album playlist OLAK5uy_mi889afBru50U3qzRclOnTIteGSEEiDcY, track 1) | −9 to −11 dBFS throughout, ~4 onsets/s, 63–74% bass, D minor (r=0.89) |
| `journey-centre-mind_*` | The Amboy Dukes – Journey to the Centre of the Mind (1968), 3:33 | https://music.youtube.com/watch?v=FXaGZ4_dGgY | −14 to −19 dBFS sections, 1–4 onsets/s, A-centred |

## Approach

Cover task, lyrics `[Instrumental]`, caption describes a raw 1968 studio band with an instrument
carrying the vocal line. Compare per song (seed 7, batch 1):
- A `s100-n000`: full structure, fresh audio (original vocals can't leak).
- B `s090-n025`: starts partly from the original audio — closer vintage sound, possible bleed.

**Risk:** these are instrumental versions of copyrighted songs. Even with new audio, the
composition (melody, chords) is the original's; publishers can claim covers on YouTube.

## Second brief (user): stem it, keep guitar + bass + drums, close re-render

First cover attempts (full mix, s100-n000 / s090-n025) — user: "horrible", deleted; journey dropped.
Demucs `htdemucs_6s` (uv tool, 12 s on MPS): stems in `logs/demucs/`. Vocals −20.8 dB (big),
other/piano ≈ silent. `source/velvet-opera-intro_gbd.wav` = guitar+bass+drums, −3 dB (sum clipped).

## Runs

| label | strength | noise | time | melody vs source | verdict |
|---|---|---|---|---|---|
| intro-gbd-s100-n050 | 1.0 | 0.5 (t=0.5, 2 steps) | 0m51s | 0.749 vs gbd | (listen) |
| intro-gbd-s100-n060 | 1.0 | 0.6 → same step as 0.5 | 0m48s | identical file, deleted | |
| intro-gbd-s100-n070 | 1.0 | 0.7 (t=0.3, 1 step) | 0m57s | 0.854 vs gbd | (listen) closest |

## Vintage treatment (post-processing per stem: `work/bin/stem_fx.py`)

User: re-render "way too clean"; no tape hiss; wanted per-instrument fuzz/echo. Demucs on each
re-render → guitar (two-stage fuzz + slapback), bass (grit), drums (medium: short echo; heavy:
1.2 s convolution room reverb — user found heavy drum echo too much). Guitar re-levelled up ~7 dB
to the original balance. Outputs `*_fx-medium.wav`, `*_fx-heavy.wav`. **User: "good enough".**

Considered/not pursued: original as reference_audio; per-stem model re-render (started, cancelled);
base-model lego (download cancelled); 1960s LoKr training.
