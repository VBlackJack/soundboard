# La Cité de la Peur pack — how to fill it

No public GitHub source ships these clips, so the audio is produced by
extraction. The registry is pre-seeded with iconic lines as a **starter** —
verify the exact wording and attribution against the real clip before shipping.

## 1. Get the audio (extraction)

Use `tools/extract_clip.py` (needs `ffmpeg`, plus `yt-dlp` for YouTube sources —
neither is installed yet: `winget install Gyan.FFmpeg` and `pip install yt-dlp`).

```bash
python tools/extract_clip.py --pack-id citedelapeur \
  --source "<YouTube URL or local video path>" \
  --start 00:01:23 --duration 3.5 \
  --out-name cite_cest_lhistoire_dun_mec.mp3
```

Repeat once per line. The `--out-name` must match the `file` column in
`registry.csv`.

## 2. Review the registry

`packs/citedelapeur/registry.csv` already lists suggested lines (`file,title,character,episode`).
Adjust titles/characters, add or remove rows, and drop the
`*_exemple_a_remplacer.mp3` placeholder row.

## 3. Import

```bash
python tools/import_pack.py --from-csv packs/citedelapeur/registry.csv --no-download \
  --pack-id citedelapeur --pack-name "La Cité de la Peur" --default-theme mortis
```

Writes `packs/citedelapeur/pack.json` and upserts `assets/data/packs.json`
(existing packs preserved). `--default-theme` must be an id from
`assets/data/themes.json`.

## 4. Before committing

Add a La Cité de la Peur attribution block to the top-level `NOTICE` (1994 film
by Les Nuls / Alain Berbérian), mirroring the existing entries — clips are
copyrighted and shipped for personal, fan use only.
