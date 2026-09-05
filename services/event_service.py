"""Active-event lookup helper (DB model lives in database.models)."""

def active_mods(events: list) -> dict:
    mods: dict = {"encounter_boost": {}, "reward_mult": 1.0, "xp_mult": 1.0}
    for e in events:
        cfg = e.config if isinstance(e.config, dict) else {}
        for k, v in (cfg.get("encounter_boost") or {}).items():
            mods["encounter_boost"][k] = mods["encounter_boost"].get(k, 0) + v
        mods["reward_mult"] *= cfg.get("reward_mult", 1.0)
        mods["xp_mult"] *= cfg.get("xp_mult", 1.0)
    return mods
