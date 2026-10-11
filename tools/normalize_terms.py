"""Unify proper nouns that different translation batches rendered differently (majority wording wins).

Run after translations change; it is idempotent. Edit CANON to add more.
"""
import glob, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CANON = [  # (variant, canonical) applied in order
    ("Crit Damage Up", "Crit DMG Up"),
    ("Ultimate Cost Down", "Ultimate Cost Reduction"),
    ("Skill Cost Down", "Skill Cost Reduction"),
    ("Limit Release", "Uncap"),
    ("Fortune Flies In! New Year's Lucky Girl Pageant", "Fortune Takes Flight! New Year Lucky Girl Contest"),
    ("Fortune Flies In! New Year's Lucky Girl", "Fortune Takes Flight! New Year Lucky Girl Contest"),
    ("Night of the Cherry Blossom Fete", "Night of the Cherry Blossom Festival"),
    ("Heart-Throb Orario Summer", "Heart-Racing☆Orario Summer"),
    ("Let's☆Be Young! Operation Valentine", "Young Love☆Operation Valentine"),
    ("Open Championship", "Open-Weight Championship"),
]

changed = 0
for f in glob.glob(f"{ROOT}/translations/*_??.json"):
    d = json.load(open(f)); dirty = False
    for k, v in d.items():
        nv = v
        for a, b in CANON:
            nv = nv.replace(a, b)
        if nv != v:
            d[k] = nv; changed += 1; dirty = True
    if dirty:
        json.dump(d, open(f, "w"), ensure_ascii=False, indent=0)
print(f"normalized {changed} strings")
