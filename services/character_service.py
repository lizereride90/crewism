"""Recruitment, synergy, team power. No discord imports."""
from __future__ import annotations

RARITY_MULT = {"Common": 1.0, "Uncommon": 1.08, "Rare": 1.16, "Epic": 1.26, "Legendary": 1.4, "Mythic": 1.55}


def recruit_chance(rarity: str, won: bool, player_level: int, min_level: int,
                   reputation: int = 0) -> float:
    base = {"Common": 0.9, "Uncommon": 0.75, "Rare": 0.6, "Epic": 0.45, "Legendary": 0.3, "Mythic": 0.15}[rarity]
    if not won:
        base *= 0.25
    if player_level < min_level:
        base *= 0.4
    base += min(0.15, reputation / 2000)
    return max(0.05, min(0.95, base))


def team_power(members: list[dict]) -> int:
    total = 0
    for m in members:
        s = m.get("str", 10) + m.get("spd", 10) + m.get("end", 10) + m.get("tech", 10)
        total += s * RARITY_MULT.get(m.get("rarity", "Common"), 1.0)
    return int(total + synergy_bonus(members))


def synergy_bonus(members: list[dict]) -> float:
    if len(members) < 2:
        return 0
    bonus = 0.0
    factions = [m.get("faction") for m in members]
    if len(set(factions)) == 1:
        bonus += sum(m.get("str", 0) + m.get("end", 0) for m in members) * 0.03
    styles = [m.get("style") for m in members]
    # technique-focused team: combo consistency
    if styles.count("Judo") + styles.count("Systema") >= 2:
        bonus += 8
    # speed team initiative
    if sum(m.get("spd", 0) for m in members) / len(members) > 24:
        bonus += 6
    # balanced team adaptability
    classes = {m.get("char_class") for m in members}
    if len(classes) >= 3:
        bonus += 6
    return bonus


def xp_for_level(level: int) -> int:
    return int(100 * (level ** 1.5))
