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
Module for downloading audio files from the Kaamelott Soundboard.
Reads settings from config.json and downloads missing sound files.
"""

import json
import os
import urllib.request
import sys


def load_config(config_path):
    """
    Loads configuration settings from a JSON file.
    """
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def download_file(url, output_path):
    """
    Downloads a single file from url and saves it to output_path.
    """
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def main():
    config_file = "config.json"
    config = load_config(config_file)

    sounds_json_url = config.get("sounds_json_url")
    sounds_base_url = config.get("sounds_base_url")
    output_dir = config.get("output_directory")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Fetching sounds registry database...")
    try:
        with urllib.request.urlopen(sounds_json_url) as response:
            sounds_data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch sounds registry: {e}")
        sys.exit(1)

    total_sounds = len(sounds_data)
    print(f"Loaded registry. Found {total_sounds} sounds to process.")

    downloaded_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, sound in enumerate(sounds_data, start=1):
        filename = sound.get("file")
        if not filename:
            continue

        sound_url = f"{sounds_base_url}{filename}"
        dest_path = os.path.join(output_dir, filename)

        if os.path.exists(dest_path):
            skipped_count += 1
            continue

        print(f"[{idx}/{total_sounds}] Downloading {filename}...")
        success = download_file(sound_url, dest_path)
        if success:
            downloaded_count += 1
        else:
            failed_count += 1

    print("\nProcessing complete:")
    print(f"  Downloaded: {downloaded_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Failed: {failed_count}")


if __name__ == "__main__":
    main()
