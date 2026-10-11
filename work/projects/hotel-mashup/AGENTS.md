# Hotel mash-up render numbering

Number every audio render sequentially as `0001_<description>.<format>` and upward.
MP3/WAV versions of the same mix share a number. Keep existing numbers stable, and create
new versions with higher numbers. Include test renders and vocal-only intermediate renders.

The project builders number their completed outputs automatically. After using the shared
`work/bin/generate.py`, run `python3 work/projects/hotel-mashup/number_renders.py` before linking
outputs or recording their filenames. Convert numbered WAVs to MP3 with the same numbered stem.
Use `number_renders.find_render()` when a script needs an older render by descriptive filename.

All audio and lyrics stay private/local. Keep old versions; do not overwrite a numbered render.
