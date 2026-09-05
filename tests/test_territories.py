from services.encounter_service import roll_encounter
from services.event_service import active_mods


class FakeE:
    def __init__(self, config):
        self.config = config


def test_encounter_kinds():
    e = roll_encounter("jhigh", 1)
    assert "kind" in e


def test_event_mods():
    m = active_mods([FakeE({"encounter_boost": {"boss": 5}, "reward_mult": 2.0})])
    assert m["encounter_boost"]["boss"] == 5
    assert m["reward_mult"] == 2.0
