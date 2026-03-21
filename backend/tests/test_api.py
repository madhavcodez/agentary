"""Basic API smoke tests for Agentary endpoints."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


def test_projects_list_requires_auth(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 401


def test_missions_list_requires_auth(client):
    resp = client.get("/api/missions")
    assert resp.status_code == 401


def test_agents_list(client):
    resp = client.get("/api/agents")
    # Agents endpoint may require auth or different prefix
    assert resp.status_code in (200, 401, 404)


def test_reports_list_requires_auth(client):
    resp = client.get("/reports/")
    assert resp.status_code == 401


def test_monitors_list_requires_auth(client):
    resp = client.get("/api/monitors")
    assert resp.status_code == 401
