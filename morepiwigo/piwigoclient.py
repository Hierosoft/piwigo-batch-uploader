"""
Piwigo API client for album creation, permissions, and image upload.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import requests


class PiwigoClient:
    def __init__(
        self,
        base_url: str,
        api_key_id: str,
        api_key: str,
        share_with_group: Optional[str] = None,
        recursive: bool = False,
        parent_album: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.ws = f"{self.base_url}/ws.php"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-PIWIGO-API": f"{api_key_id}:{api_key}",
                "User-Agent": "piwigo-batch-uploader/1.5",
            }
        )
        self._album_cache: Dict[str, int] = {}  # name -> id
        self.share_with_group = (share_with_group or "").strip() or None
        self._share_group_id: Optional[int] = None
        self.recursive = recursive
        self.parent_album_name = (parent_album or "").strip() or None
        self._parent_album_id: Optional[int] = None

    def _call(
        self, method: str, data: Optional[dict] = None, files=None
    ) -> dict:
        # format must be a query param; POST body is ignored by some installs
        url = f"{self.ws}?format=json"
        payload = {"method": method}
        if data:
            payload.update(data)

        # Dummy token is accepted when authenticating with an API key
        if "pwg_token" not in payload and method.startswith(
            ("pwg.images.", "pwg.categories.", "pwg.permissions.")
        ):
            payload["pwg_token"] = "api_key"

        resp = self.session.post(
            url, data=payload, files=files, timeout=120
        )
        resp.raise_for_status()
        try:
            result = resp.json()
        except ValueError as exc:
            body = (resp.text or "").strip()
            snippet = body[:500] if body else "(empty body)"
            raise RuntimeError(
                f"Piwigo did not return JSON for {method} "
                f"(HTTP {resp.status_code} from {url}). "
                f"Response starts with: {snippet}"
            ) from exc

        if result.get("stat") != "ok":
            err = result.get("message") or result.get("err") or str(result)
            raise RuntimeError(f"Piwigo API error ({method}): {err}")

        return result.get("result")

    def get_status(self) -> dict:
        """Return pwg.session.getStatus (who this API key is)."""
        return self._call("pwg.session.getStatus") or {}

    def get_share_group_id(self) -> Optional[int]:
        """Resolve the share-with group id (cached). None if no group set."""
        if not self.share_with_group:
            return None
        if self._share_group_id is not None:
            return self._share_group_id

        result = self._call(
            "pwg.groups.getList",
            {
                "name": self.share_with_group,
                "per_page": 100,
            },
        )
        groups = result.get("groups") or []
        target = self.share_with_group.lower()
        for g in groups:
            if (g.get("name") or "").lower() == target:
                self._share_group_id = int(g["id"])
                print(
                    f"Using group {g['name']!r} "
                    f"(id={self._share_group_id})"
                )
                return self._share_group_id

        if groups:
            g = groups[0]
            self._share_group_id = int(g["id"])
            print(
                f"Warning: no exact match for {self.share_with_group!r}; "
                f"using {g['name']!r} (id={self._share_group_id})"
            )
            return self._share_group_id

        raise RuntimeError(
            f"Group {self.share_with_group!r} not found. "
            "Create it in Piwigo (Users → Groups)."
        )

    def share_album_with_group(self, album_id: int) -> None:
        """Make album private and, if a group was set, grant it access.

        If self.recursive is True, the permission is also applied to all
        *existing* sub-albums (Piwigo's recursive flag). Newly created
        sub-albums are not automatically covered unless this is called
        again on them or Piwigo's inheritance_by_default is enabled.
        """
        self._call(
            "pwg.categories.setInfo",
            {
                "category_id": album_id,
                "status": "private",
            },
        )
        group_id = self.get_share_group_id()
        if group_id is None:
            return
        self._call(
            "pwg.permissions.add",
            {
                "cat_id": album_id,
                "group_id": group_id,
                "recursive": "true" if self.recursive else "false",
            },
        )

    def _resolve_parent_id(self) -> Optional[int]:
        """Look up or create the optional parent album and return its id."""
        if not self.parent_album_name:
            return None
        if self._parent_album_id is not None:
            return self._parent_album_id

        if not self._album_cache:
            cats = self._call(
                "pwg.categories.getList",
                {
                    "recursive": "true",
                    "fullnamelevel": "false",
                },
            )
            for cat in cats.get("categories", []):
                self._album_cache[cat["name"]] = int(cat["id"])

        if self.parent_album_name in self._album_cache:
            self._parent_album_id = self._album_cache[self.parent_album_name]
        else:
            print(f"  Creating parent album: {self.parent_album_name!r}")
            result = self._call(
                "pwg.categories.add",
                {
                    "name": self.parent_album_name,
                    "visible": "true",
                    "status": "private",
                    "commentable": "true",
                },
            )
            self._parent_album_id = int(result["id"])
            self._album_cache[self.parent_album_name] = self._parent_album_id

        # Share the parent so members can navigate into it
        self.share_album_with_group(self._parent_album_id)
        return self._parent_album_id

    def get_or_create_album(self, name: str, location: str) -> int:
        """
        Return album id; create it (private, shared with friends) if missing.

        If a parent album was configured, the new album is created as a
        sub-album of that parent.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("Carton (album name) is empty")

        if name in self._album_cache:
            return self._album_cache[name]

        if not self._album_cache:
            cats = self._call(
                "pwg.categories.getList",
                {
                    "recursive": "true",
                    "fullnamelevel": "false",
                },
            )
            for cat in cats.get("categories", []):
                self._album_cache[cat["name"]] = int(cat["id"])

        if name in self._album_cache:
            album_id = self._album_cache[name]
            try:
                self.share_album_with_group(album_id)
            except Exception as e:
                print(
                    "  Warning: could not update permissions "
                    f"on existing album: {e}"
                )
            return album_id

        parent_id = self._resolve_parent_id()
        comment = (
            f"Location: {location.strip()}"
            if location and location.strip()
            else ""
        )
        print(
            f"  Creating album: {name!r}"
            + (f" under {self.parent_album_name!r}" if parent_id else "")
            + (f"  ({comment})" if comment else "")
        )
        data = {
            "name": name,
            "comment": comment,
            "visible": "true",
            "status": "private",
            "commentable": "true",
        }
        if parent_id is not None:
            data["parent"] = parent_id
        result = self._call("pwg.categories.add", data)
        album_id = int(result["id"])
        self._album_cache[name] = album_id

        self.share_album_with_group(album_id)
        if self.share_with_group:
            print(f"  Shared with group {self.share_with_group!r}")
        return album_id

    def image_exists_by_md5(self, md5sum: str) -> Optional[int]:
        """
        Ask Piwigo if an image with this md5sum already exists.

        Returns the image id if found, None otherwise.
        Accuracy depends on Piwigo's uniqueness_mode (md5sum vs filename)
        and on whether the stored md5sum still matches the original file.
        """
        if not md5sum:
            return None
        try:
            result = self._call(
                "pwg.images.exist",
                {"md5sum_list": md5sum},
            )
        except Exception:
            return None
        if isinstance(result, dict):
            val = result.get(md5sum)
            if val not in (None, "", "null"):
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return None
        return None

    def upload_image(
        self,
        path: str,
        album_id: int,
        title: str,
        description: str,
        upload_path: Optional[Path] = None,
        level: Optional[int] = None,
    ) -> int:
        """
        Upload image. If *upload_path* is given (e.g. rotated temp), use that
        for the file body but keep the original basename for Piwigo.

        *level* is the photo privacy level (0, 1, 2, 4, 8). Omit for default.
        """
        src = Path(path)
        if not src.is_file() and upload_path is None:
            raise FileNotFoundError(f"Image not found: {src}")

        file_to_send = upload_path if upload_path is not None else src
        if not file_to_send.is_file():
            raise FileNotFoundError(f"Upload file not found: {file_to_send}")

        with open(file_to_send, "rb") as f:
            files = {"image": (src.name, f)}  # keep original filename
            data = {
                "category": album_id,
                "name": title or src.stem,
                "comment": description,
            }
            if level is not None:
                data["level"] = str(level)
            result = self._call(
                "pwg.images.addSimple", data=data, files=files
            )

        if isinstance(result, dict):
            return int(result.get("id") or result.get("image_id") or 0)
        return 0
