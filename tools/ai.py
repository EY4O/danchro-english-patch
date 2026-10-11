"""Smarter auto-battle: don't waste heal skills/assists at full HP.

The stock "Attack Priority", "Strong Enemy Priority" and "Solo Priority" behaviour trees fire every
assist and skill as soon as it is off cooldown, so Hestia-style heal assists go off at 100% HP.
The game's own "Heal Priority" tree already guards heals with "HP below 70%" checks; this copies
that guard into the other trees:

    Sequence[ SelectAttackSkillCommand X, IsAttackableSkillCommand ]
 -> Sequence[ SelectAttackSkillCommand X, IsAttackableSkillCommand,
              Selector[ Inverter(IsContainHealSkillCommand),        # not a heal: use freely
                        IsConditionMatch(self HP < threshold),        # heal, and I'm hurt
                        IsFormationUnitConditionMatch(HP < threshold) ] ]  # heal, and a party unit is hurt

for X in Assist / Artifact / Ex / Unique / Limited (Normal attacks are left alone so the AI never stalls).
"""
import copy, json

HEAL_HP_THRESHOLD = 0.7          # same value the developers use in AutoBehavior_Heal
TREES = ("AutoBehavior", "AutoBehavior_TargetBoss", "AutoBehavior_Solo")
GUARDED = ("Assist", "Artifact", "Ex", "Unique", "Limited")
AI = "Dma.Games.QuestBattle.Characters.AI."
BD = "BehaviorDesigner.Runtime.Tasks."


def _walk(t):
    yield t
    for c in t.get("Children", []):
        yield from _walk(c)


def _templates(heal_tree):
    """Pull node templates (with valid NodeData) from the developers' Heal Priority tree."""
    want = {}
    for t in _walk(heal_tree["RootTask"]):
        ty = t["Type"]
        if ty.endswith(".Selector") and "selector" not in want:
            want["selector"] = t
        elif ty.endswith(".Inverter") and t.get("Children") and t["Children"][0]["Type"] == AI + "IsContainHealSkillCommand":
            want.setdefault("not_heal", t)
        elif ty == AI + "IsConditionMatch":
            want.setdefault("self_hp", t)
        elif ty == AI + "IsFormationUnitConditionMatch":
            want.setdefault("party_hp", t)
    missing = {"selector", "not_heal", "self_hp", "party_hp"} - want.keys()
    assert not missing, f"templates not found: {missing}"
    return want


def _clone(node, next_id):
    n = copy.deepcopy(node)
    if n["Type"].endswith(".Selector"):
        n.pop("Children", None)  # the guard gets its own children
    for t in _walk(n):
        t["ID"] = next_id[0]; next_id[0] += 1
    return n


def _set_threshold(node):
    for cond in node["CharacterStatusMatchCondition[]statusMatchConditions"]:
        if cond.get("MatchConditionTargetStatusTypeMatchStatusType") == "CurrentHpRatio":
            cond["Singlethreshold"] = HEAL_HP_THRESHOLD
    return node


def patch_tree(tree_json: str, heal_tree_json: str):
    tree, tpl = json.loads(tree_json), _templates(json.loads(heal_tree_json))
    next_id = [max(t["ID"] for t in _walk(tree["RootTask"])) + 1]
    for d in tree.get("DetachedTasks") or []:
        next_id[0] = max(next_id[0], max(t["ID"] for t in _walk(d)) + 1)
    patched = 0
    for seq in _walk(tree["RootTask"]):
        kids = seq.get("Children", [])
        if not (seq["Type"] == BD + "Sequence" and len(kids) == 2
                and kids[0]["Type"] == AI + "SelectAttackSkillCommand"
                and kids[0].get("SkillCommandTypeselectCommandType") in GUARDED
                and kids[1]["Type"] == AI + "IsAttackableSkillCommand"):
            continue
        guard = _clone(tpl["selector"], next_id)
        guard["Children"] = [_clone(tpl["not_heal"], next_id),
                             _set_threshold(_clone(tpl["self_hp"], next_id)),
                             _set_threshold(_clone(tpl["party_hp"], next_id))]
        kids.append(guard)
        patched += 1
    return json.dumps(tree, ensure_ascii=False, separators=(",", ":")), patched


def apply(bundle_path, log=print):
    """Return the bundle bytes with patched behaviour trees, or None if nothing changed."""
    import UnityPy
    env = UnityPy.load(bundle_path)
    objs = {o.read_typetree()["m_Name"]: o for o in env.objects if o.type.name == "MonoBehaviour"}
    heal = objs["AutoBehavior_Heal"].read_typetree()["mBehaviorSource"]["mTaskData"]["JSONSerialization"]
    total = 0
    for name in TREES:
        tt = objs[name].read_typetree()
        data = tt["mBehaviorSource"]["mTaskData"]
        data["JSONSerialization"], n = patch_tree(data["JSONSerialization"], heal)
        objs[name].save_typetree(tt)
        log(f"auto-battle: {name}: guarded {n} skill branches (heals only below {HEAL_HP_THRESHOLD:.0%} HP)")
        total += n
    return env.file.save(packer="lz4") if total else None
