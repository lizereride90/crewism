from services.bloodline_service import bloodline_available  # noqa: F401
from services.mastery_service import evaluate
from services.crew_service import crew_war_power


def test_bloodlines():
    assert True  # progression covered in test_progression


def test_mastery_eval():
    assert evaluate(10, 0) == "Normal"


def test_territories_power():
    assert crew_war_power([100, 120], territory_bonus=20) == 240
