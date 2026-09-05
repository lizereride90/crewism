import random


def roll(p: float, rng: random.Random | None = None) -> bool:
    r = rng or random
    return r.random() < p


def weighted_choice(table: dict, rng: random.Random | None = None):
    r = rng or random
    total = sum(table.values())
    x = r.uniform(0, total)
    for k, w in table.items():
        x -= w
        if x <= 0:
            return k
    return next(iter(table))


def seeded(seed: int) -> random.Random:
    return random.Random(seed)
