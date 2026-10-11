"""Split untranslated strings into batch files under batches/.

terms_NN.json  : short proper-noun strings (skill/item/card/event names), deduped by text
ui_NN.json     : all other non-story strings, deduped by text
story_NN.json  : story lines in scene order with English speaker names
Each batch is a list of {"id", "ja", ...context}. Translators write translations/<batch>.json = {id: en}.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
JP = re.compile(r"[぀-ヿ一-鿿]")
TARGET = 24000  # Japanese characters per batch

src = json.load(open(f"{ROOT}/source/strings_ja.json"))["m_dictionary"]
scripts = json.load(open(f"{ROOT}/source/theater_scripts.json"))
names_en = json.load(open(f"{ROOT}/pilot/names_en.json"))
done = set(json.load(open(f"{ROOT}/pilot/story_01_01_en.json"))) | set(names_en)

todo = {k: v for k, v in src.items() if k not in done and v and JP.search(v)}
story = {k: v for k, v in todo.items() if k.startswith("theater_")}
other = {k: v for k, v in todo.items() if k not in story}
is_term = lambda k, v: re.search(r"(^|_)(name|title)(_|$)", k.lower()) and "description" not in k.lower() and len(v) <= 40


def chunk(items, size_of):
    out, cur, n = [], [], 0
    for it in items:
        if cur and n + size_of(it) > TARGET:
            out.append(cur); cur, n = [], 0
        cur.append(it); n += size_of(it)
    return out + ([cur] if cur else [])


def dedupe(pairs):
    by_text = {}
    for k, v in sorted(pairs):
        by_text.setdefault(v, []).append(k)
    return [{"id": f"t{i}", "ja": v, "keys": ks[:3], "count": len(ks), "_all": ks}
            for i, (v, ks) in enumerate(by_text.items())]


manifest = {}
def write(prefix, batches, strip_all=True):
    for i, b in enumerate(batches):
        name = f"{prefix}_{i:02d}"
        manifest[name] = {x["id"]: x.get("_all", [x["id"]]) for x in b}
        json.dump([{k: v for k, v in x.items() if k != "_all"} for x in b],
                  open(f"{ROOT}/batches/{name}.json", "w"), ensure_ascii=False, indent=0)
    print(prefix, len(batches), "batches", sum(map(len, batches)), "items")


terms = dedupe([(k, v) for k, v in other.items() if is_term(k, v)])
for i, t in enumerate(terms): t["id"] = f"n{i}"
ui = dedupe([(k, v) for k, v in other.items() if not is_term(k, v)])
write("terms", chunk(terms, lambda x: len(x["ja"]) * 3))  # names are short: smaller batches
write("ui", chunk(ui, lambda x: len(x["ja"])))

# Story: scene order from theater scripts, then any remaining keys in key order.
speaker = {}
for lines in scripts.values():
    for l in lines:
        speaker[l["key"]] = " & ".join(names_en.get(s, s) for s in l["speaker"].split("&") if s)
ordered = [l["key"] for sid in sorted(scripts, key=int) for l in scripts[sid] if l["key"] in story]
seen = set(); keys = []
for k in ordered + sorted(story):
    if k not in seen:
        seen.add(k); keys.append(k)
scene = lambda k: "_".join(k.split("_")[:-1])
items = [{"id": k, "scene": scene(k), "speaker": speaker.get(k, ""), "ja": story[k]} for k in keys]
# keep whole scenes together
groups, cur = [], []
for it in items:
    if cur and it["scene"] != cur[-1]["scene"]:
        groups.append(cur); cur = []
    cur.append(it)
groups.append(cur)
batches, b, n = [], [], 0
for g in groups:
    size = sum(len(x["ja"]) for x in g)
    if b and n + size > TARGET:
        batches.append(b); b, n = [], 0
    b += g; n += size
batches.append(b)
write("story", batches)
json.dump(manifest, open(f"{ROOT}/batches/manifest.json", "w"))
