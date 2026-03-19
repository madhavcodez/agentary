from app.voice.policy.engine import PolicyEngine


def test_pre_call_business_hours():
    engine = PolicyEngine()
    result = engine.evaluate_pre_call({})
    # Result depends on current time, just verify structure
    assert "allowed" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)


def test_mid_call_forbidden_topics():
    engine = PolicyEngine()

    result = engine.evaluate_mid_call("Let's discuss the weather")
    assert result["allowed"] is True

    result = engine.evaluate_mid_call("I want to talk about salary negotiation details")
    assert result["allowed"] is False
    assert any("salary negotiation" in v.lower() for v in result["violations"])


def test_mid_call_pii_detection():
    engine = PolicyEngine()

    result = engine.evaluate_mid_call("My SSN is 123-45-6789")
    assert result["allowed"] is False
    assert any("ssn" in v.lower() for v in result["violations"])

    result = engine.evaluate_mid_call("No sensitive info here")
    assert result["allowed"] is True
