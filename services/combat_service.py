"""Deterministic Lookism combat simulation. No discord imports."""
from __future__ import annotations

import random

BALANCE = {
    "base_hp": 100,
    "hp_per_end": 6,
    "dmg_base": 12,
    "str_scale": 0.55,
    "tech_scale": 0.35,
    "variance": 0.15,
    "max_rounds": 20,
    "diminishing_knee": 40,
    "speed_init_weight": 0.6,
    "iq_crit_bonus": 0.02,
}

# style advantage: attacker -> defender bonus multiplier
STYLE_EDGE = {
    ("Boxing", "Taekwondo"): 1.1,
    ("Taekwondo", "Wrestling"): 1.1,
    ("Wrestling", "Boxing"): 1.12,
    ("Judo", "Street Fighting"): 1.1,
    ("Muay Thai", "Boxing"): 1.08,
    ("Karate", "Muay Thai"): 1.08,
    ("Kendo", "Karate"): 1.1,
}


def _soft_cap(v: float) -> float:
    knee = BALANCE["diminishing_knee"]
    if v <= knee:
        return v
    return knee + (v - knee) ** 0.85


def hp_for(end: int) -> int:
    return BALANCE["base_hp"] + end * BALANCE["hp_per_end"]


def _ability_ids(c: dict) -> set:
    out = set(c.get("abilities") or [])
    if c.get("ability"):
        out.add(c["ability"])
    return {a for a in out if a}


def _has(c: dict, aid: str) -> bool:
    return aid in _ability_ids(c)


def _mastery_mult(mastery: dict | None, stat: str) -> float:
    if not mastery:
        return 1.0
    stage = mastery.get(stat, "Normal")
    return {"Normal": 1.0, "Approaching Threshold": 1.08, "Threshold": 1.18, "Advanced": 1.30}.get(stage, 1.0)


