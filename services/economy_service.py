"""Money math helpers. Actual balance changes go through repositories.economy for ledger safety."""
DAILY_BASE = 500
EXPLORE_MONEY = (50, 250)


def daily_reward(streak: int = 1) -> int:
    return DAILY_BASE + min(500, streak * 25)


def conquest_reward(income: int) -> int:
    return income
