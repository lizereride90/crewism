RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]

STAR = {"Common": 1, "Uncommon": 2, "Rare": 3, "Epic": 4, "Legendary": 5, "Mythic": 6}


def xp_for_level(level: int) -> int:
    return int(100 * (level ** 1.5))


def power_score(s: int, v: int, e: int, t: int, iq: int = 10) -> int:
    return int(s * 1.2 + v * 1.1 + e * 1.0 + t * 1.2 + iq * 0.5)


def fmt_money(n: int) -> str:
    return f"{n:,} Won"


def progress_bar(cur: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "—"
    filled = max(0, min(length, round(cur / total * length)))
    return "█" * filled + "░" * (length - filled)