def simulate(a: dict, b: dict, seed: int | None = None) -> dict:
    """a/b: {name,str,spd,end,tech,iq,style,abilities,ability,mastery,bloodline,fatigue}.

    Returns winner/loser/rounds/log/abilities_triggered/damage/xp.
    """
    rng = random.Random(seed)
    fa = dict(a)
    fb = dict(b)
    hp_a = hp_for(fa.get("end", 10))
    hp_b = hp_for(fb.get("end", 10))
    # fatigue reduces effectiveness
    for f in (fa, fb):
        fat = min(50, max(0, f.get("fatigue", 0)))
        f["_fat_mult"] = 1.0 - fat / 200.0

    log: list[str] = []
    triggered: set[str] = set()
    dmg_done = {fa.get("name", "A"): 0, fb.get("name", "B"): 0}

    # bloodline flat buffs
    for f in (fa, fb):
        bl = f.get("bloodline_effects") or {}
        for k in ("str", "spd", "end", "tech"):
            if k in bl:
                f[k] = f.get(k, 10) + int(bl[k])

    log.append(f"{fa.get('name')} vs {fb.get('name')} — fight start.")

    winner = None
    for rnd in range(1, BALANCE["max_rounds"] + 1):
        # initiative
        init_a = fa.get("spd", 10) * BALANCE["speed_init_weight"] + rng.uniform(0, 10)
        init_b = fb.get("spd", 10) * BALANCE["speed_init_weight"] + rng.uniform(0, 10)
        order = [(fa, fb, hp_a, hp_b, "A"), (fb, fa, hp_b, hp_a, "B")] if init_a >= init_b else [(fb, fa, hp_b, hp_a, "B"), (fa, fb, hp_a, hp_b, "A")]

        for atk, dfn, _h1, _h2, tag in order:
            cur_hp_a, cur_hp_b = (hp_a, hp_b) if tag == "A" else (hp_b, hp_a)
            # resolve single strike atk -> dfn
            atk_hp = hp_a if atk is fa else hp_b
            dfn_hp = hp_b if atk is fa else hp_a
            dfn_max = hp_for(dfn.get("end", 10))

            s = _soft_cap(float(atk.get("str", 10)))
            t = _soft_cap(float(atk.get("tech", 10)))
            raw = BALANCE["dmg_base"] + s * BALANCE["str_scale"] + t * BALANCE["tech_scale"]
            raw *= _mastery_mult(atk.get("mastery"), "str") if False else 1.0
            # style edge
            edge = STYLE_EDGE.get((atk.get("style", ""), dfn.get("style", "")), 1.0)
            raw *= edge
            # battle IQ crit
            crit_c = min(0.25, 0.05 + atk.get("iq", 10) * BALANCE["iq_crit_bonus"] * 0.1)
            crit = rng.random() < crit_c
            if crit:
                raw *= 1.5
            # endurance mitigation with diminishing returns
            mit = min(0.55, _soft_cap(float(dfn.get("end", 10))) * 0.008)
            raw *= (1 - mit)
            # fatigue
            raw *= atk.get("_fat_mult", 1.0)
            # abilities
            bonus_note = ""
            if _has(atk, "invisible_attack") and atk.get("spd", 10) >= dfn.get("spd", 10) + 5:
                raw *= 1.2
                triggered.add("invisible_attack")
                bonus_note += " Unseen strike lands."
            if _has(atk, "boxing_pressure"):
                raw *= 1.1
                triggered.add("boxing_pressure")
            if _has(atk, "weapon_master") and atk.get("has_weapon"):
                raw *= 1.2
                triggered.add("weapon_master")
            if _has(atk, "judo_throw") and atk.get("tech", 10) > dfn.get("tech", 10):
                raw *= 1.15
                triggered.add("judo_throw")
            if _has(dfn, "iron_will"):
                raw *= 0.9
                triggered.add("iron_will")
            if _has(dfn, "counter_master") and rng.random() < 0.15:
                raw *= 0.7
                triggered.add("counter_master")
                bonus_note += " Countered."
            # ultra instinct when low
            atk_cur = hp_a if atk is fa else hp_b
            atk_max = hp_for(atk.get("end", 10))
            if _has(atk, "ultra_instinct") and atk_cur < atk_max * 0.35:
                raw *= 1.15
                triggered.add("ultra_instinct")
                bonus_note += " Instinct takes over."
            # conviction comeback
            if _has(atk, "conviction") and atk_cur < atk_max * 0.3:
                raw *= 1.2
                triggered.add("conviction")
                bonus_note += " Conviction burns."
            # dodge from ultra instinct defender
            if _has(dfn, "ultra_instinct") and dfn_hp < dfn_max * 0.35 and rng.random() < 0.15:
                triggered.add("ultra_instinct")
                log.append(f"Round {rnd}: {dfn.get('name')} slips the punch by instinct.")
                continue

            raw *= 1 + rng.uniform(-BALANCE["variance"], BALANCE["variance"])
            dmg = max(1, int(raw))
            if atk is fa:
                hp_b -= dmg
                dmg_done[fa.get("name", "A")] += dmg
            else:
                hp_a -= dmg
                dmg_done[fb.get("name", "B")] += dmg

            flavor = "crits" if crit else "hits"
            log.append(f"Round {rnd}: {atk.get('name')} {flavor} {dfn.get('name')} for {dmg}.{bonus_note}")

            # copy: chance to note mimicry
            if _has(atk, "copy") and atk.get("tech", 10) >= 20 and rng.random() < 0.1:
                triggered.add("copy")
                log.append(f"Round {rnd}: {atk.get('name')} copies a move.")

            if hp_a <= 0 or hp_b <= 0:
                break
        if hp_a <= 0 or hp_b <= 0:
            break
        # boss phase hooks are applied by caller via hp fractions; log nothing here

    if hp_a <= 0 and hp_b <= 0:
        winner = None  # draw -> higher remaining initiative wins by speed
        winner = fa if fa.get("spd", 10) >= fb.get("spd", 10) else fb
    elif hp_a <= 0:
        winner = fb
    elif hp_b <= 0:
        winner = fa
    else:
        winner = fa if hp_a >= hp_b else fb

    loser = fb if winner is fa else fa
    # xp scaled by loser power
    loser_pow = loser.get("str", 10) + loser.get("spd", 10) + loser.get("end", 10) + loser.get("tech", 10)
    xp = max(20, int(loser_pow * 2.2))

    return {
        "winner": winner.get("name"),
        "winner_side": "A" if winner is fa else "B",
        "loser": loser.get("name"),
        "rounds": len([l for l in log if l.startswith("Round")]),
        "hp_a": max(0, hp_a),
        "hp_b": max(0, hp_b),
        "damage": dmg_done,
        "abilities_triggered": sorted(triggered),
        "xp": xp,
        "log": log[-30:],
    }
