from app.services.match_engine import _passes_hard_filter


def test_passes_ai_ml_roles():
    assert _passes_hard_filter("AI Engineer", "Work on LLMs") is True
    assert _passes_hard_filter("Machine Learning Engineer", None) is True
    assert _passes_hard_filter("ML Research Scientist", "deep learning") is True


def test_passes_fullstack_roles():
    assert _passes_hard_filter("Full Stack Developer", None) is True
    assert _passes_hard_filter("Software Engineer", "full stack web development") is True
    assert _passes_hard_filter("Backend Engineer", None) is True


def test_filters_senior_roles():
    assert _passes_hard_filter("Staff Engineer", None) is False
    assert _passes_hard_filter("Principal Software Engineer", None) is False
    assert _passes_hard_filter("Director of Engineering", None) is False
    assert _passes_hard_filter("VP Engineering", None) is False


def test_filters_unrelated_roles():
    assert _passes_hard_filter("Marketing Manager", "manage campaigns") is False
    assert _passes_hard_filter("Sales Representative", None) is False
    assert _passes_hard_filter("HR Coordinator", None) is False


def test_yoe_filter():
    assert _passes_hard_filter("Software Engineer", "Requires 10+ years of experience") is False
    assert _passes_hard_filter("Software Engineer", "0-3 years experience") is True
    assert _passes_hard_filter("Software Engineer", "2+ years") is True
