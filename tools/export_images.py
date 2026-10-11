"""Export the textures the patch redraws from your own copy of the game (inputs for image_tl.py).

  images/ja/              tutorial images
  images/honor/ja/        honor plates
  images/extra/ja/        other textures named in images/extra/spec (<bundle prefix>__<texture name>.png)
"""
import glob, json, os, re, sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from images_bundle import safe_name

PATCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.abspath(os.path.join(PATCH, ".."))
BUNDLES = f"{GAME}/danchro_Data/StreamingAssets/aa/StandaloneWindows64"


def source(prefix):
    """Untouched copy of a bundle: the backup in original/ once the patch is installed, else the live file."""
    pattern = re.compile(re.escape(prefix) + r"_[0-9a-f]{32}\.bundle$")
    name = next(os.path.basename(p) for p in glob.glob(f"{BUNDLES}/{prefix}_*.bundle") if pattern.search(p))
    orig = f"{PATCH}/original/{name}"
    return orig if os.path.exists(orig) else f"{BUNDLES}/{name}"


def export(prefix, out_dir, wanted=None, tag=""):
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for obj in UnityPy.load(source(prefix)).objects:
        if obj.type.name == "Texture2D":
            tex = obj.read()
            name = safe_name(tex.m_Name)
            if wanted is None or name in wanted:
                tex.image.save(f"{out_dir}/{tag}{name}.png"); n += 1
    return n


print("tutorial:", export("ui_textures_tutorial_assets_all", f"{PATCH}/images/ja"))
print("honor plates:", export("honor_image_assets_all", f"{PATCH}/images/honor/ja"))
# textures rebuilt by tools/fx_text_gen.py instead of a spec
FX = {"fx_003_0011_assets_all": {"ET_003_0011_07_TextMap", "ET_003_0011_07_TextMapC", "ET_003_0011_07_TextMask",
                                  "ET_003_0011_09_Text"}}
specs = {}
for f in glob.glob(f"{PATCH}/images/extra/spec/*.json"):
    specs.update(json.load(open(f)))
extra = 0
for prefix in json.load(open(f"{PATCH}/images/extra/bundles.json")):
    wanted = {k.split("__", 1)[1] for k in specs if k.startswith(prefix + "__")} | FX.get(prefix, set())
    extra += export(prefix, f"{PATCH}/images/extra/ja", wanted, tag=f"{prefix}__")
print("other textures:", extra)
