# Les Visiteurs pack — how to fill it

No public GitHub source ships these clips, so the audio is produced by
extraction. The registry is pre-seeded with iconic lines as a **starter** —
verify the exact wording and attribution against the real clip before shipping.

## 1. Get the audio (extraction)

Use `tools/extract_clip.py` (needs `ffmpeg`, plus `yt-dlp` for YouTube sources —
neither is installed yet: `winget install Gyan.FFmpeg` and `pip install yt-dlp`).

```bash
python tools/extract_clip.py --pack-id visiteurs \
  --source "<YouTube URL or local video path>" \
  --start 00:01:23 --duration 3.5 \
  --out-name visiteurs_okay.mp3
```

Repeat once per line. The `--out-name` must match the `file` column in
`registry.csv`.

## 2. Review the registry

`packs/visiteurs/registry.csv` already lists suggested lines (`file,title,character,episode`).
Adjust titles/characters, add or remove rows, and drop the
`*_exemple_a_remplacer.mp3` placeholder row.

## 3. Import

```bash
python tools/import_pack.py --from-csv packs/visiteurs/registry.csv --no-download \
  --pack-id visiteurs --pack-name "Les Visiteurs" --default-theme bracken
```

Writes `packs/visiteurs/pack.json` and upserts `assets/data/packs.json`
(existing packs preserved). `--default-theme` must be an id from
`assets/data/themes.json`.

## 4. Before committing

Add a Les Visiteurs attribution block to the top-level `NOTICE` (1993 film by
Jean-Marie Poiré / Gaumont), mirroring the existing entries — clips are
copyrighted and shipped for personal, fan use only.
