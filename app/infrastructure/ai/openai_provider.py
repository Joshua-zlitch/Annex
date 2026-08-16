from __future__ import annotations

import asyncio
import base64
import json
import random
from collections.abc import Awaitable, Callable

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from app.core.exceptions import ExternalServiceError
from app.core.ports.ai_provider import AIProvider, AnalysisResult
from app.infrastructure.config import Settings

_TRANSIENT_ERRORS = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)

_OCR_SYSTEM_PROMPT = (
    "You are an OCR engine specialised in extracting text from images with high accuracy. "
    "Transcribe ALL visible text verbatim, preserving reading order and line breaks. "
    "Do not add commentary, corrections or markdown. If no text is present, return an empty string."
)

_ANALYSIS_SYSTEM_PROMPT = (
    "You are ANNEX, an AI-powered media and information literacy analyst. "
    "Your mission is 'Learn Before You Believe': help users critically evaluate content. "
    "Given the transcribed content of a piece of media, produce a credibility assessment. "
    "Respond ONLY with a JSON object matching this schema:\n"
    '{"summary": string, "claims": [string], "credibility_score": number 0-1, '
    '"confidence": number 0-1, "flagged": boolean, "reasoning": string}. '
    "credibility_score should be low (0-0.33) for likely false/misleading content, "
    "medium (0.34-0.66) for mixed/unverifiable, high (0.67-1) for credible. "
    "Set flagged=true when the content is likely false, misleading, or unverifiable and dangerous. "
    "Be rigorous, cite what in the text supports your score, and never fabricate external facts."
)


class OpenAIProvider(AIProvider):
    """OpenAI-backed AI provider using vision (gpt-4o) for OCR and JSON output for analysis."""

    def __init__(self, settings: Settings):
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
        self._ocr_model = settings.openai_ocr_model
        self._analysis_model = settings.openai_analysis_model
        self._max_retries = settings.openai_max_retries

    async def _with_retries(self, operation: str, call: Callable[[], Awaitable[object]]) -> object:
        """Run an OpenAI call, retrying transient failures with exponential backoff + jitter."""
        for attempt in range(self._max_retries + 1):
            try:
                return await call()
            except _TRANSIENT_ERRORS as exc:
                if attempt >= self._max_retries:
                    raise ExternalServiceError(
                        f"{operation} failed after {self._max_retries + 1} attempts: {exc}"
                    ) from exc
                delay = min(2**attempt, 8) + random.uniform(0, 1)
                await asyncio.sleep(delay)
            except APIError as exc:
                raise ExternalServiceError(f"{operation} failed: {exc}") from exc
        raise AssertionError("unreachable")

    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str) -> str:
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
        response = await self._with_retries(
            "OCR request",
            lambda: self._client.chat.completions.create(
                model=self._ocr_model,
                messages=[
                    {"role": "system", "content": _OCR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Transcribe all visible text in this image."},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                max_tokens=4096,
            ),
        )
        return (response.choices[0].message.content or "").strip()

    async def analyze_content(self, content: str) -> AnalysisResult:
        user_prompt = f"Transcribed content to analyse:\n\n{content[:15000]}"
        response = await self._with_retries(
            "Analysis request",
            lambda: self._client.chat.completions.create(
                model=self._analysis_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2048,
            ),
        )

        raw = (response.choices[0].message.content or "{}").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExternalServiceError("AI returned malformed JSON") from exc

        try:
            return AnalysisResult(
                summary=str(data["summary"]),
                claims=[str(c) for c in data.get("claims", [])],
                credibility_score=float(data.get("credibility_score", 0.0)),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=str(data.get("reasoning", "")),
                flagged=bool(data.get("flagged", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError("AI response missing required fields") from exc
