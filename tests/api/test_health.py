def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ANNEX API"


def test_root_returns_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "ANNEX API"


def test_health_requires_no_auth(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200