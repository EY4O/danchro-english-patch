"""Merge English JSON files (key -> text) into the MasterData blob.

usage: apply_translation.py OUT_BLOB translations/*.json
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from masterdata import MasterData, rebuild

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUNDLE = glob.glob(f"{ROOT}/danchro_Data/StreamingAssets/aa/StandaloneWindows64/master_assets_all_*.bundle")[0]

out_path, files = sys.argv[1], sys.argv[2:]
en = {}
for f in files:
    en.update(json.load(open(f)))

md = MasterData.from_bundle(BUNDLE)
dictionary = md.table("m_dictionary")
ui = md.table("string_master")
hits = 0
for r in dictionary:
    if r["Dictkey"] in en:
        r["ContentJa"] = en[r["Dictkey"]]; hits += 1
for r in ui:
    if r["Key"] in en:
        r["Text"] = en[r["Key"]]; hits += 1
blob = rebuild(md, {"m_dictionary": dictionary, "string_master": ui})

check = MasterData(blob)  # round-trip sanity check
assert check.table("m_dictionary") == dictionary and check.table("string_master") == ui
for name in md.header:
    if name not in ("m_dictionary", "string_master"):
        assert check.table(name) == md.table(name), name
open(out_path, "wb").write(blob)
print(f"applied {hits}/{len(en)} strings -> {out_path} ({len(blob)} bytes)")
