"""Number local audio renders chronologically, keeping format variants together.

Run after a generation batch: python3 work/projects/hotel-mashup/number_renders.py.
Existing numbers stay fixed; new renders receive numbers above the current maximum.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO_SUFFIXES = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
NUMBERED = re.compile(r"^(\d{4,})_(.+)$")


def number_renders(directory: Path) -> dict[str, str]:
    """Prefix unnumbered audio groups by age; return old-to-new filename mappings."""
    groups: dict[str, list[Path]] = {}
    maximum = 0
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        match = NUMBERED.match(path.stem)
        if match:
            maximum = max(maximum, int(match.group(1)))
        else:
            groups.setdefault(path.stem, []).append(path)
    ordered = sorted(groups.values(), key=lambda files: (min(p.stat().st_mtime_ns for p in files),
                                                         files[0].stem))
    mapping = {}
    for index, files in enumerate(ordered, maximum + 1):
        for path in files:
            target = path.with_name(f"{index:04d}_{path.name}")
            if target.exists():
                raise FileExistsError(target)
            path.rename(target)
            mapping[path.name] = target.name
    return mapping


def find_render(name: str) -> Path:
    """Find a freshly written render or the latest numbered version of that filename."""
    directory = HERE / "renders"
    direct = directory / name
    if direct.exists():
        return direct
    matches = [p for p in directory.glob(f"*_{name}") if NUMBERED.match(p.stem)]
    if not matches:
        raise FileNotFoundError(direct)
    return max(matches, key=lambda p: int(NUMBERED.match(p.stem).group(1)))


def main() -> None:
    """Number project renders and print the resulting names."""
    for old, new in number_renders(HERE / "renders").items():
        print(f"{old} -> {new}")


if __name__ == "__main__":
    main()
