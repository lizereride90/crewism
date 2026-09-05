"""Crew + territory + quest/boss/event helpers."""
from __future__ import annotations

from datetime import datetime, timedelta


def conquest_cooldown_hours() -> int:
    return 12


def can_conquer(cooldown_until: datetime | None, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return not cooldown_until or now >= cooldown_until


def next_conquest_time() -> datetime:
    return datetime.utcnow() + timedelta(hours=conquest_cooldown_hours())


def crew_war_power(team_powers: list[int], territory_bonus: int = 0, morale: int = 0) -> int:
    return sum(team_powers) + territory_bonus + morale


def quest_complete(progress: int, need: int) -> bool:
    return progress >= need


def boss_phases_triggered(phases: list[dict], hp_frac: float) -> list[dict]:
    out = []
    for p in phases:
        at = p.get("at", 50) / 100
        if hp_frac <= at:
            out.append(p)
    return out
