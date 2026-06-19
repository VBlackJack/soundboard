# Caméra Café pack — how to fill it

This pack is scaffolded but **empty**: no public GitHub source ships the audio,
so the clips have to be supplied by hand. Once you have the `.mp3` files, the
import is two short steps.

## 1. Drop the audio

Put every `.mp3` directly under:

```
sounds/cameracafe/
```

Use lowercase, underscore-separated names, e.g. `serge_le_chef.mp3`,
`herve_la_secu.mp3`.

## 2. Fill the registry

Edit `packs/cameracafe/registry.csv`. One row per file (header already present):

```csv
file,title,character,episode
serge_le_chef.mp3,Serge le chef,Hervé,S1
herve_la_secu.mp3,Hervé la sécu,Hervé,S1
maeva_pause.mp3,Maéva en pause,Maéva,S2
```

- `file` — basename only, must match the file on disk.
- `title` — what shows on the card.
- `character` — drives the character filter (Hervé, Jean-Claude, Maéva, Sylvie…).
- `episode` — optional, free text.

## 3. Import (no download — files are already local)

```bash
python tools/import_pack.py --from-csv packs/cameracafe/registry.csv --no-download \
  --pack-id cameracafe --pack-name "Caméra Café" --default-theme slate
```

This writes `packs/cameracafe/pack.json` and upserts the entry into
`assets/data/packs.json` (existing packs are preserved). The `--default-theme`
value must be one of the ids in `assets/data/themes.json` (e.g. `slate`,
`parchment`, `folio`).

## 4. Before committing

Add a Caméra Café attribution block to the top-level `NOTICE` file (series
produced by Calt / M6), mirroring the existing Kaamelott / Dikkenek / Star Wars
entries — the clips are copyrighted and shipped for personal, fan use only.
