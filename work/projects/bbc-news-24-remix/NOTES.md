# BBC News 24 theme — Jamaican remix

**Brief:** Remix the BBC News 24 theme in a Jamaican style (reggae and/or steel band).
Private use only (copyrighted source).

**Source:** https://www.youtube.com/watch?v=Ty2j4w7_s7A ("BBC news theme tune news 24", 104 s)

- `source/original.wav`: full download
- `source/trimmed.wav`: 8.0 s to 92.0 s (84 s). Silence at the start (0–8 s) and the end
  (≈100–104 s of the original) removed.

## Runs

Melody match = `work/bin/melody_check.py` score vs source (1.0 identical, 0.43 = same piece at
the wrong moment, i.e. tune lost).

| label | strength | noise | batch | style | time | melody | verdict |
|---|---|---|---|---|---|---|---|
| reggae-s045 (deleted) | 0.45 | 0 | 2 | roots reggae | 2m12s | - | lost the melody |
| reggae-s100-n00 | 1.0 | 0 | 1 | live reggae band | 1m06s | 0.075 | "nothing like the original" |
| reggae-s090-n040 | 0.9 | 0.4* | 1 | live reggae band | 1m06s | 0.069 | *noise ignored (MLX bug) |
| reggae-s090-n060 | 0.9 | 0.6* | 1 | live reggae band | 1m06s | 0.069 | *identical file to n040 |
| house-s100-n030 | 1.0 | 0.3 | 1 | mid-2010s euphoric house | 0m57s | 0.771 | (listen) |
| house-s100-n050 | 1.0 | 0.5 | 1 | mid-2010s euphoric house | 0m48s | 0.877 | (listen) |
| house-s100-n070 | 1.0 | 0.7 | 1 | mid-2010s euphoric house | 0m48s | 0.923 | (listen) |

Brief changed 2026-10-10: reggae dropped → mid-2010s euphoric house.

**MLX bug found:** on Apple Silicon the DiT runs on MLX, which ignored `cover_noise_strength`
(melody retention) entirely — every reggae run started from pure noise. Fixed in
`acestep/models/mlx/cover_noise_init.py` + plumbing; house runs used it (via PyTorch fallback
during the first, broken attempt at the fix).
