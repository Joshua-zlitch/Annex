from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.core.exceptions import ExternalServiceError
from app.core.ports.ai_provider import AnalysisResult
from app.infrastructure.ai.openai_provider import OpenAIProvider
from app.infrastructure.config import Settings

TRANSIENT_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)

_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class FakeCompletions:
    def __init__(self, client):
        self._client = client

    async def create(self, **kwargs):
        return await self._client._create(kwargs)


class FakeChat:
    def __init__(self, client):
        self.completions = FakeCompletions(client)


class FakeOpenAIClient:
    def __init__(self):
        self.constructor_kwargs = {}
        self.create_calls = []
        self.sleeps = []
        self._queue = []

    @property
    def chat(self):
        return FakeChat(self)

    def enqueue(self, result):
        self._queue.append(result)
        return self

    async def _create(self, kwargs):
        self.create_calls.append(kwargs)
        if not self._queue:
            raise AssertionError("no queued OpenAI responses left")
        result = self._queue.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def make_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def make_provider(max_retries: int = 3) -> OpenAIProvider:
    return OpenAIProvider(Settings(openai_api_key="test-key", openai_max_retries=max_retries))


def transient_error(exc_type):
    request = httpx.Request("POST", _CHAT_URL)
    if exc_type is APITimeoutError:
        return APITimeoutError(request=request)
    if exc_type is APIConnectionError:
        return APIConnectionError(request=request)
    status = {RateLimitError: 429, InternalServerError: 500}[exc_type]
    return exc_type(
        "upstream error",
        response=httpx.Response(status, request=request),
        body=None,
    )


def authentication_error():
    request = httpx.Request("POST", _CHAT_URL)
    return AuthenticationError(
        "invalid api key",
        response=httpx.Response(401, request=request),
        body=None,
    )


def analysis_json(**overrides):
    data = {
        "summary": "A summary.",
        "claims": ["Claim one.", "Claim two."],
        "credibility_score": 0.7,
        "confidence": 0.8,
        "reasoning": "Because.",
        "flagged": True,
    }
    data.update(overrides)
    return json.dumps(data)


@pytest.fixture
def openai_client(monkeypatch):
    fake = FakeOpenAIClient()

    def build_client(**kwargs):
        fake.constructor_kwargs = kwargs
        return fake

    async def noop_sleep(seconds):
        fake.sleeps.append(seconds)

    monkeypatch.setattr("app.infrastructure.ai.openai_provider.AsyncOpenAI", build_client)
    monkeypatch.setattr("app.infrastructure.ai.openai_provider.asyncio.sleep", noop_sleep)
    return fake


async def test_provider_passes_settings_to_client(openai_client):
    make_provider(max_retries=4)

    assert openai_client.constructor_kwargs == {
        "api_key": "test-key",
        "timeout": 60.0,
        "max_retries": 4,
    }


async def test_ocr_retries_transient_error_then_succeeds(openai_client):
    provider = make_provider(max_retries=2)
    openai_client.enqueue(transient_error(APITimeoutError)).enqueue(
        make_response("  hello world  ")
    )

    text = await provider.extract_text_from_image(b"png-bytes", "image/png")

    assert text == "hello world"
    assert len(openai_client.create_calls) == 2
    assert openai_client.sleeps == [pytest.approx(1.0, abs=1.0)]


async def test_ocr_retries_all_transient_errors_then_raises(openai_client):
    provider = make_provider(max_retries=2)
    for exc_type in TRANSIENT_ERRORS:
        openai_client.enqueue(transient_error(exc_type))

    with pytest.raises(ExternalServiceError, match="OCR request failed after 3 attempts"):
        await provider.extract_text_from_image(b"png-bytes", "image/png")

    assert len(openai_client.create_calls) == 3
    assert len(openai_client.sleeps) == 2
    assert 1.0 <= openai_client.sleeps[0] < 2.0
    assert 2.0 <= openai_client.sleeps[1] < 3.0


async def test_ocr_non_transient_api_error_fails_immediately(openai_client):
    provider = make_provider(max_retries=2)
    openai_client.enqueue(authentication_error())

    with pytest.raises(ExternalServiceError, match="OCR request failed"):
        await provider.extract_text_from_image(b"png-bytes", "image/png")

    assert len(openai_client.create_calls) == 1
    assert openai_client.sleeps == []


async def test_ocr_sends_base64_data_url_image(openai_client):
    provider = make_provider()
    image = b"\x89PNG\r\n\x1a\n"
    openai_client.enqueue(make_response("ok"))

    await provider.extract_text_from_image(image, "image/png")

    call = openai_client.create_calls[0]
    assert call["model"] == "gpt-4o-mini"
    assert call["max_tokens"] == 4096
    user_content = call["messages"][1]["content"]
    assert user_content[0]["type"] == "text"
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"] == (
        f"data:image/png;base64,{base64.b64encode(image).decode()}"
    )


async def test_ocr_empty_content_returns_empty_string(openai_client):
    provider = make_provider()
    openai_client.enqueue(make_response(""))

    assert await provider.extract_text_from_image(b"png-bytes", "image/png") == ""


async def test_ocr_none_content_returns_empty_string(openai_client):
    provider = make_provider()
    openai_client.enqueue(make_response(None))

    assert await provider.extract_text_from_image(b"png-bytes", "image/png") == ""


async def test_analysis_retries_transient_errors(openai_client):
    provider = make_provider(max_retries=1)
    openai_client.enqueue(transient_error(RateLimitError)).enqueue(make_response(analysis_json()))

    result = await provider.analyze_content("Some content")

    assert result.summary == "A summary."
    assert len(openai_client.create_calls) == 2


async def test_analysis_success_builds_result(openai_client):
    provider = make_provider()
    openai_client.enqueue(make_response(analysis_json()))

    result = await provider.analyze_content("Some content")

    assert isinstance(result, AnalysisResult)
    assert result.summary == "A summary."
    assert result.claims == ["Claim one.", "Claim two."]
    assert result.credibility_score == 0.7
    assert result.confidence == 0.8
    assert result.reasoning == "Because."
    assert result.flagged is True

    call = openai_client.create_calls[0]
    assert call["model"] == "gpt-4o-mini"
    assert call["response_format"] == {"type": "json_object"}
    assert call["max_tokens"] == 2048
    assert "Some content" in call["messages"][1]["content"]


async def test_analysis_malformed_json_raises_external_error(openai_client):
    provider = make_provider()
    openai_client.enqueue(make_response("this is not json"))

    with pytest.raises(ExternalServiceError, match="malformed JSON"):
        await provider.analyze_content("Some content")


async def test_analysis_missing_required_fields_raises_external_error(openai_client):
    provider = make_provider()
    openai_client.enqueue(make_response(json.dumps({"claims": []})))

    with pytest.raises(ExternalServiceError, match="missing required fields"):
        await provider.analyze_content("Some content")


async def test_analysis_non_numeric_score_raises_external_error(openai_client):
    provider = make_provider()
    openai_client.enqueue(make_response(json.dumps({"summary": "x", "credibility_score": "high"})))

    with pytest.raises(ExternalServiceError, match="missing required fields"):
        await provider.analyze_content("Some content")
