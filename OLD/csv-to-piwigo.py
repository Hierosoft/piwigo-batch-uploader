#!/usr/bin/env python3
"""
Piwigo batch uploader
- Reads api_key_id + api_key from JSON
- Creates albums named after "Carton" (description = "Location: <Location value>")
- Makes each album private and shares it with the "friends" group
- Uses "Description" as photo title
- Uploads image from "Path"
- Builds photo description from remaining non-blank columns (including Path)
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Optional

import requests

# Columns that should NOT appear in the photo description
# (title / album name / album description source)
EXCLUDE_FROM_DESC = {"Description", "Carton", "Location"}

# Preferred order for fields in the photo description
DESC_ORDER = [
    "Date", "#", "Code", "Comment", "Frame", "Brand",
    "Scanned", "File", "Date Film", "Reel", "Serial", "Path",
]


class PiwigoClient:
    def __init__(
        self,
        base_url: str,
        api_key_id: str,
        api_key: str,
        friends_group_name: str = "friends",
    ):
        self.base_url = base_url.rstrip("/")
        self.ws = f"{self.base_url}/ws.php"
        self.session = requests.Session()
        self.session.headers.update({
            "X-PIWIGO-API": f"{api_key_id}:{api_key}",
            "User-Agent": "piwigo-batch-uploader/1.1",
        })
        self._album_cache: Dict[str, int] = {}  # name -> id
        self.friends_group_name = friends_group_name
        self._friends_group_id: Optional[int] = None

    def _call(self, method: str, data: Optional[dict] = None, files=None) -> dict:
        payload = {"method": method, "format": "json"}
        if data:
            payload.update(data)

        # Dummy token is accepted when authenticating with an API key
        if "pwg_token" not in payload and method.startswith(
            ("pwg.images.", "pwg.categories.", "pwg.permissions.")
        ):
            payload["pwg_token"] = "api_key"

        resp = self.session.post(self.ws, data=payload, files=files, timeout=120)
        resp.raise_for_status()
        result = resp.json()

        if result.get("stat") != "ok":
            err = result.get("message") or result.get("err") or str(result)
            raise RuntimeError(f"Piwigo API error ({method}): {err}")

        return result.get("result")

    def get_friends_group_id(self) -> int:
        """Resolve the friends group id (cached)."""
        if self._friends_group_id is not None:
            return self._friends_group_id

        result = self._call("pwg.groups.getList", {
            "name": self.friends_group_name,
            "per_page": 100,
        })
        groups = result.get("groups") or []
        # Prefer exact (case-insensitive) match
        target = self.friends_group_name.lower()
        for g in groups:
            if (g.get("name") or "").lower() == target:
                self._friends_group_id = int(g["id"])
                print(f"Using friends group {g['name']!r} (id={self._friends_group_id})")
                return self._friends_group_id

        # Fallback: first result if the API did a partial match
        if groups:
            g = groups[0]
            self._friends_group_id = int(g["id"])
            print(
                f"Warning: no exact match for {self.friends_group_name!r}; "
                f"using {g['name']!r} (id={self._friends_group_id})"
            )
            return self._friends_group_id

        raise RuntimeError(
            f"Group {self.friends_group_name!r} not found. "
            "Create it in Piwigo (Users → Groups) and put your friends in it."
        )

    def share_album_with_friends(self, album_id: int) -> None:
        """Make album private (if needed) and grant the friends group access."""
        group_id = self.get_friends_group_id()
        # Ensure private status
        self._call("pwg.categories.setInfo", {
            "category_id": album_id,
            "status": "private",
        })
        # Grant group permission
        self._call("pwg.permissions.add", {
            "cat_id": album_id,
            "group_id": group_id,
            "recursive": "false",
        })

    def get_or_create_album(self, name: str, location: str) -> int:
        """Return album id; create it (private, shared with friends) if missing."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Carton (album name) is empty")

        if name in self._album_cache:
            return self._album_cache[name]

        # Load existing albums once
        if not self._album_cache:
            cats = self._call("pwg.categories.getList", {
                "recursive": "true",
                "fullnamelevel": "false",
            })
            for cat in cats.get("categories", []):
                self._album_cache[cat["name"]] = int(cat["id"])

        if name in self._album_cache:
            album_id = self._album_cache[name]
            # Still ensure friends can see existing albums created earlier
            try:
                self.share_album_with_friends(album_id)
            except Exception as e:
                print(f"  Warning: could not update permissions on existing album: {e}")
            return album_id

        # Create new private album
        comment = f"Location: {location.strip()}" if location and location.strip() else ""
        print(f"  Creating album: {name!r}" + (f"  ({comment})" if comment else ""))
        result = self._call("pwg.categories.add", {
            "name": name,
            "comment": comment,
            "visible": "true",
            "status": "private",
            "commentable": "true",
        })
        album_id = int(result["id"])
        self._album_cache[name] = album_id

        self.share_album_with_friends(album_id)
        print(f"  Shared with group {self.friends_group_name!r}")
        return album_id

    def upload_image(
        self,
        path: str,
        album_id: int,
        title: str,
        description: str,
    ) -> int:
        path_obj = Path(path)
        if not path_obj.is_file():
            raise FileNotFoundError(f"Image not found: {path_obj}")

        with open(path_obj, "rb") as f:
            files = {"image": (path_obj.name, f)}
            data = {
                "category": album_id,
                "name": title or path_obj.stem,
                "comment": description,
            }
            result = self._call("pwg.images.addSimple", data=data, files=files)

        if isinstance(result, dict):
            return int(result.get("id") or result.get("image_id") or 0)
        return 0


def build_photo_description(row: dict) -> str:
    """Turn remaining non-blank columns into multi-line description (includes Path)."""
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


def main():
    parser = argparse.ArgumentParser(description="Piwigo batch uploader from CSV")
    parser.add_argument("--config", required=True, help="JSON with base_url, api_key_id, api_key")
    parser.add_argument("--csv", required=True, help="CSV file with image metadata")
    parser.add_argument(
        "--friends-group",
        default=None,
        help='Name of the friends group (default: "friends" or value from config)',
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be done")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    for k in ("base_url", "api_key_id", "api_key"):
        if k not in cfg:
            sys.exit(f"Missing '{k}' in config JSON")

    friends_group = (
        args.friends_group
        or cfg.get("friends_group")
        or "friends"
    )

    client = PiwigoClient(
        cfg["base_url"],
        cfg["api_key_id"],
        cfg["api_key"],
        friends_group_name=friends_group,
    )

    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("CSV is empty")
        return

    print(f"Found {len(rows)} rows")
    success = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        title = (row.get("Description") or "").strip()
        path = (row.get("Path") or "").strip()
        carton = (row.get("Carton") or "").strip()
        location = (row.get("Location") or "").strip()

        print(f"\n[{i}/{len(rows)}] {title or path}")

        if not path:
            print("  SKIP: no Path")
            errors += 1
            continue

        try:
            album_id = client.get_or_create_album(carton, location)
            description = build_photo_description(row)

            if args.dry_run:
                print(f"  Would upload → album {carton!r} (id={album_id})")
                print(f"  Title: {title}")
                print(f"  Description:\n{description}")
                success += 1
                continue

            img_id = client.upload_image(path, album_id, title, description)
            print(f"  OK → image id {img_id} in album {carton!r}")
            success += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    print(f"\nDone. Success: {success}, Errors: {errors}")


if __name__ == "__main__":
    main()
