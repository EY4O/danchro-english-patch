"""Japanese text typed directly into UI layouts (uGUI Text / LocalizeText m_Text, TextMeshPro m_text).

The game's LocalizeText components normally swap in a dictionary string at runtime, so most of this
text never shows; components without a dictionary key do show it (e.g. the quest panel's 初回報酬).
Replacing the layout text with English covers both cases.

usage:
  ui_text.py scan    -> source/ui_text_ja.json  {ja: {"count", "where": ["bundle-prefix:GameObject", ...]}}
                        and translations/ui_text_bundles.json (bundle prefixes that contain such text)
translations/ui_text.json holds the English: {ja: en}.  apply() is used by build_patch.py.
"""
import glob, json, os, re, sys

PATCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.abspath(os.path.join(PATCH, ".."))
BUNDLES = f"{GAME}/danchro_Data/StreamingAssets/aa/StandaloneWindows64"
JP = re.compile(r"[぀-ヿ一-鿿]")
FIELDS = ("m_Text", "m_text")
SKIP = re.compile(r"^(chara_|sound_|stage_|movie_|adv_animcut|adv_background|fx_|skill_|world_|"
                  r"mycharacter_charactertexture|cridata|home_banner|quest_dungeon_topimage|master_assets)")


def prefix(bundle_name):
    """Bundle name without its content hash, stable across builds: ui_windows_assets_all"""
    return re.sub(r"_[0-9a-f]{32}\.bundle$", "", bundle_name)


def _texts(env):
    """Yield (object, typetree, field, text) for every UI text component holding Japanese."""
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            raw = obj.get_raw_data()
            if not JP.search(raw.decode("utf-8", "ignore")):
                continue
            tree = obj.read_typetree()
        except Exception:
            continue
        for field in FIELDS:
            value = tree.get(field)
            if isinstance(value, str) and JP.search(value):
                yield obj, tree, field, value


def scan():
    import UnityPy
    found, bundles = {}, set()
    for path in sorted(glob.glob(f"{BUNDLES}/*.bundle")):
        name = os.path.basename(path)
        if SKIP.match(name):
            continue
        env = UnityPy.load(path)
        names = {o.path_id: o for o in env.objects if o.type.name == "GameObject"}
        for obj, tree, field, text in _texts(env):
            go = names.get(tree.get("m_GameObject", {}).get("m_PathID"))
            go_name = go.read().m_Name if go else "?"
            entry = found.setdefault(text, {"count": 0, "where": []})
            entry["count"] += 1
            where = f"{prefix(name)}:{go_name}"
            if where not in entry["where"] and len(entry["where"]) < 6:
                entry["where"].append(where)
            bundles.add(prefix(name))
    os.makedirs(f"{PATCH}/source", exist_ok=True)
    json.dump(found, open(f"{PATCH}/source/ui_text_ja.json", "w"), ensure_ascii=False, indent=1)
    json.dump(sorted(bundles), open(f"{PATCH}/translations/ui_text_bundles.json", "w"), indent=1)
    print(f"{len(found)} unique strings, {sum(e['count'] for e in found.values())} components, {len(bundles)} bundles")


def apply(bundle_path, en, log=print):
    """Return the bundle with layout text replaced by English, or None if nothing changed."""
    import UnityPy
    env = UnityPy.load(bundle_path)
    n = 0
    for obj, tree, field, text in list(_texts(env)):
        if text in en and en[text] != text:
            tree[field] = en[text]
            obj.save_typetree(tree)
            n += 1
    if not n:
        return None
    log(f"ui text: {prefix(os.path.basename(bundle_path))}: {n} components")
    return env.file.save(packer="lz4")


if __name__ == "__main__":
    if sys.argv[1:] == ["scan"]:
        scan()
    else:
        sys.exit(__doc__)
