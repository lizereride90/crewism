from .training_service import MASTERY_ORDER, mastery_check  # noqa: F401  re-export

STAGES = MASTERY_ORDER


def evaluate(stat_value: int, fights_won: int) -> str:
    return mastery_check(stat_value, fights_won)
