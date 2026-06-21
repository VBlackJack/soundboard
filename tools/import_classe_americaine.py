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
Scraper script to automatically retrieve and build the 'La Classe Américaine' sound pack
from the ouich.es soundboard.
"""

from __future__ import annotations

import csv
import os
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor


# Configuration constants
OUICH_BASE_URL = "https://ouich.es"
PACK_ID = "classe_americaine"
PACK_NAME = "La Classe Américaine"
DEFAULT_THEME = "parchment"


def get_html(url: str, ctx: ssl.SSLContext) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as response:
        return str(response.read().decode("utf-8"))


def download_file(url: str, dest: str, ctx: ssl.SSLContext) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx) as response:
            with open(dest, "wb") as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def scrape_tag_data(tag: str, ctx: ssl.SSLContext) -> dict[str, str]:
    url = f"{OUICH_BASE_URL}/tag/{tag}.html"
    try:
        html = get_html(url, ctx)
        
        # Search for citation
        citation_match = re.search(r'class="citation">(.*?)</div>', html, re.DOTALL)
        title = citation_match.group(1).strip() if citation_match else tag.replace("_", " ").capitalize()
        
        # Clean HTML entities if any
        title = title.replace("&#8217;", "'").replace("’", "'").replace("&nbsp;", " ")
        
        # Try to identify character from citation text or default to Unknown
        character = "George Abitbol"
        if "indien" in title.lower() or "chips" in title.lower():
            character = "L'Indien"
        elif "josé" in title.lower():
            character = "José"
        elif "peter" in title.lower():
            character = "Peter"
        elif "steven" in title.lower():
            character = "Steven"
        elif "dino" in title.lower():
            character = "Dino"
        else:
            # Default fallback character
            character = "George Abitbol"
            
        return {
            "file": f"{tag}.mp3",
            "title": title,
            "character": character,
            "episode": ""
        }
    except Exception as e:
        print(f"Failed to scrape tag {tag}: {e}")
        return {
            "file": f"{tag}.mp3",
            "title": tag.replace("_", " ").capitalize(),
            "character": "George Abitbol",
            "episode": ""
        }


def main() -> int:
    # Standard TLS context with certificate and hostname verification enabled.
    ctx = ssl.create_default_context()

    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    
    pack_dir = os.path.join(project_root, "packs", PACK_ID)
    sounds_dir = os.path.join(project_root, "sounds", PACK_ID)
    
    os.makedirs(pack_dir, exist_ok=True)
    os.makedirs(sounds_dir, exist_ok=True)

    print("Fetching ouich.es homepage to collect all sound tags...")
    try:
        homepage_html = get_html(OUICH_BASE_URL, ctx)
    except Exception as e:
        print(f"Failed to load ouich.es: {e}")
        return 1

    # Extract all tag links
    tags = re.findall(r'href="\./tag/([^"]+?)\.html"', homepage_html)
    tags = list(set(tags))  # De-duplicate
    
    if not tags:
        print("No sound tags found on the website. The HTML structure might have changed.")
        return 1

    total_tags = len(tags)
    print(f"Found {total_tags} sound tags. Scraping details and downloading audio...")

    records = []
    
    # Use ThreadPoolExecutor to speed up page scraping and file downloading
    def process_tag(tag: str) -> dict[str, str] | None:
        print(f"Processing sound: {tag}...")
        # Get metadata
        data = scrape_tag_data(tag, ctx)
        
        # Download MP3
        mp3_url = f"{OUICH_BASE_URL}/mp3/{tag}.mp3"
        dest_path = os.path.join(sounds_dir, f"{tag}.mp3")
        
        success = True
        if not os.path.exists(dest_path):
            success = download_file(mp3_url, dest_path, ctx)
            
        if success:
            return data
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(process_tag, tags)
        for r in results:
            if r:
                records.append(r)

    # Write registry.csv
    registry_csv_path = os.path.join(pack_dir, "registry.csv")
    print(f"Writing registry to {registry_csv_path}...")
    with open(registry_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "title", "character", "episode"])
        writer.writeheader()
        writer.writerows(records)

    # Run the import pack script
    print("\nRegistering and importing the pack into the SoundBoard...")

    # Invoke import_pack main logic
    sys.path.insert(0, here)
    try:
        import import_pack
        import_argv = [
            "--from-csv", registry_csv_path,
            "--no-download",
            "--pack-id", PACK_ID,
            "--pack-name", PACK_NAME,
            "--default-theme", DEFAULT_THEME
        ]
        import_pack.main(import_argv)
        print("\nSuccess! 'La Classe Americaine' pack has been successfully imported.")
        print(f"Total sounds: {len(records)}")
        print(f"Files saved in: {sounds_dir}")
        return 0
    except Exception as e:
        print(f"Failed to import pack: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
