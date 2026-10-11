# dune-credits

Close, goofier chiptune cover of Toto – "Take My Hand" (Dune 1984 closing titles), for Idea
Grabber (2026-10-10). Same melody, recognisably close. **Risk:** a cover of a copyrighted
composition; shipping it in a public game needs a licence (user decides).

Source: https://www.youtube.com/watch?v=6GPfuyrEK2U (TOTO official, 2:40). `source/trimmed.wav`
= 0:00–2:32 (last 8 s near-silent), 48 kHz. Measured ~89 BPM, C major, instrumental.

Caption: goofy chiptune cover, square-wave + toy synth brass melody, triangle bass, toy drums,
kazoo-like lead, slide-whistle flourishes. Cover task, strength 1.0, seed 7.

| label | noise | time | melody vs source | verdict |
|---|---|---|---|---|
| tmh-chip-s100-n070 | 0.7 (1 step) | 1m33s | 0.942 | (listen) closest |
| tmh-chip-s100-n050 | 0.5 (2 steps) | 1m45s | 0.917 | (listen) more room to be goofy |

Parked (user, 2026-10-10): deliver later, when the Idea Grabber credit screen is built.

## Round 2 — user: first covers "a bit too close"; try more chiptune and Jimmy Smith organ jazz

Strength 1.0, seed 7, looser noise (0.36 = 3 steps, 0.25 = 4 steps).

| label | style | noise | time | melody vs source | verdict |
|---|---|---|---|---|---|
| tmh-nes-n036 | pure NES chiptune | 0.36 | 1m10s | 0.882 | (listen) |
| tmh-nes-n025 | pure NES chiptune | 0.25 | 1m34s | 0.832 | (listen) loosest chip |
| tmh-organ-n036 | Jimmy Smith organ trio | 0.36 | 1m21s | 0.878 | (listen) |
| tmh-organ-n025 | Jimmy Smith organ trio | 0.25 | 1m55s | 0.814 | (listen) loosest |

## Round 3 — user: round 2 "all way too close"; keep melody, allow re-arrangement

Melody-only source `source/melody_og.wav` = Demucs other + guitar (other matches the mix 0.90).
Cover from it at noise 0, strength 0.8 / 0.6 → melody **lost** (0.07–0.09 ≈ unrelated −0.10).
Noise 0 doesn't carry notes, same as the BBC remix. Proposed next (not run): melody-only source at
strength 1.0, noise 0.25–0.36, so only the tune carries over; else a pitch-tracked melody line.
