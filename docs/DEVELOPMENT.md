# Development

The repository is meant to live inside the game folder as `english-patch/` (next to `danchro.exe`). Every tool finds the game through that location. No game files are committed; the build reads them from your own copy.

```
tools/               build, install and translation tools (Python; tools/ocr is Swift)
translations/        English text, one JSON file per batch: {id: English}
batches/manifest.json  which dictionary keys each translated id fills
pilot/*_en.json      the first hand-checked batch (story chapter 1-1, names)
translations/ui_text.json   English for text typed into screen layouts ({japanese: english})
translations/overrides.json hand-tuned replacements applied last (e.g. STR/END/DEX/MAG)
images/              tutorial images: text_en.json + spec/ (layout per image), ocr.json (text boxes)
images/honor/        honor plates: generated text_en.json, ocr.json
images/extra/        other UI/effect textures: spec/, ocr.json, bundles.json
installer/           install/uninstall scripts and README shipped in the release zip
glossary.md          names and terms (Yen Press English release)
docs/                this file, README images
```

Local only (ignored by git): `original/` backups of the game files, `out/` the built files, `dist/` the release zip, `source/` and `batches/*` the extracted Japanese text, `images/ja` and `images/en`.

## Run it locally

```bash
python3 -m venv .venv
.venv/bin/pip install UnityPy msgpack lz4 numpy
.venv/bin/python tools/export_images.py          # textures to redraw -> images/ja, images/honor/ja, images/extra/ja
.venv/bin/python tools/image_tl.py render        # English tutorial images -> images/en/
IMG_ROOT=images/honor .venv/bin/python tools/image_tl.py render   # honor plates
IMG_ROOT=images/extra .venv/bin/python tools/image_tl.py render   # other textures
.venv/bin/python tools/fx_text_gen.py images/extra/en             # Awakening / Mastery Up effects
.venv/bin/python tools/build_patch.py build      # -> out/, backs up originals to original/ on first run
.venv/bin/python tools/build_patch.py install    # copy out/ into the game (uninstall restores)
```

`build` options switch parts off: `--no-gameplay`, `--no-ai`, `--no-images`, `--no-quality`, `--no-audio`, `--pilot-only`.

## Translation workflow

1. `tools/extract.py` dumps every dictionary string and story script from the game to `source/`.
2. `tools/make_batches.py` splits all text outside `pilot/` into batches (`terms_*` names first, `ui_*` deduplicated, `story_*` whole scenes in order) and writes `batches/manifest.json`. Batch ids are stable for the same game data.
3. Translate a batch into `translations/<batch>.json`. For names, use `glossary.md` and `translations/terms_index.tsv` (built by `tools/build_terms_index.py`).
4. `tools/check_batch.py <batch>` must report 0 errors: every id present, `{placeholders}` and `<color>`/`<size>` tags unchanged, no Japanese left.
5. `tools/normalize_terms.py` unifies names that different batches rendered differently.

## Tutorial images

1. `tools/ocr/ocr.swift` (macOS, Apple Vision) finds Japanese text boxes: `swiftc -O tools/ocr/ocr.swift -o tools/ocr/ocr && tools/ocr/ocr images/ja/*.png > images/ocr.json`.
2. Each image gets a spec in `images/text_en.json` or `images/spec/*.json`: style `headline` (game-style white/orange text, `*emphasis*`), `ui` (plain text in the sampled colour) or `keep`, with optional `size`, `color`, `dx`/`dy`, `erase` and `box` overrides. See the docstring in `tools/image_tl.py`.
3. `tools/image_tl.py render [names]`, then compare `images/en/` against `images/ja/` by eye.

## Layout text

1. `tools/ui_text.py scan` lists every Japanese string in uGUI/TextMeshPro text components across the bundles (`source/ui_text_ja.json`, with the GameObject names as context) and writes `translations/ui_text_bundles.json`.
2. Translate into `translations/ui_text.json`; `tools/check_ui_text.py` must report 0 errors (it also warns when English is much longer than the box was designed for).
3. `build` writes the English into every matching component.

## Honor plates and other images

- Honor plates: `tools/honor_plates.py export`, `ocr`, `spec`, then `IMG_ROOT=images/honor .venv/bin/python tools/image_tl.py render`. The spec is generated from the translated honor names; edit `images/honor/text_en.json` for one-off fixes.
- Other textures: export them as `images/extra/ja/<bundle prefix>__<texture name>.png` (listed in `images/extra/bundles.json`), write specs in `images/extra/spec/`, then `IMG_ROOT=images/extra .venv/bin/python tools/image_tl.py render`. The Awakening / Mastery Up effect textures are shader masks; `tools/fx_text_gen.py images/extra/en` rebuilds them.
- Re-rendering can differ slightly from the released images, because the erase fill has improved since the tutorial images were made; review before shipping.

## Releasing

1. Close the game, then `.venv/bin/python tools/build_patch.py package`. This builds both variants (full and translation-only) into `dist/DanChro-English-Patch.zip`.
2. Test the installers on a copy of the game folder.
3. Commit and push, then `gh release create vX.Y.Z dist/DanChro-English-Patch.zip --title "DanChro English Patch vX.Y.Z"`.
