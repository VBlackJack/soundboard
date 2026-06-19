# OSS 117 pack — how to fill it

No public GitHub source ships these clips, so the audio is produced by
extraction. The registry is pre-seeded with iconic lines as a **starter** —
verify the exact wording and attribution against the real clip before shipping.

## 1. Get the audio (extraction)

Use `tools/extract_clip.py` (needs `ffmpeg`, plus `yt-dlp` for YouTube sources —
neither is installed yet: `winget install Gyan.FFmpeg` and `pip install yt-dlp`).

```bash
python tools/extract_clip.py --pack-id oss117 \
  --source "<YouTube URL or local video path>" \
  --start 00:01:23 --duration 3.5 \
  --out-name oss117_le_metier_qui_rentre.mp3
```

Repeat once per line. The `--out-name` must match the `file` column in
`registry.csv`.

## 2. Review the registry

`packs/oss117/registry.csv` already lists suggested lines (`file,title,character,episode`).
Adjust titles/characters, add or remove rows, and drop the
`*_exemple_a_remplacer.mp3` placeholder row.

## 3. Import

```bash
python tools/import_pack.py --from-csv packs/oss117/registry.csv --no-download \
  --pack-id oss117 --pack-name "OSS 117" --default-theme folio
```

Writes `packs/oss117/pack.json` and upserts `assets/data/packs.json` (existing
packs preserved). `--default-theme` must be an id from `assets/data/themes.json`.

## 4. Before committing

Add an OSS 117 attribution block to the top-level `NOTICE` (films produced by
Gaumont / Mandarin), mirroring the existing entries — clips are copyrighted and
shipped for personal, fan use only.
