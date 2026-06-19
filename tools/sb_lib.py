#
# Copyright 2026 Julien Bombled
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Shared helpers for the SoundBoard data tooling.

A "record" is a normalized dict with the keys file, title, character and
episode. A "pack" is the manifest consumed by the web app. Nothing here is
hardcoded: callers pass every path and identifier explicitly.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any

LOG = logging.getLogger("sb")

RECORD_KEYS = ("file", "title", "character", "episode")


def _normalize(record: dict[str, Any]) -> dict[str, str]:
    """Coerce an arbitrary registry row into a clean record."""
    file_name = (record.get("file") or "").strip()
    return {
        "file": file_name,
        "title": (record.get("title") or file_name).strip(),
        "character": (record.get("character") or "").strip(),
        "episode": (record.get("episode") or "").strip(),
    }


def _load_json(source: str) -> list[dict[str, Any]]:
    """Load a JSON array from a URL or a local path."""
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    else:
        with open(source, encoding="utf-8") as handle:
            data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"expected a JSON array in {source}, got {type(data).__name__}")
    return data


def records_from_json(source: str) -> list[dict[str, str]]:
    """Read records from a 2ec0b4-style sounds.json (URL or path)."""
    return [_normalize(row) for row in _load_json(source) if row.get("file")]


def records_from_csv(path: str) -> list[dict[str, str]]:
    """Read records from a CSV with a file,title,character,episode header."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [_normalize(row) for row in reader if (row.get("file") or "").strip()]


def download_missing(
    records: list[dict[str, str]],
    base_url: str,
    dest_dir: str,
    *,
    logger: logging.Logger = LOG,
) -> tuple[int, int, int]:
    """Download any record file missing from dest_dir. Returns (new, kept, failed)."""
    if not base_url:
        return (0, 0, 0)
    os.makedirs(dest_dir, exist_ok=True)
    present = set(os.listdir(dest_dir))
    base = base_url if base_url.endswith("/") else base_url + "/"
    new = kept = failed = 0
    for record in records:
        name = record["file"]
        if name in present:
            kept += 1
            continue
        url = base + urllib.parse.quote(name)
        try:
            urllib.request.urlretrieve(url, os.path.join(dest_dir, name))
            new += 1
            logger.info("downloaded %s", name)
        except OSError as exc:  # network/IO error: log and continue, never silent
            logger.warning("failed %s: %s", name, exc)
            failed += 1
    return (new, kept, failed)


def build_pack(
    records: list[dict[str, str]],
    sounds_dir: str,
    *,
    pack_id: str,
    pack_name: str,
    default_theme: str,
    sounds_base: str,
) -> dict[str, Any]:
    """Build a pack manifest, keeping only records whose file exists on disk."""
    available = set(os.listdir(sounds_dir)) if os.path.isdir(sounds_dir) else set()
    sounds: list[dict[str, str]] = []
    counter: dict[str, int] = {}
    for record in records:
        if record["file"] not in available:
            continue
        sounds.append(record)
        character = record["character"]
        if character:
            counter[character] = counter.get(character, 0) + 1
    sounds.sort(key=lambda item: item["title"].lower())
    characters = [c for c, _ in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {
        "id": pack_id,
        "name": pack_name,
        "defaultTheme": default_theme,
        "soundsBase": sounds_base,
        "characters": characters,
        "count": len(sounds),
        "sounds": sounds,
    }


def load_packs_index(path: str) -> dict[str, Any]:
    """Load the packs index, or return an empty one if it does not exist yet."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"expected a JSON object in {path}, got {type(data).__name__}")
        return data
    return {"packs": []}


def upsert_pack(index: dict[str, Any], entry: dict[str, Any]) -> None:
    """Insert or replace a pack entry in the index, keyed by id."""
    packs: list[dict[str, Any]] = index.setdefault("packs", [])
    for position, existing in enumerate(packs):
        if existing.get("id") == entry["id"]:
            packs[position] = entry
            return
    packs.append(entry)


def write_json(path: str, data: Any) -> None:
    """Write pretty UTF-8 JSON, creating parent directories as needed."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
