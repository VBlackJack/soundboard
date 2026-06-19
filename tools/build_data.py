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

"""
Generates the static data files consumed by the SoundBoard web app.

Outputs (relative to the repository root):
  * assets/data/themes.json   -- all ThemeForge palettes as web tokens
  * assets/data/packs.json     -- index of available content packs
  * packs/<id>/pack.json        -- one manifest per content pack

The ThemeForge palettes are read from the sibling ThemeForge repository.
Nothing is hardcoded: paths come from CLI arguments or sensible defaults
resolved from the repository layout.
"""

import argparse
import json
import logging
import os
import re
import sys
from collections import Counter

LOG = logging.getLogger("build_data")

# Slots we expose to the web layer, mapped from their XAML "<Name>Color" key.
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
        if alpha == 255:
            return f"#{rgb.upper()}"
        return f"#{rgb.upper()}{value[0:2].upper()}"  # CSS #RRGGBBAA
    return f"#{value.upper()}"


def parse_theme(path: str) -> dict:
    """Parse a single ThemeForge variant XAML into a web theme descriptor."""
    text = open(path, encoding="utf-8").read()
    colors_raw = {m.group("key"): m.group("val") for m in _COLOR_RE.finditer(text)}
    strings = {m.group("key"): m.group("val") for m in _STRING_RE.finditer(text)}

    name = strings.get("ThemeDisplayName") or os.path.splitext(os.path.basename(path))[0]
    family = strings.get("ThemeFamily", "Dark")

    colors = {}
    for slot in COLOR_SLOTS:
        if slot in colors_raw:
            key = slot[0].lower() + slot[1:]
            colors[key] = _to_css_color(colors_raw[slot])

    return {
        "id": os.path.splitext(os.path.basename(path))[0].lower(),
        "name": name,
        "family": family,
        "colors": colors,
    }


def build_themes(themes_dir: str) -> dict:
    """Build the themes.json payload from every variant in themes_dir."""
    variants = []
    for entry in sorted(os.listdir(themes_dir)):
        if not entry.endswith(".xaml"):
            continue
        full = os.path.join(themes_dir, entry)
        if os.path.isfile(full):
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


def build_pack(registry_path: str, sounds_dir: str, pack_id: str,
               pack_name: str, default_theme: str, sounds_base: str) -> dict:
    """Build a content-pack manifest from a sound registry JSON file."""
    registry = json.load(open(registry_path, encoding="utf-8"))
    available = set(os.listdir(sounds_dir))

    sounds = []
    missing = []
    char_counter: Counter = Counter()
    for item in registry:
        filename = item.get("file")
        if not filename:
            continue
        if filename not in available:
            missing.append(filename)
            continue
        character = (item.get("character") or "").strip()
        sounds.append({
            "file": filename,
            "title": (item.get("title") or filename).strip(),
            "character": character,
            "episode": (item.get("episode") or "").strip(),
        })
        if character:
            char_counter[character] += 1

    if missing:
        LOG.warning("%d registry entries missing from %s", len(missing), sounds_dir)

    sounds.sort(key=lambda s: s["title"].lower())
    characters = [c for c, _ in char_counter.most_common()]

    return {
        "id": pack_id,
        "name": pack_name,
        "defaultTheme": default_theme,
        "soundsBase": sounds_base,
        "characters": characters,
        "count": len(sounds),
        "sounds": sounds,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build SoundBoard data files.")
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    parser.add_argument("--repo", default=repo, help="SoundBoard repo root")
    parser.add_argument(
        "--themes-dir",
        default=os.path.normpath(os.path.join(repo, "..", "ThemeForge", "src",
                                              "ThemeForge.Theme", "Themes")),
        help="ThemeForge Themes directory",
    )
    parser.add_argument("--registry", required=True, help="Sound registry JSON")
    parser.add_argument("--pack-id", default="kaamelott")
    parser.add_argument("--pack-name", default="Kaamelott")
    parser.add_argument("--default-theme", default="drakul")
    parser.add_argument("--sounds-base", default="sounds/")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")

    themes = build_themes(args.themes_dir)
    data_dir = os.path.join(args.repo, "assets", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "themes.json"), "w", encoding="utf-8") as fh:
        json.dump(themes, fh, ensure_ascii=False, indent=2)
    LOG.info("wrote themes.json (%d themes)", len(themes["themes"]))

    sounds_dir = os.path.join(args.repo, args.sounds_base.rstrip("/"))
    pack = build_pack(args.registry, sounds_dir, args.pack_id, args.pack_name,
                      args.default_theme, args.sounds_base)
    pack_dir = os.path.join(args.repo, "packs", args.pack_id)
    os.makedirs(pack_dir, exist_ok=True)
    with open(os.path.join(pack_dir, "pack.json"), "w", encoding="utf-8") as fh:
        json.dump(pack, fh, ensure_ascii=False, indent=2)
    LOG.info("wrote pack '%s' (%d sounds, %d characters)",
             pack["id"], pack["count"], len(pack["characters"]))

    packs_index = {
        "packs": [{
            "id": pack["id"],
            "name": pack["name"],
            "manifest": f"packs/{pack['id']}/pack.json",
            "defaultTheme": pack["defaultTheme"],
        }]
    }
    with open(os.path.join(data_dir, "packs.json"), "w", encoding="utf-8") as fh:
        json.dump(packs_index, fh, ensure_ascii=False, indent=2)
    LOG.info("wrote packs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
