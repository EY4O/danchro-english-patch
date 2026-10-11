"""Gameplay rebalance for the offline edition: fairer gacha, more crystals from story.

apply(md) returns {table_name: rows} for every table it changes, plus prints a summary.
Tunables are at the top; set a multiplier to 1 (or a rate to None) to leave that part vanilla.
"""
import collections

CRYSTAL = 990000001             # free crystals (shown top-left in menus)
EXCHANGE_TOKEN = 920010053      # token granted per pull; 50 buy any character in exchange shop 150015001
ACTIVE_GACHAS = range(5065, 5070)  # the five element banners still live in the offline edition

TOKEN_MULTIPLIER = 5            # 1 pull -> 5 tokens, so a ten-pull = one character of your choice
TOP_RARITY_WEIGHT_MULTIPLIER = 3  # 2.5% -> 7.5% for top-rarity characters and assists
STORY_FIRST_CLEAR_CRYSTALS = {1: 150, 2: 300, 3: 500}  # by quest Difficulty: normal / hard / very hard

# Less grind: multipliers on per-clear rewards for every quest type, and on upgrade-material drops.
QUEST_REWARD_MULTIPLIER = {"RewardExp": 2, "RewardCp": 2, "RewardPlayerExp": 2, "RewardFamiliaExp": 2,
                           "DropGoldItemAmount": 2}
QUEST_TABLES = ("m_dma_quest_dungeon", "m_dma_quest_event", "m_dma_quest_daily", "m_dma_quest_deep",
                "m_dma_quest_episode")
MATERIAL_DROP_MULTIPLIER = 2
MATERIAL_CONTENT_TYPES = (13, 14)  # enhancement materials; currency (2) and artifacts (41) untouched

PLAYABLE, ASSIST = 21, 22


def _gacha(md, log):
    extra = md.table("m_dma_gacha_extra")
    n = 0
    for r in extra:
        if r["ContentId"] == EXCHANGE_TOKEN:
            r["ContentQuantity"] *= TOKEN_MULTIPLIER
            n += 1
    log(f"exchange tokens x{TOKEN_MULTIPLIER} on {n} gacha bonus rows")

    draws = [r for r in md.table("m_dma_gacha_draw") if r["MdmaGachaId"] in ACTIVE_GACHAS]
    groups = {r[f"MdmaGachaLotteryRarityGroupId{s}"] for r in draws for s in ("I", "II", "III")} - {0, None}
    rarity_of = {PLAYABLE: {r["Id"]: r["Rarity"] for r in md.table("m_dma_character_playable")},
                 ASSIST: {r["Id"]: r.get("Rarity") for r in md.table("m_dma_character_assist")}}
    contents = collections.defaultdict(list)
    for c in md.table("m_dma_gacha_lottery_content"):
        contents[c["GroupId"]].append(c)

    rarity = md.table("m_dma_gacha_lottery_rarity")
    for g in sorted(groups):
        rows = [r for r in rarity if r["GroupId"] == g]
        for kind in (PLAYABLE, ASSIST):
            tiers = []
            for r in rows:
                cs = contents[r["MdmaGachaLotteryContentGroupId"]]
                if cs and cs[0]["ContentType"] == kind:
                    tiers.append((max(rarity_of[kind].get(c["ContentId"]) or 0 for c in cs), r))
            if len(tiers) < 2:
                continue
            top_r = max(t for t, _ in tiers)
            low_r = min(t for t, _ in tiers)
            top = [r for t, r in tiers if t == top_r]
            low = [r for t, r in tiers if t == low_r]
            added = sum(r["Weight"] * (TOP_RARITY_WEIGHT_MULTIPLIER - 1) for r in top)
            if added >= sum(r["Weight"] for r in low):
                log(f"  group {g}: not enough low-rarity weight to rebalance kind {kind}; skipped")
                continue
            for r in top:
                r["Weight"] *= TOP_RARITY_WEIGHT_MULTIPLIER
            for r in low:  # take the extra weight from the lowest tier so the total is unchanged
                r["Weight"] -= added * r["Weight"] // sum(x["Weight"] for x in low)
    log(f"top-rarity weight x{TOP_RARITY_WEIGHT_MULTIPLIER} in {len(groups)} rarity groups of banners {list(ACTIVE_GACHAS)}")
    return {"m_dma_gacha_extra": extra, "m_dma_gacha_lottery_rarity": rarity}


def _story(md, log):
    rewards = md.table("m_dma_reward_quest")
    by_group = collections.defaultdict(list)
    for r in rewards:
        by_group[r["GroupId"]].append(r)
    next_id = max(r["Id"] for r in rewards) + 1
    changed = added = 0
    seen = set()
    for q in md.table("m_dma_quest_dungeon"):
        g, amount = q["FirstMDmaRewardGroupId"], STORY_FIRST_CLEAR_CRYSTALS.get(q["Difficulty"])
        if not g or not amount or g in seen:
            continue
        seen.add(g)
        crystal = [r for r in by_group[g] if r["ContentId"] == CRYSTAL]
        if crystal:
            for r in crystal:
                if r["ContentQuantity"] < amount:
                    r["ContentQuantity"] = amount; changed += 1
        elif by_group[g]:  # group exists (other rewards) but pays no crystals: add a crystal row
            template = next(r for r in by_group[g])
            row = dict(template, Id=next_id, ContentType=2, ContentId=CRYSTAL, ContentQuantity=amount)
            rewards.append(row); by_group[g].append(row); next_id += 1; added += 1
    rewards.sort(key=lambda r: r["Id"])  # MasterMemory tables must stay sorted by primary key
    log(f"story first-clear crystals: {changed} reward rows raised, {added} added")
    return {"m_dma_reward_quest": rewards}


def _grind(md, log):
    out = {}
    for t in QUEST_TABLES:
        rows = md.table(t)
        for r in rows:
            for field, mult in QUEST_REWARD_MULTIPLIER.items():
                if field in r and r[field]:
                    r[field] = int(r[field] * mult)
        out[t] = rows
    drops = md.table("m_dma_reward_enemy_drop")
    n = 0
    for r in drops:
        if r["ContentType"] in MATERIAL_CONTENT_TYPES:
            r["ContentQuantity"] *= MATERIAL_DROP_MULTIPLIER; n += 1
    out["m_dma_reward_enemy_drop"] = drops
    log(f"less grind: quest EXP/gold x{QUEST_REWARD_MULTIPLIER['RewardExp']} in {len(QUEST_TABLES)} quest tables, "
        f"material drops x{MATERIAL_DROP_MULTIPLIER} on {n} drop rows")
    return out


def apply(md, log=print):
    out = {}
    out.update(_gacha(md, log))
    out.update(_story(md, log))  # story crystals first: it reads m_dma_quest_dungeon before _grind replaces it
    grind = _grind(md, log)
    out.update(grind)
    return out
