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

"""Import a content pack from the useless-industries soundbox API.

The public endpoint <API>/sounds.php?app=<package> returns a JSON array of
sounds (name, res, description, speaker). Audio is served at
<API>/<dir>/sounds/<res>.mp3, where <dir> is resolved by probing because it is
sometimes the package short name and sometimes the resource prefix. The returned
text is double-encoded UTF-8 and is repaired before use. The manifest and the
packs index are then produced through import_pack/sb_lib.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import import_pack
from sb_lib import download_missing

API = "https://useless-industries.fr/soundboxes"
HEADERS = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)"}
DIGITS = "0123456789"

LOG = logging.getLogger("import_useless")


def _fix_mojibake(text: str) -> str:
    """Repair UTF-8 bytes that were decoded as Latin-1 (e.g. 'CÃ©sar' -> 'César')."""
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _http_json(url: str) -> list[dict[str, str]]:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        data: list[dict[str, str]] = json.loads(response.read().decode("utf-8"))
        return data


def _resource_exists(url: str) -> bool:
    request = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return bool(200 <= response.status < 300)
    except urllib.error.URLError:
        return False


def _resolve_audio_dir(package: str, sample_res: str) -> str:
    """Find the audio sub-folder by probing the candidate shapes for one file."""
    candidates = [package.split(".")[-1], sample_res.rstrip(DIGITS)]
    for candidate in candidates:
        if _resource_exists(f"{API}/{candidate}/sounds/{sample_res}.mp3"):
            return candidate
    raise RuntimeError(f"cannot resolve audio dir for {package} (tried {candidates})")


def records_from_useless(package: str) -> tuple[list[dict[str, str]], str]:
    """Return normalized records and the resolved audio dir for an app package."""
    raw = _http_json(f"{API}/sounds.php?app={urllib.parse.quote(package)}")
    if not raw:
        raise RuntimeError(f"no sounds returned for {package}")
    records: list[dict[str, str]] = []
    for item in raw:
        res = (item.get("res") or "").strip()
        if not res:
            continue
        speaker = _fix_mojibake((item.get("speaker") or "").strip())
        records.append({
            "file": f"{res}.mp3",
            "title": _fix_mojibake((item.get("name") or res).strip()),
            "character": speaker.split(",")[0].strip(),
            "episode": "",
        })
    return records, _resolve_audio_dir(package, raw[0]["res"])


def _write_registry(path: str, records: list[dict[str, str]]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "title", "character", "episode"])
        writer.writeheader()
        writer.writerows(records)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Import a useless-industries soundbox as a pack.")
    parser.add_argument("--app", required=True, help="app package, e.g. fr.useless.asterix")
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--pack-name", required=True)
    parser.add_argument("--default-theme", required=True)
    parser.add_argument("--repo-root", default=os.path.dirname(here))
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")

    records, audio_dir = records_from_useless(args.app)
    LOG.info("api: %d sounds, audio dir '%s'", len(records), audio_dir)

    sounds_dir = os.path.join(args.repo_root, "sounds", args.pack_id)
    new, kept, failed = download_missing(records, f"{API}/{audio_dir}/sounds/", sounds_dir)
    LOG.info("download: %d new, %d existing, %d failed", new, kept, failed)

    registry = os.path.join(args.repo_root, "packs", args.pack_id, "registry.csv")
    _write_registry(registry, records)

    return import_pack.main([
        "--from-csv", registry, "--no-download",
        "--pack-id", args.pack_id, "--pack-name", args.pack_name,
        "--default-theme", args.default_theme, "--repo-root", args.repo_root,
    ])


if __name__ == "__main__":
    sys.exit(main())
