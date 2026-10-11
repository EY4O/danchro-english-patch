"""Validate translations/ui_text.json against source/ui_text_ja.json (from ui_text.py scan).

Errors (exit 1): missing/extra keys, lost or added {placeholders} / <tags>, Japanese left in the English.
Warnings: English much longer than the Japanese (layout boxes were sized for Japanese).
"""
import collections, json, os, re, sys

PATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JP = re.compile(r"[぀-ヿ一-鿿]")
TOKENS = re.compile(r"\{[^{}]*\}|</?[a-zA-Z][^<>]*>")

src = json.load(open(f"{PATCH}/source/ui_text_ja.json"))
en = json.load(open(f"{PATCH}/translations/ui_text.json"))
errors, warnings = [], []
for ja in src.keys() - en.keys():
    errors.append(f"missing: {ja!r}")
for ja in en.keys() - src.keys():
    errors.append(f"unknown key: {ja!r}")
for ja, text in en.items():
    if ja not in src:
        continue
    if collections.Counter(TOKENS.findall(ja)) != collections.Counter(TOKENS.findall(text)):
        errors.append(f"tags/placeholders differ: {ja!r} -> {text!r}")
    if JP.search(text):
        errors.append(f"Japanese left: {ja!r} -> {text!r}")
    width_ja = sum(2 if JP.match(c) else 1 for c in ja)  # Japanese glyphs are ~2 Latin glyphs wide
    if len(text) > max(6, width_ja * 1.4):
        warnings.append(f"long: {ja!r} ({width_ja}) -> {text!r} ({len(text)})")
for e in errors[:40]:
    print("ERROR", e)
for w in warnings[:40]:
    print("WARN ", w)
print(f"{len(en)}/{len(src)} translated, {len(errors)} errors, {len(warnings)} long")
sys.exit(1 if errors else 0)
