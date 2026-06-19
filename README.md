# SoundBoard

Soundboard web **moderne, statique et multi-thème**, prête à héberger sur
**GitHub Pages**. Aucune dépendance, aucun build côté navigateur : du HTML, du
CSS et du JavaScript vanilla.

Le premier pack est **Kaamelott** (645 répliques). L'architecture est pensée
pour décliner facilement d'autres packs (Star Wars, etc.), chacun avec son
propre thème graphique par défaut.

Les thèmes graphiques proviennent de **ThemeForge** (palettes Dracula & co).

---

## Fonctionnalités

- 🔎 **Recherche** live sur les répliques (titre, personnage, épisode).
- 🎭 **Filtre par personnage** (puces triées par fréquence).
- ⭐ **Favoris** par pack, mémorisés dans le navigateur (`localStorage`).
- 🔊 **Volume** + bouton **Stop** global (raccourci `Échap`).
- 🎨 **Sélecteur de thème** : 16 variantes ThemeForge, appliquées à chaud.
- 📦 **Multi-pack** : chaque pack a son manifeste et son thème par défaut.

Raccourcis clavier : `/` pour aller à la recherche, `Échap` pour stopper le son.

---

## Lancer en local

Le site doit être servi en HTTP (les `fetch()` JSON ne marchent pas en
`file://`) :

```bash
python3 -m http.server 8000
# puis ouvrir http://localhost:8000
```

## Déployer sur GitHub Pages

Deux options :

1. **Automatique** — le workflow `.github/workflows/pages.yml` déploie à chaque
   push sur `main`. Dans *Settings → Pages*, choisir la source **GitHub Actions**.
2. **Manuel** — *Settings → Pages*, source **Deploy from a branch**, brancher
   sur `main` / racine. Le fichier `.nojekyll` est déjà présent.

---

## Structure du dépôt

```
SoundBoard/
├── index.html                  Page unique
├── assets/
│   ├── css/app.css             Styles (couleurs = variables CSS injectées)
│   ├── js/app.js               Logique de l'app
│   └── data/
│       ├── themes.json         Les 16 palettes ThemeForge (généré)
│       └── packs.json          Index des packs disponibles (généré)
├── packs/
│   └── kaamelott/pack.json     Manifeste du pack (sons + métadonnées) (généré)
├── sounds/                     Fichiers .mp3
├── tools/
│   ├── sb_lib.py               Helpers partagés (registre, build pack, upsert)
│   ├── import_pack.py          Importe un pack (repo 2ec0b4 / JSON / CSV)
│   ├── build_data.py           Génère themes.json + pack Kaamelott
│   └── download_sounds.py      Télécharge les .mp3 depuis le registre
├── config.json                 URL du registre + dossier de sortie
├── LICENSE                     Apache 2.0 (code)
└── NOTICE                      Attributions (palettes, clips audio)
```

> Les fichiers marqués *(généré)* sont produits par `tools/build_data.py`.
> Ne pas les éditer à la main.

---

## Ajouter un nouveau pack (Star Wars, etc.)

Tout passe par `tools/import_pack.py`. Les sons d'un pack vivent sous
`sounds/<pack-id>/` et `packs.json` est mis à jour sans écraser les packs
existants.

**Cas 1 — un soundboard GitHub au format 2ec0b4** (un `sounds/sounds.json` +
les `.mp3` à côté). L'outil télécharge tout et génère le pack :

```bash
python3 tools/import_pack.py --from-repo owner/nom-du-repo \
  --pack-id monpack --pack-name "Mon Pack" --default-theme drakul
```

**Cas 2 — tes propres MP3 + un CSV.** Dépose les `.mp3` dans
`sounds/<pack-id>/`, prépare un CSV `file,title,character,episode` puis :

```bash
python3 tools/import_pack.py --from-csv registre.csv --no-download \
  --pack-id starwars --pack-name "Star Wars" --default-theme cinder
```

**Cas 3 — un `sounds.json` distant ou local** (même format que Kaamelott) :

```bash
python3 tools/import_pack.py --from-json https://.../sounds.json \
  --sounds-url https://.../ --pack-id monpack --pack-name "Mon Pack"
```

Options utiles : `--sounds-base` (préfixe web, défaut `sounds/<pack-id>/`),
`--branch` (pour `--from-repo`, défaut `master`), `--no-download` (n'aller
chercher aucun fichier). Le pack apparaît ensuite dans le sélecteur **Pack**.

## Régénérer les thèmes / le pack Kaamelott

```bash
python3 tools/build_data.py \
  --registry registre_kaamelott.json \
  --default-theme drakul
```

Le script lit automatiquement les variantes ThemeForge dans
`../ThemeForge/src/ThemeForge.Theme/Themes/` (override possible via
`--themes-dir`).

---

## Thèmes

| Famille | Variantes |
|---|---|
| Sombres | Dracula, Drakul, Cinder, Mortis, Slate, Tarn, Vesper, Voivode, Wormwood, Striga, Bracken… |
| Clairs | Parchment, Folio, Whitby, Sconce, Carmilla… |

Le thème **Drakul** (variante Dracula conforme WCAG AA) est le défaut du pack
Kaamelott. Le choix de l'utilisateur est mémorisé et prioritaire sur le défaut
du pack.

---

## Licence & attributions

Code sous **Apache 2.0** (`LICENSE`). Les clips audio Kaamelott appartiennent à
leurs ayants droit (CALT / Alexandre Astier) et sont inclus pour un usage
personnel non commercial. Voir `NOTICE` pour le détail.
