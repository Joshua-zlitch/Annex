from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import Settings
from app.infrastructure.container import Container
from app.interface.factory import create_app
from tests.unit.fakes import (
    FakeAIProvider,
    FakeAnalysisRepository,
    FakeAuthProvider,
    FakeMediaRepository,
    FakeStorageProvider,
)


@pytest.fixture
def test_container():
    return Container(
        Settings(),
        media_repository=FakeMediaRepository(),
        analysis_repository=FakeAnalysisRepository(),
        ai_provider=FakeAIProvider(),
        storage_provider=FakeStorageProvider(),
        auth_provider=FakeAuthProvider(),
    )


@pytest.fixture
def client(test_container):
    app = create_app(settings=test_container.settings, container=test_container)
    return TestClient(app)


AUTH_HEADERS = {"Authorization": "Bearer test-token"}