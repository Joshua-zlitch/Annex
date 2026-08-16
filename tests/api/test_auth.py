from tests.conftest import AUTH_HEADERS


def test_me_returns_current_user(client):
    response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user-1"
    assert body["email"] == "user@example.com"


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-the-test-token"}
    )
    assert response.status_code == 401