"""Seed static JSON data into DB without wiping player progress."""
from __future__ import annotations

import json
import logging
import os

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import (
    AbilityDefinition,
    Bloodline,
    BloodlineStage,
    Boss,
    CharacterDefinition,
    Event,
    ItemDefinition,
    Quest,
    Territory,
    Trainer,
)

log = logging.getLogger("crewism.seed")
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load(name: str):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        log.warning("missing seed file %s", name)
        return []
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


async def seed_all():
    async with SessionLocal() as s:
        # characters
        for c in _load("characters.json"):
            if not await s.get(CharacterDefinition, c["id"]):
                s.add(CharacterDefinition(
                    id=c["id"], name=c["name"], series=c.get("series", "lookism"),
                    rarity=c.get("rarity", "Common"), style=c.get("style", "Street Fighting"),
                    char_class=c.get("char_class", "Brawler"), generation=c.get("generation", 2),
                    faction=c.get("faction", "Streets"), role=c.get("role", "recruitable"),
                    source=c.get("source", "canon"), recruitable=c.get("recruitable", 1),
                    base_str=c.get("base_str", 10), base_spd=c.get("base_spd", 10),
                    base_end=c.get("base_end", 10), base_tech=c.get("base_tech", 10),
                    base_iq=c.get("base_iq", 10), bloodline=c.get("bloodline"),
                    ability_id=c.get("ability_id"), min_level=c.get("min_level", 1),
                    description=c.get("description", "")[:2000]))
        # abilities + techniques share ids
        seen = set()
        for fname in ("abilities.json", "techniques.json"):
            for a in _load(fname):
                if a["id"] in seen:
                    continue
                seen.add(a["id"])
                if not await s.get(AbilityDefinition, a["id"]):
                    s.add(AbilityDefinition(id=a["id"], name=a["name"], kind=a.get("kind", "passive"),
                                            trigger=a.get("trigger", "on_round"),
                                            description=a.get("description", "")[:2000],
                                            effects=a.get("effects", {}), source=a.get("source", "original")))
        # bloodlines
        for b in _load("bloodlines.json"):
            if not await s.get(Bloodline, b["id"]):
                s.add(Bloodline(id=b["id"], name=b["name"],
                                description=b.get("description", "")[:2000], source=b.get("source", "canon")))
                for st in b.get("stages", []):
                    s.add(BloodlineStage(bloodline_id=b["id"], stage=st.get("stage", 1),
                                         level_req=st.get("level_req", 1), name=st.get("name", ""),
                                         description=st.get("name", ""), effects=st.get("effects", {})))
        # items
        for it in _load("items.json"):
            if not await s.get(ItemDefinition, it["id"]):
                s.add(ItemDefinition(id=it["id"], name=it["name"], kind=it.get("kind", "consumable"),
                                     rarity=it.get("rarity", "Common"), price=it.get("price", 100),
                                     description=it.get("description", "")[:2000],
                                     effects=it.get("effects", {}), source=it.get("source", "original")))
        # territories
        for t in _load("territories.json"):
            if not await s.get(Territory, t["id"]):
                s.add(Territory(id=t["id"], name=t["name"], rec_level=t.get("rec_level", 1),
                                income=t.get("income", 200), boss_id=t.get("boss_id"),
                                description=t.get("description", "")[:2000]))
        # trainers
        for tr in _load("trainers.json"):
            if not await s.get(Trainer, tr["id"]):
                s.add(Trainer(id=tr["id"], name=tr["name"], specialty=tr.get("specialty", "strength"),
                              price=tr.get("price", 200), duration_min=tr.get("duration_min", 30),
                              req_level=tr.get("req_level", 1), region=tr.get("region", "jhigh"),
                              rarity=tr.get("rarity", "Common"), source=tr.get("source", "original")))
        # quests
        for q in _load("quests.json"):
            if not await s.get(Quest, q["id"]):
                s.add(Quest(id=q["id"], name=q["name"], kind=q.get("kind", "daily"),
                            description=q.get("description", "")[:2000],
                            req=q.get("req", {}), rewards=q.get("rewards", {})))
        # bosses
        for b in _load("bosses.json"):
            if not await s.get(Boss, b["id"]):
                s.add(Boss(id=b["id"], name=b["name"], level=b.get("level", 10),
                           stats=b.get("stats", {}), abilities=b.get("abilities", []),
                           phases=b.get("phases", []), rewards=b.get("rewards", {}),
                           region=b.get("region", "jhigh"), cooldown_h=b.get("cooldown_h", 24),
                           generation=b.get("generation", 2)))
        await s.commit()
    log.info("seed complete")
