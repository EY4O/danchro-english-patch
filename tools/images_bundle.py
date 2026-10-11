"""Swap translated tutorial images (images/en/*.png) into the tutorial texture bundle."""
import glob, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images", "en")


def apply(bundle_path, log=print):
    """Return the bundle bytes with translated textures, or None if there is nothing to swap."""
    import UnityPy
    from PIL import Image
    done = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(f"{ROOT}/*.png")}
    if not done:
        return None
    env = UnityPy.load(bundle_path)
    n = 0
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        tex = obj.read()
        if tex.m_Name in done:
            img = Image.open(done[tex.m_Name]).convert("RGBA")
            assert img.size == (tex.m_Width, tex.m_Height), tex.m_Name
            tex.set_image(img, target_format=tex.m_TextureFormat, mipmap_count=tex.m_MipCount)
            tex.save(); n += 1
    log(f"tutorial images: {n} translated textures swapped in")
    return env.file.save(packer="lz4") if n else None
