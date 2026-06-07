"""Unit tests for the LLM provider layer."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from supervisor.config import Settings
from supervisor.decisions import (
    DraftReport,
    ResearchResult,
    ReviewResult,
    SupervisorDecision,
)
from supervisor.providers import (
    AnthropicProvider,
    FakeProvider,
    LLMError,
    OpenAIProvider,
    ProviderRefused,
    ProviderUnavailable,
    build_provider,
    default_fake_provider,
)


class TestFakeProvider:
    def test_string_response(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue("hello")
        out = fake_provider.complete([{"role": "user", "content": "hi"}])
        assert out == "hello"

    def test_dict_validated_to_model(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(
            {
                "selected_agents": ["writer"],
                "execution_order": ["writer"],
                "reasoning": "r",
            }
        )
        out = fake_provider.complete(
            [{"role": "user", "content": "x"}], response_model=SupervisorDecision
        )
        assert isinstance(out, SupervisorDecision)
        assert out.selected_agents == ["writer"]

    def test_model_returned_as_is(self, fake_provider: FakeProvider) -> None:
        dec = SupervisorDecision(
            selected_agents=["writer"],
            execution_order=["writer"],
            reasoning="r",
        )
        fake_provider.queue(dec)
        out = fake_provider.complete(
            [{"role": "user", "content": "x"}], response_model=SupervisorDecision
        )
        assert out is dec

    def test_string_json_validated(self, fake_provider: FakeProvider) -> None:
        js = json.dumps(
            {
                "selected_agents": ["writer"],
                "execution_order": ["writer"],
                "reasoning": "r",
            }
        )
        fake_provider.queue(js)
        out = fake_provider.complete(
            [{"role": "user", "content": "x"}], response_model=SupervisorDecision
        )
        assert isinstance(out, SupervisorDecision)

    def test_queue_many(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue_many(["a", "b"])
        assert fake_provider.remaining() == 2

    def test_empty_provider_raises(self, fake_provider: FakeProvider) -> None:
        with pytest.raises(LLMError, match="out of queued"):
            fake_provider.complete([{"role": "user", "content": "x"}])

    def test_invalid_response_type_raises(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(123)
        with pytest.raises(LLMError):
            fake_provider.complete(
                [{"role": "user", "content": "x"}],
                response_model=SupervisorDecision,
            )

    def test_records_calls(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(json.dumps({"topic": "x", "findings": ["a"]}))
        fake_provider.complete(
            [{"role": "user", "content": "hi"}],
            response_model=ResearchResult,
            temperature=0.5,
        )
        assert len(fake_provider.calls) == 1
        assert fake_provider.calls[0]["response_model"] == "ResearchResult"
        assert fake_provider.calls[0]["temperature"] == 0.5


class TestBuildProvider:
    def test_fake(self, test_settings: Settings) -> None:
        assert isinstance(build_provider(test_settings), FakeProvider)

    def test_openai_missing_key_raises(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = ""
        with pytest.raises(ProviderRefused):
            OpenAIProvider(test_settings)

    def test_anthropic_missing_key_raises(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = ""
        with pytest.raises(ProviderRefused):
            AnthropicProvider(test_settings)

    def test_unknown_provider(self, test_settings: Settings) -> None:
        object.__setattr__(test_settings, "llm_provider", "nope")
        with pytest.raises(LLMError, match="Unknown"):
            build_provider(test_settings)


class TestOpenAIProvider:
    def test_text_completion(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-test"
        with respx.mock(base_url="https://api.openai.com/v1") as mock:
            mock.post("/chat/completions").mock(
                return_value=httpx.Response(
                    200, json={"choices": [{"message": {"content": "hello"}}]}
                )
            )
            p = OpenAIProvider(test_settings)
            out = p.complete([{"role": "user", "content": "hi"}])
        assert out == "hello"

    def test_structured_completion(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-test"
        js = json.dumps(
            {
                "selected_agents": ["writer"],
                "execution_order": ["writer"],
                "reasoning": "r",
            }
        )
        with respx.mock(base_url="https://api.openai.com/v1") as mock:
            mock.post("/chat/completions").mock(
                return_value=httpx.Response(200, json={"choices": [{"message": {"content": js}}]})
            )
            p = OpenAIProvider(test_settings)
            out = p.complete(
                [{"role": "user", "content": "x"}],
                response_model=SupervisorDecision,
            )
        assert isinstance(out, SupervisorDecision)

    def test_5xx_raises_unavailable(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-test"
        with respx.mock(base_url="https://api.openai.com/v1") as mock:
            mock.post("/chat/completions").mock(return_value=httpx.Response(500, text="boom"))
            p = OpenAIProvider(test_settings)
            with pytest.raises(ProviderUnavailable):
                p.complete([{"role": "user", "content": "x"}])

    def test_4xx_raises_refused(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-test"
        with respx.mock(base_url="https://api.openai.com/v1") as mock:
            mock.post("/chat/completions").mock(return_value=httpx.Response(400, text="bad"))
            p = OpenAIProvider(test_settings)
            with pytest.raises(ProviderRefused):
                p.complete([{"role": "user", "content": "x"}])

    def test_custom_base_url(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-test"
        test_settings.llm_base_url = "https://proxy.example.com/v1"
        with respx.mock(base_url="https://proxy.example.com/v1") as mock:
            mock.post("/chat/completions").mock(
                return_value=httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
            )
            p = OpenAIProvider(test_settings)
            out = p.complete([{"role": "user", "content": "x"}])
        assert out == "ok"


class TestAnthropicProvider:
    def test_text_completion(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-ant-test"
        with respx.mock(base_url="https://api.anthropic.com/v1") as mock:
            mock.post("/messages").mock(
                return_value=httpx.Response(
                    200,
                    json={"content": [{"type": "text", "text": "hi from claude"}]},
                )
            )
            p = AnthropicProvider(test_settings)
            out = p.complete([{"role": "user", "content": "hi"}])
        assert out == "hi from claude"

    def test_system_message_extracted(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-ant-test"
        with respx.mock(base_url="https://api.anthropic.com/v1") as mock:
            route = mock.post("/messages").mock(
                return_value=httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})
            )
            p = AnthropicProvider(test_settings)
            p.complete(
                [
                    {"role": "system", "content": "you are helpful"},
                    {"role": "user", "content": "hi"},
                ]
            )
        request = route.calls.last.request
        body = json.loads(request.content)
        assert body["system"] == "you are helpful"
        assert body["messages"] == [{"role": "user", "content": "hi"}]

    def test_structured_via_tool_use(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-ant-test"
        with respx.mock(base_url="https://api.anthropic.com/v1") as mock:
            mock.post("/messages").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "content": [
                            {
                                "type": "tool_use",
                                "input": {
                                    "selected_agents": ["writer"],
                                    "execution_order": ["writer"],
                                    "reasoning": "r",
                                },
                            }
                        ]
                    },
                )
            )
            p = AnthropicProvider(test_settings)
            out = p.complete(
                [{"role": "user", "content": "x"}],
                response_model=SupervisorDecision,
            )
        assert isinstance(out, SupervisorDecision)
        assert out.selected_agents == ["writer"]

    def test_no_tool_use_raises(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-ant-test"
        with respx.mock(base_url="https://api.anthropic.com/v1") as mock:
            mock.post("/messages").mock(
                return_value=httpx.Response(
                    200, json={"content": [{"type": "text", "text": "no tool"}]}
                )
            )
            p = AnthropicProvider(test_settings)
            with pytest.raises(ProviderRefused):
                p.complete(
                    [{"role": "user", "content": "x"}],
                    response_model=SupervisorDecision,
                )

    def test_5xx_raises(self, test_settings: Settings) -> None:
        test_settings.llm_api_key = "sk-ant-test"
        with respx.mock(base_url="https://api.anthropic.com/v1") as mock:
            mock.post("/messages").mock(return_value=httpx.Response(503, text="down"))
            p = AnthropicProvider(test_settings)
            with pytest.raises(ProviderUnavailable):
                p.complete([{"role": "user", "content": "x"}])


class TestDefaultFakeProvider:
    def test_seeds_decision_draft_and_review(self) -> None:
        p = default_fake_provider()
        assert p.remaining() == 3

        decision = p.complete([{"role": "user", "content": "x"}], response_model=SupervisorDecision)
        assert isinstance(decision, SupervisorDecision)
        assert decision.selected_agents

        draft = p.complete([{"role": "user", "content": "x"}], response_model=DraftReport)
        assert isinstance(draft, DraftReport)
        assert draft.title

        review = p.complete([{"role": "user", "content": "x"}], response_model=ReviewResult)
        assert isinstance(review, ReviewResult)
        assert review.is_sufficient is True
        assert p.remaining() == 0
