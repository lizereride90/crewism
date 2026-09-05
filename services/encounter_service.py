"""Encounter tables by region/level. Returns encounter dicts."""
from __future__ import annotations

import random

TABLES = {
    "jhigh": {"fighter": 40, "money": 15, "item": 12, "trainer": 5, "named": 8, "boss": 1, "nothing": 19},
    "bigdeal_turf": {"fighter": 38, "money": 14, "item": 12, "trainer": 6, "named": 10, "boss": 3, "nothing": 17},
    "hostel_turf": {"fighter": 38, "money": 14, "item": 12, "trainer": 6, "named": 10, "boss": 3, "nothing": 17},
    "cheonliang": {"fighter": 36, "money": 12, "item": 12, "trainer": 6, "named": 12, "boss": 6, "nothing": 16},
    "gangnam": {"fighter": 34, "money": 14, "item": 12, "trainer": 6, "named": 12, "boss": 8, "nothing": 14},
    "workers_turf": {"fighter": 32, "money": 12, "item": 12, "trainer": 6, "named": 12, "boss": 14, "nothing": 12},
    "hnh_tower": {"fighter": 30, "money": 12, "item": 12, "trainer": 6, "named": 12, "boss": 18, "nothing": 10},
}

RARITY_W = {"Common": 40, "Uncommon": 25, "Rare": 15, "Epic": 10, "Legendary": 7, "Mythic": 3}


def roll_encounter(region: str = "jhigh", level: int = 1, event_mod: dict | None = None,
                   rng: random.Random | None = None) -> dict:
    rng = rng or random
    table = dict(TABLES.get(region, TABLES["jhigh"]))
    if event_mod:
        for k, v in event_mod.get("encounter_boost", {}).items():
            if k in table:
                table[k] += v
    total = sum(table.values())
    x = rng.uniform(0, total)
    kind = "nothing"
    for k, w in table.items():
        x -= w
        if x <= 0:
            kind = k
            break
    # rarity gated by level: low levels rarely see high rarity
    rarity_table = dict(RARITY_W)
    if level < 5:
        rarity_table["Legendary"] = 1
        rarity_table["Mythic"] = 0
    elif level < 12:
        rarity_table["Mythic"] = 1
    if kind in ("fighter", "named"):
        total_r = sum(v for v in rarity_table.values() if v > 0)
        y = rng.uniform(0, total_r)
        rarity = "Common"
        for k, w in rarity_table.items():
            if w <= 0:
                continue
            y -= w
            if y <= 0:
                rarity = k
                break
        return {"kind": kind, "rarity": rarity, "region": region}
    return {"kind": kind, "region": region}
