"""Training, mastery, bloodline progression rules."""
from __future__ import annotations

MASTERY_ORDER = ["Normal", "Approaching Threshold", "Threshold", "Advanced"]
MASTERY_STAT = {"strength": "str", "speed": "spd", "endurance": "end", "technique": "tech"}
MASTERY_NEED = {"Normal": 0, "Approaching Threshold": 30, "Threshold": 60, "Advanced": 100}


def training_gains(specialty: str, base: int = 3, train_boost_pct: int = 0) -> dict:
    gains = {"str": 1, "spd": 1, "end": 1, "tech": 1}
    key = {"strength": "str", "speed": "spd", "endurance": "end", "technique": "tech"}.get(specialty, "str")
    gains[key] = base
    if train_boost_pct:
        for k in gains:
            gains[k] = int(gains[k] * (1 + train_boost_pct / 100))
    return gains


def mastery_check(stat_value: int, fights_won: int) -> str:
    stage = "Normal"
    if stat_value >= 100 and fights_won >= 30:
        return "Advanced"
    if stat_value >= 60 and fights_won >= 12:
        return "Threshold"
    if stat_value >= 30 and fights_won >= 4:
        return "Approaching Threshold"
    return stage


def bloodline_available(stages: list[dict], player_level: int, current: int) -> dict | None:
    nxt = current + 1
    for st in stages:
        if st.get("stage") == nxt and player_level >= st.get("level_req", 1):
            return st
    return None
