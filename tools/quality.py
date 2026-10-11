"""Raise Unity's quality presets (the game boots on "Fastest": LOD bias 0.3, per-texture filtering).

Every preset gets LOD bias >= MIN_LOD_BIAS (models keep their detailed meshes further from the camera).
Shadows and anti-aliasing are left as shipped (the toon shader draws its own shading; the game's options
menu controls AA).

Anisotropic filtering is left as shipped too: forcing it on made thin coloured lines appear along
character outlines and polygon edges, apparently from the toon shader's ramp/matcap lookups.
"""
MIN_LOD_BIAS = 2.0
FORCE_ANISO = None  # 2 = AnisotropicFiltering.ForceEnable; None = keep each preset's own setting


def apply(path, log=print):
    import UnityPy
    env = UnityPy.load(path)
    for obj in env.objects:
        if obj.type.name == "QualitySettings":
            tree = obj.read_typetree()
            for q in tree["m_QualitySettings"]:
                q["lodBias"] = max(q["lodBias"], MIN_LOD_BIAS)
                if FORCE_ANISO is not None:
                    q["anisotropicTextures"] = FORCE_ANISO
            obj.save_typetree(tree)
            log(f"quality: {len(tree['m_QualitySettings'])} presets -> LOD bias >= {MIN_LOD_BIAS}"
                + (", anisotropic forced on" if FORCE_ANISO is not None else ""))
            return env.file.save()
    return None
