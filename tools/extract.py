"""Dump every translatable string to source/strings_ja.json and build story scripts."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from masterdata import MasterData

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUNDLE = glob.glob(f"{ROOT}/danchro_Data/StreamingAssets/aa/StandaloneWindows64/master_assets_all_*.bundle")[0]
OUT = os.path.join(os.path.dirname(__file__), "..", "source")

md = MasterData.from_bundle(BUNDLE)
strings = {r["Dictkey"]: r["ContentJa"] for r in md.table("m_dictionary")}
ui = {r["Key"]: r["Text"] for r in md.table("string_master")}
json.dump({"m_dictionary": strings, "string_master": ui}, open(f"{OUT}/strings_ja.json", "w"),
          ensure_ascii=False, indent=1)

# Story scripts: ordered lines with resolved speaker name keys.
visual = {v["Id"]: v["Name"] for v in md.table("m_character_visual")}
scripts = {}
for r in sorted(md.table("m_character_theater"), key=lambda r: r["Id"]):
    key = r["WindowText"]
    if not key:
        continue
    ids = [int(i) for i in str(r["NarratorVisualId"] or "").split("&") if i.strip().isdigit()]
    spk = "&".join(visual.get(i, "") for i in ids)
    scripts.setdefault(str(r["TheaterId"]), []).append({"key": key, "speaker": spk})
json.dump(scripts, open(f"{OUT}/theater_scripts.json", "w"), ensure_ascii=False, indent=1)
print(len(strings), "dictionary,", len(ui), "ui,", len(scripts), "scenes")
