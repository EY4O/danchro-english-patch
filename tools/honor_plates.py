"""Honor plates (profile title banners, HI_*.png in honor_image_assets_all) in English.

The English title of every plate is already in the translation (honor_master.Name -> dictionary key),
so the spec is generated, not hand-written:
  - a text block that reads like the plate's full Japanese title -> the English title ("plate" style)
  - a rank fragment on event-logo plates (1位, 10傑, TOP10000)    -> "1st", "Top 10", "Top 10000"
  - anything else (logo art)                                     -> left alone

usage: honor_plates.py export | ocr | spec      (then: IMG_ROOT=images/honor image_tl.py render)
"""
import difflib, glob, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PATCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.abspath(os.path.join(PATCH, ".."))
ROOT = f"{PATCH}/images/honor"
JP = re.compile(r"[぀-ヿ一-鿿]")


def bundle_path():
    name = os.path.basename(glob.glob(f"{GAME}/danchro_Data/StreamingAssets/aa/StandaloneWindows64/honor_image_assets_all_*.bundle")[0])
    orig = f"{PATCH}/original/{name}"
    return orig if os.path.exists(orig) else f"{GAME}/danchro_Data/StreamingAssets/aa/StandaloneWindows64/{name}"


def export():
    import UnityPy
    os.makedirs(f"{ROOT}/ja", exist_ok=True)
    n = 0
    for obj in UnityPy.load(bundle_path()).objects:
        if obj.type.name == "Texture2D":
            tex = obj.read()
            tex.image.save(f"{ROOT}/ja/{tex.m_Name}.png"); n += 1
    print(f"exported {n} plates")


def ocr():
    files = sorted(glob.glob(f"{ROOT}/ja/*.png"))
    result = {}
    for i in range(0, len(files), 300):  # chunked: one call per 300 files
        out = subprocess.run([f"{PATCH}/tools/ocr/ocr", *files[i:i + 300]], capture_output=True, text=True).stdout
        result.update(json.loads(out))
    json.dump(result, open(f"{ROOT}/ocr.json", "w"), ensure_ascii=False, indent=0)
    print(f"ocr: {len(result)} plates")


def rank_fragment(text):
    t = text.replace(" ", "").replace("　", "")
    if m := re.fullmatch(r".*?(\d+)位", t):
        n = int(m.group(1))
        suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"
    if m := re.fullmatch(r".*?(\d+)傑", t):
        return f"Top {m.group(1)}"
    if m := re.fullmatch(r".*?TOP(\d+)", t, re.I):
        return f"Top {m.group(1)}"
    return None


def spec():
    from masterdata import MasterData
    import build_patch as bp
    md = MasterData.from_bundle(glob.glob(f"{PATCH}/original/master_assets_all_*.bundle")[0])
    ja = {r["Dictkey"]: r["ContentJa"] for r in md.table("m_dictionary")}
    en = bp.collect_translations()
    title = {r["HonorIconResourceId"]: r["Name"] for r in md.table("honor_master")}
    ocr_boxes = json.load(open(f"{ROOT}/ocr.json"))
    out, stats = {}, {"title": 0, "rank": 0, "kept": 0}
    for fname, blocks in sorted(ocr_boxes.items()):
        plate = fname[:-4]
        key = title.get(plate)
        name_ja = re.sub(r"\s", "", ja.get(key) or "")
        items = []
        jp = [b for b in blocks if JP.search(b["text"]) and b["conf"] >= 0.5]
        joined = re.sub(r"\s", "", "".join(b["text"] for b in sorted(jp, key=lambda b: b["y"])))
        similar = difflib.SequenceMatcher(None, joined, name_ja).ratio() if name_ja and jp else 0
        if similar >= 0.6 and key in en:
            # the title (possibly on two lines): erase every Japanese block, draw the English once over their union
            x0, y0 = min(b["x"] for b in jp), min(b["y"] for b in jp)
            x1, y1 = max(b["x"] + b["w"] for b in jp), max(b["y"] + b["h"] for b in jp)
            missing = len(name_ja) - len(joined)
            if missing > 0:  # OCR caught only part of the title: widen leftwards by the missing characters
                x0 = max(0, x0 - missing * (x1 - x0) / max(len(joined), 1))
                jp = [dict(b, x=x0, w=b["x"] + b["w"] - x0) if b["x"] == min(o["x"] for o in jp) else b for b in jp]
            right = [o["x"] for o in blocks if o not in jp and o["x"] >= x1 - 2]  # badges like "S3" to the right
            union = {"x": x0, "y": y0, "w": x1 - x0, "h": min(y1 - y0, max(b["h"] for b in jp) * 1.15)}
            title_en = en[key]
            badges = [o["text"] for o in blocks if o not in jp and o["x"] >= x1 - 2]
            for badge in badges:  # the plate already shows e.g. "S3" as art; don't repeat it
                title_en = re.sub(rf"\s*{re.escape(badge.strip())}$", "", title_en)
            items.append({"ja": "title", "en": title_en, "style": "plate", "box": union, "erase": "none",
                          "max_right": (min(right) - 4) if right else None})
            items += [{"ja": f"erase:{b['text']}", "en": "", "style": "plate", "pad": 6,
                       "box": {k: b[k] for k in ("x", "y", "w", "h")}} for b in jp]  # erase-only entries
            stats["title"] += 1
        else:
            for b in jp:
                if (rank := rank_fragment(b["text"])):
                    items.append({"ja": b["text"], "en": rank, "style": "plate", "max_right": b["x"] + b["w"] + 4})
                    stats["rank"] += 1
                else:
                    stats["kept"] += 1
        for i in items:
            if i.get("max_right") is None:
                i.pop("max_right", None)
        if items:
            out[plate] = items
    json.dump(out, open(f"{ROOT}/text_en.json", "w"), ensure_ascii=False, indent=1)
    print(f"spec: {len(out)} plates; {stats['title']} titles, {stats['rank']} rank labels, {stats['kept']} blocks left as art")


if __name__ == "__main__":
    {"export": export, "ocr": ocr, "spec": spec}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
