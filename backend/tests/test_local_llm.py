import json

import httpx
import pytest

from app.local_llm import (
    LocalLLMClient,
    LocalModelUnavailableError,
)


def build_client(handler) -> LocalLLMClient:
    return LocalLLMClient(
        base_url="http://127.0.0.1:1234/api/v1",
        model="qwen/qwen3.6-27b",
        timeout_seconds=10,
        context_length=32_768,
        max_output_tokens=800,
        reasoning="off",
        transport=httpx.MockTransport(handler),
    )


def test_readiness_reports_a_loaded_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/models"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "key": "qwen/qwen3.6-27b",
                        "loaded_instances": [{"id": "qwen/qwen3.6-27b"}],
                    }
                ]
            },
        )

    readiness = build_client(handler).check_readiness()

    assert readiness.ready is True
    assert "loaded and ready" in readiness.detail


def test_readiness_explains_when_the_model_is_not_loaded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "key": "qwen/qwen3.6-27b",
                        "loaded_instances": [],
                    }
                ]
            },
        )

    readiness = build_client(handler).check_readiness()

    assert readiness.ready is False
    assert "installed but not loaded" in readiness.detail


def test_generate_returns_only_message_output_and_inference_stats():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/chat"
        request_body = json.loads(request.content)
        assert request_body["model"] == "qwen/qwen3.6-27b"
        assert request_body["reasoning"] == "off"
        assert request_body["store"] is False
        assert request_body["context_length"] == 32_768
        return httpx.Response(
            200,
            json={
                "output": [
                    {"type": "reasoning", "content": "Internal reasoning"},
                    {"type": "message", "content": "The answer is supported [Page 2]."},
                ],
                "stats": {
                    "input_tokens": 120,
                    "total_output_tokens": 18,
                    "reasoning_output_tokens": 0,
                    "tokens_per_second": 24.5,
                    "time_to_first_token_seconds": 0.8,
                },
            },
        )

    result = build_client(handler).generate(
        system_prompt="Use only supplied evidence.",
        user_prompt="Context and question",
    )

    assert result.text == "The answer is supported [Page 2]."
    assert result.input_tokens == 120
    assert result.output_tokens == 18
    assert result.reasoning_tokens == 0
    assert result.tokens_per_second == 24.5
    assert result.time_to_first_token_seconds == 0.8


def test_generate_translates_server_failures_into_a_domain_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "model unavailable"})

    with pytest.raises(LocalModelUnavailableError, match="local model request failed"):
        build_client(handler).generate(
            system_prompt="Use only supplied evidence.",
            user_prompt="Context and question",
        )
