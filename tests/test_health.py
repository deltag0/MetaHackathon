def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


def test_health_live_returns_200(client):
    """Liveness probe must always return 200 — no external deps checked."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_health_ready_checks_db(client):
    """Readiness probe must check the DB and report its status."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


def test_health_ready_includes_cache_key(client):
    """Readiness probe response must include a cache field."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert "cache" in data
