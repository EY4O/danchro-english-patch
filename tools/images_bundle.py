"""Swap translated images into a bundle.

images/en/<texture name>.png          tutorial images (ui_textures_tutorial bundle)
images/honor/en/<texture name>.png    honor plates (honor_image bundle)
images/extra/en/<bundle prefix>__<texture name>.png   everything else (see images/extra/bundles.json)
"""
import glob, os

PATCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.join(PATCH, "images", "en")


def safe_name(name):
    """Texture name as used for PNG files (atlas names contain "|", e.g. sactx-0-...-DXT5|BC3-...)."""
    return name.replace("|", "_").replace("/", "_")


def apply(bundle_path, en_dir=ROOT, prefix=None, log=print):
    """Return the bundle bytes with translated textures, or None if there is nothing to swap."""
    import UnityPy
    from PIL import Image
    tag = f"{prefix}__" if prefix else ""
    done = {os.path.basename(p)[len(tag):-4]: p for p in glob.glob(f"{en_dir}/{tag}*.png")}
    if not done:
        return None
    env = UnityPy.load(bundle_path)
    n = 0
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        tex = obj.read()
        name = safe_name(tex.m_Name)
        if name in done:
            img = Image.open(done[name]).convert("RGBA")
            assert img.size == (tex.m_Width, tex.m_Height), tex.m_Name
            tex.set_image(img, target_format=tex.m_TextureFormat, mipmap_count=tex.m_MipCount)
            tex.save(); n += 1
    label = prefix or os.path.relpath(os.path.dirname(en_dir.rstrip("/")), PATCH)  # images, images/honor
    log(f"images: {label}: {n} textures swapped in")
    return env.file.save(packer="lz4") if n else None
