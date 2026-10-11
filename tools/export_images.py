"""Export the tutorial textures from your own copy of the game to images/ja/ (input for image_tl.py)."""
import glob, os

import UnityPy

PATCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.abspath(os.path.join(PATCH, ".."))
ORIG = f"{PATCH}/original"

name = os.path.basename(glob.glob(f"{GAME}/danchro_Data/StreamingAssets/aa/StandaloneWindows64/ui_textures_tutorial_assets_all_*.bundle")[0])
# prefer the untouched backup: once the patch is installed, the live bundle holds English images
src = f"{ORIG}/{name}" if os.path.exists(f"{ORIG}/{name}") else f"{GAME}/danchro_Data/StreamingAssets/aa/StandaloneWindows64/{name}"
os.makedirs(f"{PATCH}/images/ja", exist_ok=True)
n = 0
for obj in UnityPy.load(src).objects:
    if obj.type.name == "Texture2D":
        tex = obj.read()
        tex.image.save(f"{PATCH}/images/ja/{tex.m_Name}.png")
        n += 1
print(f"exported {n} textures from {os.path.relpath(src, GAME)} to images/ja/")
