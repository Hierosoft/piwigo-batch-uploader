"""
CLI entry logic for the Piwigo batch uploader.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

from morepiwigo import (
    build_photo_description,
    decide_rotation,
    make_rotated_temp,
)
from morepiwigo.piwigoclient import PiwigoClient


def load_csv_columns(path: str) -> OrderedDict[str, List[str]]:
    """
    Load a CSV into an OrderedDict of lists.

    Keys are the header values. List index 0 is the first data row
    (the second row of the file). Adds "Uploaded" (filled with "0")
    and "ImageId" (filled with "") if they are missing.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    columns: OrderedDict[str, List[str]] = OrderedDict()
    for col in fieldnames:
        columns[col] = [(row.get(col) or "") for row in rows]

    n = len(rows)
    if "Uploaded" not in columns:
        columns["Uploaded"] = ["0"] * n
    if "ImageId" not in columns:
        columns["ImageId"] = [""] * n
    return columns


def save_csv_columns(path: str, columns: OrderedDict[str, List[str]]) -> None:
    """
    Write the column OrderedDict back to a CSV file safely.

    Writes to a temporary file first. On success, if the real file exists
    and no .bak exists yet, renames the real file to .bak; otherwise
    removes the real file. Then renames the temp file to the real name.
    """
    import os
    import tempfile

    target = Path(path)
    fieldnames = list(columns.keys())
    n = len(next(iter(columns.values()))) if columns else 0

    fd, tmp_name = tempfile.mkstemp(
        suffix=".tmp", prefix=target.name + ".", dir=target.parent or "."
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i in range(n):
                writer.writerow({col: columns[col][i] for col in fieldnames})
            f.flush()
            os.fsync(f.fileno())

        if target.exists():
            bak = target.with_suffix(target.suffix + ".bak")
            if not bak.exists():
                target.rename(bak)
            else:
                target.unlink()
        tmp_path.rename(target)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def row_from_columns(
    columns: OrderedDict[str, List[str]], idx: int
) -> Dict[str, str]:
    return {col: columns[col][idx] for col in columns}


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_privacy_level(value: Optional[str]) -> int:
    """
    Map a privacy-level name or number to Piwigo's integer.

    0=Everybody, 1=Contacts, 2=Friends, 4=Family, 8=Admins.
    Empty or missing value defaults to 0 (Everybody).
    """
    if not value or not str(value).strip():
        return 0
    v = str(value).strip().lower()
    names = {
        "everybody": 0,
        "none": 0,
        "contacts": 1,
        "contact": 1,
        "friends": 2,
        "friend": 2,
        "family": 4,
        "admins": 8,
        "admin": 8,
    }
    if v in names:
        return names[v]
    try:
        n = int(v)
    except ValueError:
        raise SystemExit(
            f"Unknown --privacy-level {value!r}. "
            "Use 0/1/2/4/8 or everybody/contacts/friends/family/admins."
        )
    if n not in (0, 1, 2, 4, 8):
        raise SystemExit(
            f"Privacy level {n} is not one of 0, 1, 2, 4, 8."
        )
    return n


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Piwigo batch uploader from CSV"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="JSON with base_url, api_key_id, api_key",
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="CSV file with image metadata",
    )
    parser.add_argument(
        "--share-with-group",
        default=None,
        help=(
            "Group name to grant access to each album. "
            "Default: curators. Matching is case-insensitive. "
            "Pass an empty string to skip."
        ),
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help=(
            "When sharing an album with a group, also apply the "
            "permission to all existing sub-albums (Piwigo recursive flag). "
            "Does not auto-inherit to future sub-albums created outside this tool."
        ),
    )
    parser.add_argument(
        "--parent-album",
        default=None,
        help=(
            "Create Carton albums as sub-albums of this parent album "
            "(created and shared if it does not exist)."
        ),
    )
    parser.add_argument(
        "--privacy-level",
        default=None,
        help=(
            "Photo privacy level for uploads (pwg.images.addSimple level). "
            "Default: everybody (0). Name or number: everybody/0, "
            "contacts/1, friends/2, family/4, admins/8."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done",
    )
    args = parser.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    for k in ("base_url", "api_key_id", "api_key"):
        if k not in cfg:
            sys.exit(f"Missing '{k}' in config JSON")

    share_with_group = (
        args.share_with_group
        if args.share_with_group is not None
        else cfg.get("share_with_group", "curators")
    )
    if share_with_group is not None:
        share_with_group = str(share_with_group).strip() or None

    privacy_level = parse_privacy_level(
        args.privacy_level or cfg.get("privacy_level")
    )

    client = PiwigoClient(
        cfg["base_url"],
        cfg["api_key_id"],
        cfg["api_key"],
        share_with_group=share_with_group,
        recursive=args.recursive,
        parent_album=args.parent_album,
    )

    print()
    print("piwigo-batch-uploader")
    print("---------------------")

    try:
        status = client.get_status()
        who = status.get("username") or "?"
        role = status.get("status") or "?"
        print(f"Authenticated as {who!r} (status={role})")
        if role not in ("admin", "webmaster"):
            print(
                "WARNING: album creation requires admin or webmaster. "
                "Create the API key on an administrator account."
            )
    except Exception as e:
        print(f"WARNING: could not check session status: {e}")

    columns = load_csv_columns(args.csv)
    if not columns or not next(iter(columns.values())):
        print("CSV is empty")
        return

    n = len(next(iter(columns.values())))
    print(f"Found {n} rows")
    success = 0
    errors = 0
    stopped = False

    for i in range(n):
        row = row_from_columns(columns, i)
        title = (row.get("Description") or "").strip()
        path = (row.get("Path") or "").strip()
        carton = (row.get("Carton") or "").strip()
        location = (row.get("Location") or "").strip()
        uploaded = (row.get("Uploaded") or "").strip()

        print(f"\n[{i + 1}/{n}] {title or path}")

        if uploaded == "1":
            print("  SKIP: already marked Uploaded")
            continue

        if not path:
            print("  SKIP: no Path")
            errors += 1
            continue

        src = Path(path)
        if not src.is_file() and not src.is_absolute():
            alt = Path(args.csv).resolve().parent / path
            if alt.is_file():
                print(f"  Path relative to CSV: {alt}")
                src = alt
                path = str(alt)

        tmp_path: Optional[Path] = None
        try:
            src = Path(path)
            if src.is_file():
                md5 = file_md5(src)
                existing = client.image_exists_by_md5(md5)
                if existing is not None:
                    print(
                        f"  WARNING: Piwigo reports an image with the same "
                        f"md5sum already exists (id={existing}). "
                        "Not marking as uploaded; continuing."
                    )

            album_id = client.get_or_create_album(carton, location)
            description = build_photo_description(row)

            rotation = decide_rotation(title)
            upload_path = None

            if rotation:
                if not src.is_file():
                    raise FileNotFoundError(f"Image not found: {src}")
                print(f"  Rotating {rotation} (temp copy)")
                if not args.dry_run:
                    tmp_path = make_rotated_temp(src, rotation)
                    upload_path = tmp_path
                else:
                    print(f"  [dry-run] would rotate {rotation}")

            if args.dry_run:
                print(f"  Would upload → album {carton!r} (id={album_id})")
                print(f"  Title: {title}")
                print(f"  Description:\n{description}")
                success += 1
                continue

            img_id = client.upload_image(
                path,
                album_id,
                title,
                description,
                upload_path=upload_path,
                level=privacy_level,
            )
            print(f"  OK → image id {img_id} in album {carton!r}")
            columns["Uploaded"][i] = "1"
            columns["ImageId"][i] = str(img_id) if img_id else ""
            success += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            stopped = True
            break
        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    if success > 0 and not args.dry_run:
        save_csv_columns(args.csv, columns)
        print(f"Saved {args.csv}")

    if stopped:
        print(f"\nStopped on error. Success: {success}, Errors: {errors}")
    else:
        print(f"\nDone. Success: {success}, Errors: {errors}")


if __name__ == "__main__":
    main()
