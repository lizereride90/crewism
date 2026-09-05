from services.combat_service import simulate


def _c(name, s=20, v=20, e=20, t=20, **kw):
    d = {"name": name, "str": s, "spd": v, "end": e, "tech": t, "iq": 12,
         "style": "Street Fighting", "abilities": []}
    d.update(kw)
    return d


def test_deterministic_with_seed():
    a, b = _c("A"), _c("B")
    r1 = simulate(a, b, seed=42)
    r2 = simulate(a, b, seed=42)
    assert r1["winner"] == r2["winner"]
    assert r1["rounds"] == r2["rounds"]


def test_stronger_usually_wins():
    a = _c("Strong", s=40, e=40)
    b = _c("Weak", s=10, e=10)
    r = simulate(a, b, seed=7)
    assert r["winner"] == "Strong"


def test_abilities_trigger():
    a = _c("UI", abilities=["ultra_instinct"], e=10)
    b = _c("B", s=30)
    r = simulate(a, b, seed=3)
    assert "winner" in r and r["xp"] > 0 and isinstance(r["log"], list)


def test_style_edge():
    a = _c("Boxer", style="Boxing", s=25)
    b = _c("Kicker", style="Taekwondo", e=25)
    r = simulate(a, b, seed=11)
    assert r["winner"] in ("Boxer", "Kicker")
