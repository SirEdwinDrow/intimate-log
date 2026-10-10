from app import scoring


def test_overall_weighted():
    s = {c.key: 10 for c in scoring.CRITERIA}
    assert scoring.overall_score(s) == 10.0
    assert scoring.overall_score({}) is None
    assert scoring.overall_score({"chemistry": 8, "stamina": None}) == 8.0
    # вес химии 1.5, выносливости 0.9: (10*1.5 + 2*0.9)/2.4 = 7.0
    assert scoring.overall_score({"chemistry": 10, "stamina": 2}) == 7.0


def test_clamp():
    assert scoring.clamp_score("15") == 10
    assert scoring.clamp_score("0") == 1
    assert scoring.clamp_score("") is None
    assert scoring.clamp_score("abc") is None


def test_tier():
    assert scoring.tier(9.3) == "S"
    assert scoring.tier(8.0) == "A"
    assert scoring.tier(7) == "B"
    assert scoring.tier(5) == "C"
    assert scoring.tier(2) == "D"
    assert scoring.tier(None) == "—"
