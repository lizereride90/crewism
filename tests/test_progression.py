from services.character_service import recruit_chance, synergy_bonus, team_power, xp_for_level
from services.crew_service import boss_phases_triggered, can_conquer
from services.training_service import bloodline_available, mastery_check, training_gains


def test_xp_curve():
    assert xp_for_level(2) > xp_for_level(1)


def test_recruit_win_matters():
    assert recruit_chance("Rare", True, 5, 1) > recruit_chance("Rare", False, 5, 1)


def test_synergy_same_faction():
    m = [{"str": 20, "end": 20, "spd": 10, "tech": 10, "faction": "Big Deal",
          "style": "Boxing", "char_class": "Brawler", "rarity": "Common"} for _ in range(3)]
    assert synergy_bonus(m) > 0
    assert team_power(m) > 0


def test_mastery_gates():
    assert mastery_check(10, 0) == "Normal"
    assert mastery_check(65, 15) == "Threshold"


def test_bloodline_gating():
    stages = [{"stage": 1, "level_req": 15}]
    assert bloodline_available(stages, 1, 0) is None
    assert bloodline_available(stages, 20, 0) is not None


def test_training_gains():
    g = training_gains("strength")
    assert g["str"] >= 3


def test_conquer_and_phases():
    assert can_conquer(None) is True
    assert boss_phases_triggered([{"at": 50}], 0.4)
