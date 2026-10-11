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

## Lyric swap (2026-10-11)

Initial brief: re-sing each song's words on the other's melody. Wrote the seven-section lyric
sheet privately in `source/swap_lyrics.txt`. Generator parses as Python 3.9; a mocked submission
and the actual saved JSON requests confirmed `lyrics` and `vocal_language=unknown` reach the API.
Full-mix cover: strength 1.0, seed 7, batch 1, thinking off. Server startups took 25–35 s;
stopped after every batch. An immediate stop/start raced shutdown once; retried successfully.

| render | noise | elapsed | chroma similarity vs full swap guide | local chorus check |
|---|---|---|---|---|
| `swap-n036_1.wav` | .36 | 81 s | .733 | Original HC words remain in Serbian slot; other slot inconclusive |
| `swap-n050_1.wav` | .50 | 72 s | .814 | Same failure, better harmony preservation |
| `swap-n025_1.wav` | .25 | 85 s | .645 | Original Vlak words remain in English slot |
| `swap-instr-n036_1.wav` | .36 | 93 s | .582 | English chorus recognized in Vlak slot; Serbian slot unconfirmed |

Reference self similarity 1.000, shifted-source baseline .243. Chroma measures full-mix harmony,
not vocal-melody fidelity. All transcription used cached mlx-whisper locally, offline.
User-requested `swap-n050_1.mp3`: 320 kbps, 175.8 s, 7.03 MB; conversion 1.36 s.

User then requested simultaneous crossed vocals. Tried separate 26 s chorus covers with wordless
pitch guides (5.65 s preparation), strength .75 / noise .36 / seed 7: 46 s each. English lyrics
were recognized; Serbian lyrics were not. Strength .4 / noise 0 also failed the Serbian check
(40 s). Approximate local pitch-contour retuning of the original voices produced a preliminary
`crossed-overlap_master.mp3` (two crossed parts overlap at 2:04–2:30). This is processed and
approximate, not a verified exact melodic swap. Chorus median pitch errors were 128/103 cents.

## Hotel California band + Vlak vocals (latest direction)

User changed direction: **all backing from Hotel California, all sung words from Vlak**, using
Vlak's real vocal stem and shifting notes only where harmony clashes. No ACE-Step vocals here.

`build_hotel_vlak.py` uses HC drums/bass/guitar/other/piano only, and Vlak vocals only. Offline
transcription revealed Vlak's first verse starts at 0:00, so the complete first verse is used.
Time-stretch each vocal section without changing pitch to match its HC backing section.
Final duration 182.61 s (3:03); the first chorus repeats near the end, followed by instrumental
outro. The three-minute arrangement includes both verses and repeated choruses, rather than the
entire 4:18 original recording.

| output time | HC backing source | Vlak vocal source |
|---|---|---|
| 0:00–0:13 | 39.36–52.41 | instrumental |
| 0:13–1:05 | 52.41–104.56 | 0.00–59.07, full first verse |
| 1:05–1:31 | 104.56–130.66 | 59.07–87.75, chorus |
| 1:31–1:57 | 130.66–156.74 | 87.75–117.31, second verse |
| 1:57–2:23 | 182.83–208.91 | 117.31–145.98, chorus |
| 2:23–2:50 | 104.56–130.66 | 59.07–87.75, chorus repeat |
| 2:50–3:03 | 208.91–221.96 | instrumental |

`harmony_pitch.py`: pYIN vocal pitches; only confident notes held >=180 ms may move onto a chord
tone, at most two semitones. Short passing notes stay intact. Backing chord schedule assumes
HC's evenly spaced verse/chorus progression; it is not an automatic harmonic transcription.
Changed 8.0% / 12.3% of reliable voiced frames in the verses; no chorus corrections triggered.
Overlapping phase-vocoder windows preserve words and duration but may introduce artifacts.
This preserves Vlak's melody broadly; it does not force every note onto HC's vocal melody.

Outputs to listen to:
- `renders/hotel-band-vlak-vocals_master.mp3` — selective harmony correction, 320 kbps.
- `renders/hotel-band-vlak-vocals_unshifted.mp3` — same arrangement, no pitch correction, 320 kbps.
- Matching 48 kHz/24-bit WAV files for both.

Assembly/correction/mastering first pass: 24.43 s. Measured two-pass mastering added afterward
because one-pass loudnorm missed the target. Target -14 LUFS / <=-1 dBTP.
Final chorus transcription recognized Vlak's words and no HC words. Six focused harmony tests,
three layout tests, Python 3.9 parsing, and no-shift waveform reconstruction checks passed.
Human listening remains necessary for phrasing, vocal balance, and pitch-shift artifacts.
All audio, lyric sheets, transcripts and the handoff containing lyric excerpts remain local.

Final mastering verification: -14.23 LUFS / -1.51 dBTP (WAV). Measured normalization and
oversampled peak limiting added about 43 s. Nine focused unit tests passed in total.
