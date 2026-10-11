# DanChro English Patch

An unofficial English patch for the **offline edition** of *DanMachi Battle Chronicle* (ダンクロ), the version Aiming released after the online service ended on September 29, 2025. The offline edition runs entirely on your computer, but it is Japanese only.

**Download the patch from [Releases](../../releases).** This repository holds the tools and the English text used to build it.

## What it changes

The installer offers two versions:

| | Full | Translation only |
|---|---|---|
| All game text in English: about 56,000 strings of story, menus, skills, items and missions | ✓ | ✓ |
| English text in the 57 tutorial images | ✓ | ✓ |
| Sound fix for Wine (Mac/Linux) | ✓ | ✓ |
| Fairer gacha: 5 exchange tokens per pull (a ten-pull earns any character of your choice); top-rarity rate 2.5% → 7.5% | ✓ | |
| Story first clears pay 150 / 300 / 500 crystals (normal / hard / very hard), up from 30 / 100 / 0 | ✓ | |
| Double EXP, gold and upgrade-material drops from quests | ✓ | |
| Smarter auto-battle: healing skills and assists wait until someone is below 70% HP | ✓ | |
| Models keep full detail further from the camera | ✓ | |

Names and terms follow the official Yen Press English release (Bell Cranel, Ais Wallenstein, Falna, Loki Familia…), see [glossary.md](glossary.md).

**How the translation was made:** the text was translated with AI (Claude) against that glossary, checked automatically for broken formatting, and spot-checked against the Japanese in play. It reads naturally but it is not a professional human translation. Corrections are welcome, see [Contributing](#contributing).

## Install

1. You need the offline edition of the PC game (October 2025 build). The installer checks the files and won't touch any other version.
2. Close the game. Put the unzipped `DanChro-English-Patch` folder inside the game folder, next to `danchro.exe`.
3. Run `install-windows.bat` (Windows) or `install-mac.command` (macOS, right-click > Open the first time) and choose 1 (full) or 2 (translation only).

The original files are backed up inside the patch folder; `uninstall-…` restores them. Run the installer again to switch versions. Save data is never touched.

### Playing on a Mac

The game is a Windows program. It runs well on Apple Silicon with:

1. Rosetta 2: `softwareupdate --install-rosetta --agree-to-license`
2. [Gcenx's Wine Staging](https://github.com/Gcenx/macOS_Wine_builds) (11.18 tested)
3. [DXVK-macOS](https://github.com/Gcenx/DXVK-macOS), the `-repack-builtin` package. Copy its `d3d11.dll` and `d3d10core.dll` over the ones in `Wine Staging.app/Contents/Resources/wine/lib/wine/x86_64-windows/` (and `i386-windows/`). Without this the game stops with "Failed to initialize graphics".
4. Start it from the game folder: `"/path/to/Wine Staging.app/Contents/Resources/wine/bin/wine" danchro.exe -screen-fullscreen 1`

The game's Screen Size option tops out at 1920×1080. For native resolution, add `-screen-width` and `-screen-height` with your display's pixel size.

## Known issues

- A few stylized logos in tutorial images are still Japanese, and some glowing banners became plain text.
- English runs longer than Japanese; if text overflows a button or box somewhere, please open an issue with a screenshot.

## Building it yourself

The repository contains no game files. You build the patch from your own copy of the game:

```bash
# clone this repo into the game folder as "english-patch" (next to danchro.exe)
cd english-patch
python3 -m venv .venv
.venv/bin/pip install UnityPy msgpack lz4 numpy
.venv/bin/python tools/export_images.py          # tutorial textures -> images/ja/
.venv/bin/python tools/image_tl.py render        # English tutorial images -> images/en/
.venv/bin/python tools/build_patch.py build      # patched files -> out/ (backs up originals to original/)
.venv/bin/python tools/build_patch.py install    # or: package -> dist/DanChro-English-Patch.zip
```

`build` options: `--no-gameplay`, `--no-ai`, `--no-images`, `--no-quality`, `--no-audio`. `uninstall` restores the original files.

### How it works

| File | Role |
|---|---|
| `tools/masterdata.py` | Reads and rebuilds the game's MasterMemory database (MessagePack, LZ4 per table), where all text lives |
| `tools/build_patch.py` | Applies everything, rewrites the bundles, zeroes their CRCs in the Addressables catalog, installs/packages |
| `tools/gameplay.py` | Gacha, crystal and grind tuning; constants at the top |
| `tools/ai.py` | Adds "only heal when hurt" guards to the auto-battle behaviour trees |
| `tools/quality.py`, `tools/audio.py` | Detail preset; CRIWARE spatial-audio flag that breaks sound under Wine |
| `tools/image_tl.py`, `tools/ocr/ocr.swift` | Tutorial image translation: OCR boxes, erase, redraw in the game's style |
| `translations/*.json`, `batches/manifest.json` | The English text; the manifest maps each entry to the game's dictionary keys |
| `images/text_en.json`, `images/spec/` | English text and layout for each tutorial image |
| `tools/check_batch.py`, `tools/normalize_terms.py` | Validation (placeholders, tags, leftover Japanese) and term consistency |

## Contributing

To fix a line, search `translations/` for the English text, edit it, and open a pull request. Keep `{placeholders}` and `<color>` tags exactly as they are. `tools/check_batch.py <batch>` validates a file if you have the game's source text extracted (`tools/extract.py`, then `tools/make_batches.py`).

## Disclaimer

Unofficial fan project, not affiliated with Aiming, Fujino Ōmori, SB Creative or the other DanMachi rights holders. It does not include or help you obtain the game.
