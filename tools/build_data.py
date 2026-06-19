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

"""Generate the ThemeForge themes file and, optionally, the Kaamelott pack.

  * assets/data/themes.json  -- always regenerated from the ThemeForge variants
  * packs/<id>/pack.json       -- only when --registry is given
  * assets/data/packs.json     -- upserted (existing packs are preserved)

Pack building and the packs index are delegated to sb_lib so that this script
and import_pack.py stay consistent.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from typing import Any

from sb_lib import (
    build_pack,
    load_packs_index,
    records_from_json,
    upsert_pack,
    write_json,
)

LOG = logging.getLogger("build_data")

COLOR_SLOTS = (
    "Background", "Surface", "SurfaceAlt", "Accent", "AccentHover",
    "AccentPressed", "TextPrimary", "TextSecondary", "Border", "Success",
    "Warning", "Error", "Info", "CurrentLine", "Selection", "Foreground",
    "Comment", "Cyan", "Green", "Orange", "Pink", "Purple", "Red", "Yellow",
    "Blue",
)

_COLOR_RE = re.compile(
    r'<Color\s+x:Key="(?P<key>\w+)Color">\s*(?P<val>#[0-9A-Fa-f]{6,8})\s*</Color>'
)
_STRING_RE = re.compile(
    r'<sys:String\s+x:Key="(?P<key>\w+)">\s*(?P<val>[^<]+?)\s*</sys:String>'
)


def _to_css_color(argb: str) -> str:
    """Convert an XAML #AARRGGBB / #RRGGBB token to a CSS color string."""
    value = argb.lstrip("#")
    if len(value) == 8:
        alpha = int(value[0:2], 16)
        rgb = value[2:]
        return f"#{rgb.upper()}" if alpha == 255 else f"#{rgb.upper()}{value[0:2].upper()}"
    return f"#{value.upper()}"


def parse_theme(path: str) -> dict[str, Any]:
    """Parse a single ThemeForge variant XAML into a web theme descriptor."""
    text = open(path, encoding="utf-8").read()
    colors_raw = {m.group("key"): m.group("val") for m in _COLOR_RE.finditer(text)}
    strings = {m.group("key"): m.group("val") for m in _STRING_RE.finditer(text)}
    base = os.path.splitext(os.path.basename(path))[0]
    colors = {
        slot[0].lower() + slot[1:]: _to_css_color(colors_raw[slot])
        for slot in COLOR_SLOTS if slot in colors_raw
    }
    return {
        "id": base.lower(),
        "name": strings.get("ThemeDisplayName", base),
        "family": strings.get("ThemeFamily", "Dark"),
        "colors": colors,
    }


def build_themes(themes_dir: str) -> dict[str, Any]:
    """Build the themes.json payload from every variant in themes_dir."""
    variants = []
    for entry in sorted(os.listdir(themes_dir)):
        full = os.path.join(themes_dir, entry)
        if entry.endswith(".xaml") and os.path.isfile(full):
            theme = parse_theme(full)
            variants.append(theme)
            LOG.info("theme parsed: %s (%d slots)", theme["name"], len(theme["colors"]))
    return {
        "tokens": {
            "radius": {"sm": "3px", "md": "4px", "lg": "6px", "xl": "10px", "full": "999px"},
            "spacing": {"xs": "4px", "sm": "6px", "md": "8px", "lg": "12px", "xl": "16px", "xxl": "24px"},
            "fontSize": {"xs": "11px", "sm": "12px", "md": "14px", "lg": "18px", "xl": "22px"},
        },
        "themes": variants,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    parser = argparse.ArgumentParser(description="Build SoundBoard themes and the Kaamelott pack.")
    parser.add_argument("--repo", default=repo, help="SoundBoard repo root")
    parser.add_argument(
        "--themes-dir",
        default=os.path.normpath(os.path.join(repo, "..", "ThemeForge", "src",
                                              "ThemeForge.Theme", "Themes")),
        help="ThemeForge Themes directory",
    )
    parser.add_argument("--registry", help="Kaamelott sounds.json (optional)")
    parser.add_argument("--pack-id", default="kaamelott")
    parser.add_argument("--pack-name", default="Kaamelott")
    parser.add_argument("--default-theme", default="drakul")
    parser.add_argument("--sounds-base", default="sounds/")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")

    themes = build_themes(args.themes_dir)
    write_json(os.path.join(args.repo, "assets", "data", "themes.json"), themes)
    LOG.info("wrote themes.json (%d themes)", len(themes["themes"]))

    if not args.registry:
        LOG.info("no --registry given; skipped pack generation")
        return 0

    sounds_dir = os.path.join(args.repo, args.sounds_base.rstrip("/"))
    pack = build_pack(
        records_from_json(args.registry), sounds_dir,
        pack_id=args.pack_id, pack_name=args.pack_name,
        default_theme=args.default_theme, sounds_base=args.sounds_base,
    )
    write_json(os.path.join(args.repo, "packs", args.pack_id, "pack.json"), pack)
    LOG.info("wrote pack '%s' (%d sounds, %d characters)",
             pack["id"], pack["count"], len(pack["characters"]))

    index_path = os.path.join(args.repo, "assets", "data", "packs.json")
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
