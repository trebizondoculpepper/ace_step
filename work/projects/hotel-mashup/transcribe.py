"""Transcribe a vocal stem with mlx-whisper; print timestamped segments (offset added)."""
import sys
import mlx_whisper

path, lang, offset = sys.argv[1], sys.argv[2], float(sys.argv[3])
r = mlx_whisper.transcribe(path, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                           language=lang, condition_on_previous_text=False)
for s in r["segments"]:
    t = s["start"] + offset
    print(f"{int(t // 60)}:{t % 60:05.2f}  {s['text'].strip()}")
