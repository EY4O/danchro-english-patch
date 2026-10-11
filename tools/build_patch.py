"""Build the English + rebalance + smarter-auto-battle patch and optionally install it into the game.

usage:
  build_patch.py build [--no-gameplay] [--no-ai] [--no-images] [--no-quality] [--no-audio] [--pilot-only]
                            -> writes every patched file to out/ (flat) + out/files.txt (name -> game path)
  build_patch.py install    -> backs up originals to original/ (once), copies out/ into the game
  build_patch.py uninstall  -> restores the originals
  build_patch.py package    -> dist/DanChro-English-Patch.zip with two variants the installer offers:
                               full (everything) and translation (text + tutorial images only)

Translations are merged in this order (later wins): pilot/*_en.json, translations/*.json (via batches/manifest.json).
"""
import base64, glob, json, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masterdata import MasterData, rebuild

PATCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.abspath(os.path.join(PATCH, ".."))
AA = f"{GAME}/danchro_Data/StreamingAssets/aa"
ORIG, OUT = f"{PATCH}/original", f"{PATCH}/out"
LIVE_CATALOG = f"{AA}/catalog.json"


def _bundle(prefix):
    return os.path.basename(glob.glob(f"{AA}/StandaloneWindows64/{prefix}_*.bundle")[0])


MASTER = _bundle("master_assets_all")
BEHAVIOR = _bundle("battle_behaviortree_assets_all")
TUTORIAL_IMAGES = _bundle("ui_textures_tutorial_assets_all")
BUNDLES = (MASTER, BEHAVIOR, TUTORIAL_IMAGES)
QUALITY = "globalgamemanagers"
AUDIO = "level0"
# every file the patch may replace: flat name -> path relative to the game folder
FILES = {**{b: f"danchro_Data/StreamingAssets/aa/StandaloneWindows64/{b}" for b in BUNDLES},
         "catalog.json": "danchro_Data/StreamingAssets/aa/catalog.json",
         QUALITY: "danchro_Data/globalgamemanagers",
         AUDIO: "danchro_Data/level0"}


def backup_originals():
    os.makedirs(ORIG, exist_ok=True)
    for name, rel in FILES.items():
        dst = f"{ORIG}/{name}"
        if not os.path.exists(dst):
            shutil.copy2(f"{GAME}/{rel}", dst)


def collect_translations(pilot_only=False):
    en = {}
    for f in sorted(glob.glob(f"{PATCH}/pilot/*_en.json")):
        en.update(json.load(open(f)))
    if pilot_only:
        return en
    manifest = json.load(open(f"{PATCH}/batches/manifest.json"))
    missing = []
    for batch, ids in manifest.items():
        path = f"{PATCH}/translations/{batch}.json"
        if not os.path.exists(path):
            missing.append(batch); continue
        out = json.load(open(path))
        for i, keys in ids.items():
            if i in out:
                for k in keys:
                    en[k] = out[i]
    if missing:
        print(f"note: {len(missing)} batches not translated yet: {', '.join(missing)}")
    return en


def patch_catalog(text, bundle_names):
    """Zero the CRC of each modified bundle (it no longer matches) while keeping byte lengths identical."""
    c = json.loads(text)
    extra = bytearray(base64.b64decode(c["m_ExtraDataString"]))
    for name in bundle_names:
        h = re.search(r"_([0-9a-f]{32})\.bundle$", name).group(1)
        at = extra.find(h.encode("utf-16-le"))
        end = extra.find("}".encode("utf-16-le"), at)
        entry = extra[at:end].decode("utf-16-le")
        m = re.search(r'"m_Crc":(\d+)', entry)
        if m.group(1) != "0":
            extra[at:end] = entry.replace(m.group(0), '"m_Crc":0' + " " * (len(m.group(1)) - 1)).encode("utf-16-le")
    c["m_ExtraDataString"] = base64.b64encode(bytes(extra)).decode()
    return json.dumps(c, separators=(",", ":"))


def build_master(gameplay, pilot_only):
    import UnityPy
    md = MasterData.from_bundle(f"{ORIG}/{MASTER}")
    en = collect_translations(pilot_only)
    dictionary, ui = md.table("m_dictionary"), md.table("string_master")
    hits = 0
    for r in dictionary:
        if r["Dictkey"] in en:
            r["ContentJa"] = en[r["Dictkey"]]; hits += 1
    for r in ui:
        if r["Key"] in en:
            r["Text"] = en[r["Key"]]; hits += 1
    print(f"translations: {hits} strings applied")
    changed = {"m_dictionary": dictionary, "string_master": ui}
    if gameplay:
        import gameplay as gp
        changed.update(gp.apply(md))
    blob = rebuild(md, changed)
    check = MasterData(blob)
    for name in md.header:
        assert check.table(name) == (changed[name] if name in changed else md.table(name)), name

    env = UnityPy.load(f"{ORIG}/{MASTER}")
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            data.m_Script = blob.decode("utf-8", "surrogateescape")
            data.save()
    open(f"{OUT}/{MASTER}", "wb").write(env.file.save(packer="lz4"))
    assert MasterData.from_bundle(f"{OUT}/{MASTER}").blob == blob


