def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


def test_get_profile(client):
    resp = client.get("/profile")
    assert resp.status_code in (200, 404)


def test_list_opportunities_empty(client):
    resp = client.get("/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 0
    assert "items" in data


def test_list_matches_empty(client):
    resp = client.get("/matches")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_list_policies_empty(client):
    resp = client.get("/policies")
    assert resp.status_code == 200


def test_ingest_status(client):
    resp = client.get("/ingest/status")
    assert resp.status_code == 200


def test_create_policy(client):
    resp = client.post("/policies", json={
        "name": "Test Policy",
        "rules_json": {"exclude_companies": ["test"]},
        "description": "A test policy",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Policy"
    assert data["is_active"] is True
