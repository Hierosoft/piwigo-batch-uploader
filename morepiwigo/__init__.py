"""
morepiwigo — batch upload helpers and shared utilities for Piwigo.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit(
        "Pillow is required for rotation. Install with: pip install Pillow"
    ) from exc

# Columns that should NOT appear in the photo description
# (title / album name / album description source)
EXCLUDE_FROM_DESC = {"Description", "Carton", "Location"}

# Preferred order for fields in the photo description
DESC_ORDER = [
    "Date",
    "#",
    "Code",
    "Comment",
    "Frame",
    "Brand",
    "Scanned",
    "File",
    "Date Film",
    "Reel",
    "Serial",
    "Path",
]


def decide_rotation(description: str) -> Optional[str]:
    """
    Return 'left', 'right', '180', or None based on Description text.

    Precedence (case-insensitive):
      1. "rotate right"  → 90° clockwise
      2. "rotate 180"    → 180°
      3. "(portrait"     → 90° counter-clockwise (left)
      4. otherwise       → no rotation
    """
    text = (description or "").lower()
    if "rotate right" in text:
        return "right"
    if "rotate 180" in text:
        return "180"
    if "(portrait" in text:
        return "left"
    return None


def make_rotated_temp(src_path: Path, direction: str) -> Path:
    """
    Open *src_path*, rotate, write to a NamedTemporaryFile, return its Path.

    Caller must delete the temp file when done.
    The original file is never modified.
    """
    img = Image.open(src_path)
    if direction == "left":
        img = img.transpose(Image.Transpose.ROTATE_90)  # 90° CCW
    elif direction == "right":
        img = img.transpose(Image.Transpose.ROTATE_270)  # 90° CW
    elif direction == "180":
        img = img.transpose(Image.Transpose.ROTATE_180)
    else:
        raise ValueError(f"Unknown rotation direction: {direction}")

    fmt = (img.format or src_path.suffix.lstrip(".").upper() or "JPEG")
    if fmt.upper() in ("JPG",):
        fmt = "JPEG"

    suffix = src_path.suffix or ".jpg"
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix="piwigo_rot_")
    os.close(fd)
    tmp_path = Path(tmp_name)

    save_kwargs = {}
    if fmt.upper() == "JPEG":
        save_kwargs["quality"] = 95
        save_kwargs["optimize"] = True
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

    img.save(tmp_path, format=fmt, **save_kwargs)
    img.close()
    return tmp_path


def build_photo_description(row: dict) -> str:
    """
    Turn remaining non-blank columns into a multi-line description
    (includes Path; excludes Description / Carton / Location).
    """
    lines = []
    seen = set()
    for col in DESC_ORDER + [c for c in row if c not in DESC_ORDER]:
        if col in EXCLUDE_FROM_DESC or col in seen:
            continue
        seen.add(col)
        val = (row.get(col) or "").strip()
        if val:
            lines.append(f"{col}: {val}")
    return "\n".join(lines)


__all__ = [
    "EXCLUDE_FROM_DESC",
    "DESC_ORDER",
    "decide_rotation",
    "make_rotated_temp",
    "build_photo_description",
]