def build(gameplay=True, smarter_ai=True, pilot_only=False, images=True, quality=True, audio=True):
    backup_originals()
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for b in BUNDLES:  # start clean so a skipped part ships the original file
        shutil.copy2(f"{ORIG}/{b}", f"{OUT}/{b}")
    build_master(gameplay, pilot_only)
    if smarter_ai:
        import ai
        data = ai.apply(f"{ORIG}/{BEHAVIOR}")
        if data:
            open(f"{OUT}/{BEHAVIOR}", "wb").write(data)
    if images:
        import images_bundle
        data = images_bundle.apply(f"{ORIG}/{TUTORIAL_IMAGES}")
        if data:
            open(f"{OUT}/{TUTORIAL_IMAGES}", "wb").write(data)
    modified = [b for b in BUNDLES if open(f"{OUT}/{b}", "rb").read() != open(f"{ORIG}/{b}", "rb").read()]
    for b in BUNDLES:  # unmodified bundles don't need shipping
        if b not in modified:
            os.remove(f"{OUT}/{b}")
    open(f"{OUT}/catalog.json", "w").write(patch_catalog(open(f"{ORIG}/catalog.json").read(), modified))
    if quality:
        import quality as q
        data = q.apply(f"{ORIG}/{QUALITY}")
        if data:
            open(f"{OUT}/{QUALITY}", "wb").write(data)
    if audio:
        import audio as au
        data = au.apply(f"{ORIG}/{AUDIO}", f"{GAME}/danchro_Data/globalgamemanagers.assets")
        if data:
            open(f"{OUT}/{AUDIO}", "wb").write(data)
    shipped = sorted(n for n in FILES if os.path.exists(f"{OUT}/{n}"))
    with open(f"{OUT}/files.txt", "w") as fh:  # read by the installers
        for n in shipped:
            fh.write(f"{n}|{FILES[n]}\n")
    print(f"built out/: {', '.join(shipped)}")


def _shipped():
    return [line.rstrip("\n").split("|") for line in open(f"{OUT}/files.txt") if line.strip()]


def install():
    backup_originals()
    shipped = {n for n, _ in _shipped()}
    for name, rel in FILES.items():  # anything not shipped by this build goes back to the original
        shutil.copy2(f"{OUT}/{name}" if name in shipped else f"{ORIG}/{name}", f"{GAME}/{rel}")
    print(f"installed patch ({len(shipped)} files)")


def uninstall():
    for name, rel in FILES.items():
        shutil.copy2(f"{ORIG}/{name}", f"{GAME}/{rel}")
    print("restored original files")


VARIANTS = {  # name -> build() options
    "full": dict(gameplay=True, smarter_ai=True, images=True, quality=True, audio=True),
    "translation": dict(gameplay=False, smarter_ai=False, images=True, quality=False, audio=True),
}


def package():
    """Build every variant, store files shared by all variants once, and zip with the installers.

    Zip layout: <variant>/ and common/ hold files; files-<variant>.txt lists "src|game path" per variant;
    files-all.txt lists "backup name|game path" for every file any variant touches (for backup/uninstall).
    """
    import hashlib, zipfile
    staged = {}
    for v, opts in VARIANTS.items():
        build(**opts)
        staged[v] = {n: (rel, open(f"{OUT}/{n}", "rb").read()) for n, rel in _shipped()}
    digest = lambda b: hashlib.sha256(b).hexdigest()
    common = {n for n in set.intersection(*(set(f) for f in staged.values()))
              if len({digest(staged[v][n][1]) for v in staged}) == 1}
    name = "DanChro-English-Patch"
    zpath = f"{PATCH}/dist/{name}.zip"
    os.makedirs(os.path.dirname(zpath), exist_ok=True)
    union = {}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for v, files in staged.items():
            lines = []
            for n, (rel, data) in sorted(files.items()):
                src = f"common/{n}" if n in common else f"{v}/{n}"
                if src not in z.namelist() and f"{name}/{src}" not in z.namelist():
                    z.writestr(f"{name}/{src}", data)
                lines.append(f"{src}|{rel}")
                union[n] = rel
            z.writestr(f"{name}/files-{v}.txt", "\n".join(lines) + "\n")
        z.writestr(f"{name}/files-all.txt", "\n".join(f"{n}|{r}" for n, r in sorted(union.items())) + "\n")
        for f in sorted(os.listdir(f"{PATCH}/installer")):
            info = zipfile.ZipInfo.from_file(f"{PATCH}/installer/{f}", f"{name}/{f}")
            if f.endswith(".command"):
                info.external_attr = (0o100755 << 16)  # keep the macOS scripts executable
            z.writestr(info, open(f"{PATCH}/installer/{f}", "rb").read(), zipfile.ZIP_DEFLATED)
    build(**VARIANTS["full"])  # leave out/ holding the full build for local install
    print(f"packaged {zpath} ({os.path.getsize(zpath) // 1024} KB): variants {', '.join(staged)}; "
          f"{len(common)} shared files")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build(gameplay="--no-gameplay" not in sys.argv, smarter_ai="--no-ai" not in sys.argv,
              pilot_only="--pilot-only" in sys.argv, images="--no-images" not in sys.argv,
              quality="--no-quality" not in sys.argv, audio="--no-audio" not in sys.argv)
    elif cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "package":
        package()
    else:
        sys.exit(__doc__)
