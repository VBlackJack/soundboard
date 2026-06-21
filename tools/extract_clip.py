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
Helper tool to extract audio segments from local video/audio files or YouTube videos.
Converts the output to MP3 and saves it in the sound pack directory.
"""

import argparse
import os
import subprocess
import sys


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract and crop audio segments from YouTube or local files."
    )
    parser.add_argument("--source", required=True, help="YouTube URL or local path to media file")
    parser.add_argument("--start", required=True, help="Start time in seconds or HH:MM:SS format")
    parser.add_argument("--duration", type=float, required=True, help="Duration of the clip in seconds")
    parser.add_argument("--out-name", required=True, help="Name of the output mp3 file (e.g. jc_test.mp3)")
    parser.add_argument("--pack-id", default="cameracafe", help="ID of the pack (determines the folder)")
    return parser.parse_args(argv)


def to_seconds(value: str) -> float:
    """Convert a time string in seconds or HH:MM:SS / MM:SS form to seconds."""
    parts = value.split(":")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def check_tool_installed(tool_name: str) -> bool:
    try:
        subprocess.run(
            [tool_name, "-version" if tool_name == "ffmpeg" else "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return True
    except FileNotFoundError:
        return False


def extract_from_local(input_path: str, start: str, duration: float, output_path: str) -> bool:
    print(f"Extracting segment from local file: {input_path}")
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", start,
            "-t", str(duration),
            "-i", input_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            output_path
        ]
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg processing: {e}")
        return False


def extract_from_youtube(url: str, start: str, duration: float, output_path: str) -> bool:
    print(f"Downloading and cutting segment from YouTube: {url}")
    # Using yt-dlp section downloading feature
    try:
        # Construct the section query for yt-dlp.
        # Format for --download-sections is '*[start]-[end]' in seconds.
        # Accept both raw seconds and HH:MM:SS / MM:SS start values.
        start_sec = to_seconds(start)
        end_sec = start_sec + duration
        section_str = f"*{start_sec}-{end_sec}"

        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "192K",
            "--download-sections", section_str,
            "--force-keyframes-at-cuts",
            "-o", output_path,
            url
        ]
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during yt-dlp downloading: {e}")
        return False


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    
    output_dir = os.path.join(project_root, "sounds", args.pack_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, args.out_name)
    
    if not check_tool_installed("ffmpeg"):
        print("Error: ffmpeg is not installed or not in the system PATH.")
        print("Please install ffmpeg first. (e.g. winget install Gyan.FFmpeg on Windows)")
        return 1
        
    is_youtube = args.source.startswith("http://") or args.source.startswith("https://") or "youtube.com" in args.source or "youtu.be" in args.source
    
    if is_youtube:
        if not check_tool_installed("yt-dlp"):
            print("Error: yt-dlp is not installed or not in the system PATH.")
            print("Please install yt-dlp first. (e.g. pip install yt-dlp)")
            return 1
        success = extract_from_youtube(args.source, args.start, args.duration, output_path)
    else:
        if not os.path.exists(args.source):
            print(f"Error: Local source file not found: {args.source}")
            return 1
        success = extract_from_local(args.source, args.start, args.duration, output_path)
        
    if success and os.path.exists(output_path):
        print(f"Successfully generated clip at: {output_path}")
        return 0
    else:
        print("Failed to generate clip.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
