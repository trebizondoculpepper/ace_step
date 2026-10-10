# drones

Collecting and describing drone / ambient reference material. Private use only.

## Sources

| file | track | URL | notes |
|---|---|---|---|
| `traveller_original.wav` | Talvin Singh – Traveller (OK, 1998), 11:17 | https://music.youtube.com/watch?v=yNOOdnodof8 | music.youtube URL 403s; use www.youtube.com |
| `traveller_ambient_0415-0800.wav` | ambient section 4:15–8:00 (48 kHz) | | |
| `magick-mother_original.wav` / `_48k.wav` | Gong – Magick Mother Invocation (You, 1974; 2006 reissue), 1:10 | https://music.youtube.com/watch?v=r5l_Ffs0BdU | |
| `pelmonauts_original.wav` | Ed Wynne & Gre Vanderloo – Pelmonauts (Tumbling Through the Floativerse, 2022), 6:38 | https://music.youtube.com/watch?v=xWeOFuqsonQ | |
| `pelmonauts_drone_0000-0140.wav` | drone intro 0:00–1:40 (48 kHz) | | |
| `limbo-prayer_original.wav` / `_48k` / `_ext144` | Prayer – Limbo OST (Martin Stig Andersen; upload by "Soundtracks of Time"), 1:39 | https://music.youtube.com/watch?v=dXB4SXQxAT4 | whole track is drone |

## Traveller — measured (work/bin/describe_audio.py)

- 3:00–4:00 loud groove (−11 dBFS, ~80% of energy below 250 Hz, 4.5–6 onsets/s).
- Drop at 4:00–4:10: −10 → −22 dBFS, bass share collapses.
- **4:15–8:00 ambient:** −23 to −25 dBFS, bass only 3–15%, mids 85–97%, ~0.5 onsets/s,
  centroid ~1.5–2 kHz. Pitch centre B♭/F (+F#); key fit B♭ minor.
- 8:00–10:30 swells back to −12/−15 dBFS but still bass-free; 10:30+ bass returns, outro.

ACE-Step 1.7B LM analysis of 4:15–8:00 (43 s): "emotive, virtuosic solo on breathy ney flute,
free-form improvisation, melancholic, spacious, microtonal ornamentation, builds to trills and
runs, natural reverb of a large space, haunting, introspective". 79 BPM, E♭ minor, "Experimental
world". Plausible but unverified (instrument ID uncertain).

## Magick Mother Invocation — measured

- Quiet and dark throughout: −25 to −32 dBFS after a −17 dBFS opening 10 s; centroid ~0.9–1.4
  kHz; essentially no energy above 4 kHz; 0.2–0.6 onsets/s (no rhythm).
- Static pitch centre F#/G (+F, D) for the whole piece — a drone. Key fit F# minor (weak, r=0.57).

ACE-Step analysis (24 s): "grand, epic orchestral, heroic theme, brass fanfares, timpani,
cymbal crashes, rapid string ostinatos". **Contradicted by the measurements** (no transients, no
highs, no dynamics) — treat ACE-Step's captioner as unreliable for drone material.

## Pelmonauts — measured

- 0:00–1:40 drone intro: D/A open-fifth bed, bass-heavy (50–80% < 250 Hz), 0.25–0.75 onsets/s,
  −17 to −20 dBFS. 1:40–5:40 a groove builds (to ~4 onsets/s, −11 dBFS). 5:40–end quiet drone
  outro (−25 to −30 dBFS). Key fit D minor (r=0.82).

ACE-Step analysis: "epic cinematic orchestral… brass fanfares, thunderous drums", G minor, 125 BPM.
**Wrong again** — 2 of 3 drone refs captioned "epic orchestral". Write style cards from measurements.

## Limbo – Prayer — measured

- Uniform throughout: −28 dBFS, centroid ~700 Hz, ~98% mids (no bass, no highs), 0.1–0.6
  onsets/s. G/D fifth with B♭/A♭ colour; key fit G minor (r=0.82). Murky, muffled, static.

## Style cards

- **Traveller (4:15–8:00):** airy, mid-register (centroid ~1.8 kHz, bass ≤15%), breathy wind lead
  in free improvised phrases over a quiet bed, B♭/F centre, big reverb, ~0.5 onsets/s.
- **Magick Mother:** dark, quiet static drone on F#/G, nothing above 4 kHz, no rhythm.
- **Pelmonauts (0:00–1:40):** warm, bass-heavy D–A fifth drone, slow and steady.

## Generation runs (text2music, 140 s, batch 2)

| label | ref | time | onsets/s | dyn dB | bass % | bright | max sim to a ref | notes |
|---|---|---|---|---|---|---|---|---|
| trav-ref | Traveller | 1m39s | 0.66 / 0.96 | 8.2 / 6.7 | 84 / 81 | 562 / 494 | 0.23 | dark, steady; loops made |
| trav-noref | – | 1m24s | 3.34 / 0.61 | 5.9 / 8.7 | 90 / 58 | 1269 / 723 | 0.46 (Pelmonauts) | _1 busy |
| trav-airy-ref | Traveller | 1m45s | 1.36 / 1.12 | 6.3 / 9.5 | 81 / 57 | 467 / 688 | 0.17 | "no bass" ignored |
| mm-ref | Magick Mother | 1m42s | 0.68 / 0.86 | 4.1 / 5.5 | 67 / 79 | 708 / 736 | 0.20 | both DRONE; user disliked (too far from original), deleted |
| pel-ref | Pelmonauts | 1m36s | 1.29 / 1.18 | 10.0 / 3.9 | 83 / 87 | 800 / 738 | 0.40 | slightly busy; user disliked (too far from original), deleted |

### Cover runs on extended refs (source looped to 144 s, cover task, batch 2)

| label | strength | noise | time | onsets/s | bass % | bright | sim to own ref | verdict |
|---|---|---|---|---|---|---|---|---|
| mm-cov-s070-n030 | 0.7 | 0.3 | 2m18s | 0.49 / 0.47 | 61 / 58 | 909 / 854 | 0.76 | **user: "much better — sounds like a synthesized version of the acoustic original"** |
| pel-cov-s070-n030 | 0.7 | 0.3 | 2m21s | 1.47 / 1.77 | 74 / 78 | 1531 / 1424 | 0.71 | (listen) |
| mm-cov-s050-n015 | 0.5 | 0.15 | 2m34s | 0.35 / 0.27 | 75 / 72 | 830 / 785 | 0.64 / 0.66 | (listen) looser, bassier |
| pel-cov-s050-n015 | 0.5 | 0.15 | 2m33s | 1.29 / 1.30 | 87 / 87 | 1284 / 1560 | 0.60 | (listen) looser, bassier |

Similarity ~0.7 on a drone mostly reflects the same held pitches (F#/G, D/A), not copied audio;
Content ID fingerprints the recording, and these are regenerated. Still the closest we go.
Prepare short refs for cover with `loop.py <clip> --trim 2 --xfade 4 --minutes 2.4 --fade 0.5`.

Learned: reference keeps takes calmer and tonally closer while staying original (max 0.23).
Captions with "no bass" don't remove bass — ACE-Step ignores negations; fix tone in post (EQ)
or describe only what should be present. All takes are darker than the Traveller section.

Only `*_loop.wav` files are kept in renders/ (118 s, −18 LUFS); originals deleted 2026-10-10.
Extend a loop: `.venv/bin/python work/bin/loop.py renders/<name>_loop.wav --minutes N`.
