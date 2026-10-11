"""Validate translations/<batch>.json against batches/<batch>.json.

usage: python3 tools/check_batch.py story_03
Errors (exit 1): missing/extra ids, non-string values, lost or added {placeholders} / <color>/<size> tags,
Japanese kana/kanji left in the English. Warnings: story lines over 52 chars or more than 3 lines.
"""
import collections, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JP = re.compile(r"[぀-ヿ一-鿿]")
TOKENS = re.compile(r"\{[^{}]*\}|</?(?:color|size)[^>]*>")

name = sys.argv[1]
src = {x["id"]: x for x in json.load(open(f"{ROOT}/batches/{name}.json"))}
try:
    out = json.load(open(f"{ROOT}/translations/{name}.json"))
except FileNotFoundError:
    sys.exit(f"translations/{name}.json does not exist yet")

errors, warnings = [], []
for i in src.keys() - out.keys():
    errors.append(f"{i}: missing")
for i in out.keys() - src.keys():
    errors.append(f"{i}: unknown id")
for i, en in out.items():
    if i not in src:
        continue
    if not isinstance(en, str):
        errors.append(f"{i}: value is not a string"); continue
    ja = src[i]["ja"]
    want, got = collections.Counter(TOKENS.findall(ja)), collections.Counter(TOKENS.findall(en))
    if want != got:
        errors.append(f"{i}: tags/placeholders differ: ja={sorted(want.elements())} en={sorted(got.elements())}")
    if JP.search(en):
        errors.append(f"{i}: Japanese left in English: {en[:60]!r}")
    if name.startswith("story"):
        lines = en.split("\n")
        if len(lines) > 3 or max(len(l) for l in lines) > 52:
            warnings.append(f"{i}: long box ({len(lines)} lines, max {max(len(l) for l in lines)} chars)")

for e in errors[:40]:
    print("ERROR", e)
for w in warnings[:15]:
    print("WARN ", w)
print(f"{name}: {len(out)}/{len(src)} translated, {len(errors)} errors, {len(warnings)} warnings")
sys.exit(1 if errors else 0)
