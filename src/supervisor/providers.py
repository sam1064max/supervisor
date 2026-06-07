"""LLM provider abstraction.

The Supervisor depends on a small ``LLMProvider`` Protocol rather than a
specific SDK. Three implementations are provided:

* :class:`FakeProvider` - offline, deterministic, default for tests / CI
* :class:`OpenAIProvider` - ``httpx`` + JSON-schema structured outputs
* :class:`AnthropicProvider` - ``httpx`` + tool-use structured outputs

The provider is selected via :attr:`Settings.llm_provider`. All HTTP calls
are wrapped in ``httpx`` so they can be mocked with ``respx`` in tests.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel

from supervisor.config import Settings, get_settings
from supervisor.logging_setup import get_logger

logger = get_logger(__name__)


class LLMError(RuntimeError):
    """Base class for provider failures."""


class ProviderUnavailable(LLMError):
    """The provider is unreachable or returned 5xx."""


class ProviderRefused(LLMError):
    """The provider returned 4xx; the request is malformed."""


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface every provider must implement."""

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_model: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str | BaseModel: ...


# ----------------------------------------------------------------------
# Fake provider
# ----------------------------------------------------------------------


class FakeProvider:
    """Deterministic offline provider for tests and CI.

    Responses are queued in advance and consumed in FIFO order. The provider
    validates that structured responses match the requested Pydantic model.
    """

    def __init__(self, responses: list[Any] | None = None) -> None:
        self._responses: list[Any] = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    def queue(self, response: Any) -> None:
        """Append a response to the queue."""
        self._responses.append(response)

    def queue_many(self, responses: list[Any]) -> None:
        self._responses.extend(responses)

    def remaining(self) -> int:
        return len(self._responses)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_model: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str | BaseModel:
        self.calls.append(
            {
                "messages": messages,
                "response_model": response_model.__name__ if response_model else None,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if not self._responses:
            raise LLMError("FakeProvider ran out of queued responses.")
        raw = self._responses.pop(0)
        if response_model is None:
            return raw if isinstance(raw, str) else json.dumps(raw)
        if isinstance(raw, response_model):
            return raw
        if isinstance(raw, BaseModel):
            return raw
        if isinstance(raw, dict):
            return response_model.model_validate(raw)
        if isinstance(raw, str):
            return response_model.model_validate_json(raw)
        raise LLMError(
            f"FakeProvider cannot convert {type(raw).__name__} to {response_model.__name__}",
        )


# ----------------------------------------------------------------------
# OpenAI
# ----------------------------------------------------------------------


class OpenAIProvider:
    """OpenAI provider using ``httpx`` + JSON-schema structured outputs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.llm_api_key:
            raise ProviderRefused("SUPERVISOR_LLM_API_KEY is required for the OpenAI provider.")
        self._base_url = settings.llm_base_url or "https://api.openai.com/v1"
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=settings.llm_timeout_s,
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_model: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str | BaseModel:
        payload: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_model is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                    "strict": True,
                },
            }
        response = self._client.post("/chat/completions", json=payload)
        if response.status_code >= 500:
            raise ProviderUnavailable(f"openai 5xx: {response.status_code}")
        if response.status_code >= 400:
            raise ProviderRefused(f"openai 4xx: {response.status_code} {response.text[:200]}")
        data = response.json()
        content: str = data["choices"][0]["message"]["content"]
        if response_model is None:
            return content
        parsed: BaseModel = response_model.model_validate_json(content)
        return parsed

    def close(self) -> None:
        self._client.close()


# ----------------------------------------------------------------------
# Anthropic
# ----------------------------------------------------------------------


class AnthropicProvider:
    """Anthropic provider using ``httpx`` + tool-use for structured outputs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.llm_api_key:
            raise ProviderRefused("SUPERVISOR_LLM_API_KEY is required for the Anthropic provider.")
        self._base_url = settings.llm_base_url or "https://api.anthropic.com/v1"
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=settings.llm_timeout_s,
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_model: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str | BaseModel:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_parts = [
            {"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"
        ]
        payload: dict[str, Any] = {
            "model": self._settings.llm_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_parts,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if response_model is not None:
            tool_name = f"submit_{response_model.__name__}"
            payload["tools"] = [
                {
                    "name": tool_name,
                    "description": f"Submit a structured {response_model.__name__} response.",
                    "input_schema": response_model.model_json_schema(),
                }
            ]
            payload["tool_choice"] = {"type": "tool", "name": tool_name}
        response = self._client.post("/messages", json=payload)
        if response.status_code >= 500:
            raise ProviderUnavailable(f"anthropic 5xx: {response.status_code}")
        if response.status_code >= 400:
            raise ProviderRefused(f"anthropic 4xx: {response.status_code} {response.text[:200]}")
        data = response.json()
        if response_model is None:
            return "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
        for block in data.get("content", []):
            if block.get("type") == "tool_use":
                return response_model.model_validate(block["input"])
        raise ProviderRefused("anthropic did not return a tool_use block for structured output.")

    def close(self) -> None:
        self._client.close()


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def build_provider(settings: Settings | None = None) -> LLMProvider:
    """Construct the configured provider."""
    settings = settings or get_settings()
    logger.info("provider.build", provider=settings.llm_provider, model=settings.llm_model)
    if settings.llm_provider == "fake":
        return FakeProvider()
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings)
    raise LLMError(f"Unknown provider: {settings.llm_provider}")


def default_fake_provider() -> FakeProvider:
    """Return a ``FakeProvider`` pre-queued with sensible demo responses.

    Useful for the offline CLI / quickstart: a single ``supervisor run``
    command without API keys or test fixtures still produces a coherent
    end-to-end answer.
    """
    from supervisor.decisions import (
        DraftReport,
        ReviewResult,
        SupervisorDecision,
    )

    decision = SupervisorDecision(
        selected_agents=["calculator", "writer"],
        execution_order=["calculator", "writer"],
        requires_parallel_execution=False,
        reasoning="offline demo default",
    )
    draft = DraftReport(
        title="Answer",
        summary="Offline demo answer produced without an LLM call.",
        body=(
            "[offline demo] The Supervisor routed your query to the most "
            "appropriate specialists and produced this placeholder response. "
            "Set SUPERVISOR_LLM_PROVIDER=openai (or anthropic) and provide "
            "an API key to get a real model-generated answer."
        ),
        citations=[],
    )
    review = ReviewResult(
        is_sufficient=True,
        feedback="ok",
        confidence=1.0,
        issues=[],
    )
    provider = FakeProvider()
    provider.queue_many([decision, draft, review])
    return provider
