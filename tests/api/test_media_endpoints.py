from tests.conftest import AUTH_HEADERS


def test_upload_image_creates_media_and_analysis(client):
    response = client.post(
        "/api/v1/media/upload",
        headers=AUTH_HEADERS,
        files={"file": ("screenshot.png", b"fake-png-content", "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["media_type"] == "image"
    assert body["source"] == "upload"
    assert body["status"] == "pending"
    assert body["media_id"]
    assert body["analysis_id"]

    analysis_id = body["analysis_id"]
    analysis = client.get(f"/api/v1/analysis/{analysis_id}", headers=AUTH_HEADERS)
    assert analysis.status_code == 200
    result = analysis.json()
    assert result["status"] in {"completed", "processing", "pending"}
    assert result["media_id"] == body["media_id"]


def test_upload_rejects_non_image(client):
    response = client.post(
        "/api/v1/media/upload",
        headers=AUTH_HEADERS,
        files={"file": ("data.json", b"{}", "application/json")},
    )
    assert response.status_code == 422
    assert "unsupported content type" in response.json()["detail"]


def test_upload_rejects_oversized_file(client, test_container):
    big = b"x" * (test_container.settings.max_upload_size_bytes + 1)
    response = client.post(
        "/api/v1/media/upload",
        headers=AUTH_HEADERS,
        files={"file": ("big.png", big, "image/png")},
    )
    assert response.status_code == 422
    assert "upload limit" in response.json()["detail"]


def test_create_text_media_runs_background_analysis(client):
    response = client.post(
        "/api/v1/media/from-text",
        headers=AUTH_HEADERS,
        json={"text": "A clearly false headline about the moon."},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["media_type"] == "text"
    assert body["status"] == "pending"

    analysis = client.get(f"/api/v1/analysis/{body['analysis_id']}", headers=AUTH_HEADERS)
    assert analysis.status_code == 200
    result = analysis.json()
    assert result["ocr_text"] == "A clearly false headline about the moon."
    assert result["summary"] == "A fake summary."
    assert [c["text"] for c in result["claims"]] == ["Claim one.", "Claim two."]


def test_list_and_get_media(client):
    create = client.post(
        "/api/v1/media/from-text", headers=AUTH_HEADERS, json={"text": "content here"}
    )
    media_id = create.json()["media_id"]

    listed = client.get("/api/v1/media", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()["items"]]
    assert media_id in ids

    fetched = client.get(f"/api/v1/media/{media_id}", headers=AUTH_HEADERS)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == media_id


def test_media_requires_auth(client):
    response = client.get("/api/v1/media")
    assert response.status_code == 401


def test_get_unknown_media_returns_404(client):
    response = client.get("/api/v1/media/does-not-exist", headers=AUTH_HEADERS)
    assert response.status_code == 404