"""Build translations/terms_index.tsv (ja<TAB>en) from finished terms batches + glossary names.

Translators grep this file so skill/item/card names stay identical everywhere: grep -F '<japanese>' translations/terms_index.tsv
"""
import glob, json, os, csv

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
rows = {}
names_tsv = {r["key"]: r["ja"] for r in csv.DictReader(open(f"{ROOT}/pilot/names.tsv"), delimiter="\t", quoting=csv.QUOTE_NONE)}
for k, en in json.load(open(f"{ROOT}/pilot/names_en.json")).items():
    if names_tsv.get(k):
        rows[names_tsv[k].replace("\\n", " ")] = en.replace("\n", " ")
for f in sorted(glob.glob(f"{ROOT}/batches/terms_*.json")):
    out_path = f"{ROOT}/translations/{os.path.basename(f)}"
    if not os.path.exists(out_path):
        print("missing", out_path); continue
    out = json.load(open(out_path))
    for item in json.load(open(f)):
        if item["id"] in out:
            rows[item["ja"].replace("\n", " ")] = out[item["id"]].replace("\n", " ")
with open(f"{ROOT}/translations/terms_index.tsv", "w") as fh:
    for ja, en in sorted(rows.items(), key=lambda r: (-len(r[0]), r[0])):
        fh.write(f"{ja}\t{en}\n")
print(len(rows), "terms indexed")
