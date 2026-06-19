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

"""Import a content pack into the SoundBoard.

Three registry sources are supported:
  * --from-repo  owner/name of a 2ec0b4-style GitHub soundboard (sounds/sounds.json)
  * --from-json  a sounds.json URL or path in the same format
  * --from-csv   a CSV with a file,title,character,episode header

Sounds are stored under sounds/<pack-id>/ by default and the manifest plus the
packs index are updated in place (existing packs are preserved).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from sb_lib import (
    build_pack,
    download_missing,
    load_packs_index,
    records_from_csv,
    records_from_json,
    upsert_pack,
    write_json,
)

LOG = logging.getLogger("import_pack")


def _repo_raw_base(owner_repo: str, branch: str) -> str:
    """Return the raw sounds/ base URL for a 2ec0b4-style repository."""
    return f"https://raw.githubusercontent.com/{owner_repo}/{branch}/sounds/"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a SoundBoard content pack.")
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--repo-root", default=os.path.dirname(here))

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-repo", help="GitHub 'owner/name' of a 2ec0b4-format soundboard")
    source.add_argument("--from-json", help="sounds.json URL or path (2ec0b4 format)")
    source.add_argument("--from-csv", help="CSV with columns file,title,character,episode")

    parser.add_argument("--branch", default="master", help="branch for --from-repo")
    parser.add_argument("--sounds-url", help="base URL to download missing mp3 (optional)")
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--pack-name", required=True)
    parser.add_argument("--default-theme", default="drakul")
    parser.add_argument("--sounds-base", help="web path prefix; default sounds/<pack-id>/")
    parser.add_argument("--no-download", action="store_true", help="never fetch mp3 files")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")

    sounds_base = args.sounds_base or f"sounds/{args.pack_id}/"
    if not sounds_base.endswith("/"):
        sounds_base += "/"
    sounds_dir = os.path.join(args.repo_root, sounds_base.rstrip("/"))

    sounds_url = args.sounds_url
    if args.from_repo:
        base = _repo_raw_base(args.from_repo, args.branch)
        records = records_from_json(base + "sounds.json")
        sounds_url = sounds_url or base
    elif args.from_json:
        records = records_from_json(args.from_json)
    else:
        records = records_from_csv(args.from_csv)
    LOG.info("registry: %d entries", len(records))

    if sounds_url and not args.no_download:
        new, kept, failed = download_missing(records, sounds_url, sounds_dir)
        LOG.info("download: %d new, %d existing, %d failed", new, kept, failed)

    pack = build_pack(
        records, sounds_dir,
        pack_id=args.pack_id, pack_name=args.pack_name,
        default_theme=args.default_theme, sounds_base=sounds_base,
    )
    if pack["count"] == 0:
        LOG.error("no sounds matched on disk in %s — aborting", sounds_dir)
        return 1

    write_json(os.path.join(args.repo_root, "packs", args.pack_id, "pack.json"), pack)
    LOG.info("wrote pack '%s' (%d sounds, %d characters)",
             pack["id"], pack["count"], len(pack["characters"]))

    index_path = os.path.join(args.repo_root, "assets", "data", "packs.json")
    index = load_packs_index(index_path)
    upsert_pack(index, {
        "id": pack["id"],
        "name": pack["name"],
        "manifest": f"packs/{pack['id']}/pack.json",
        "defaultTheme": pack["defaultTheme"],
    })
    write_json(index_path, index)
    LOG.info("updated packs.json (%d packs total)", len(index["packs"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
