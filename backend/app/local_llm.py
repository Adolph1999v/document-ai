"""Local LM Studio boundary used for readiness checks and answer generation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx

from .config import settings


class LocalModelUnavailableError(RuntimeError):
    """The configured local model server cannot currently handle requests."""


class LocalModelResponseError(RuntimeError):
    """The local model server returned a response without usable answer text."""


@dataclass(frozen=True)
class LocalModelReadiness:
    """A dependency check result suitable for the API readiness endpoint."""

    ready: bool
    detail: str


@dataclass(frozen=True)
class LocalModelResult:
    """Generated text plus the inference measurements reported by LM Studio."""

    text: str
    input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    tokens_per_second: float | None
    time_to_first_token_seconds: float | None


def _optional_number(value: Any, number_type: type[int | float]) -> int | float | None:
    """Convert an optional LM Studio statistic without trusting its JSON type blindly."""

    if value is None or isinstance(value, bool):
        return None
    try:
        return number_type(value)
    except (TypeError, ValueError):
        return None


class LocalLLMClient:
    """Small synchronous client for LM Studio's loopback-only native REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int,
        context_length: int,
        max_output_tokens: int,
        reasoning: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.context_length = context_length
        self.max_output_tokens = max_output_tokens
        self.reasoning = reasoning
        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/",
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def check_readiness(self) -> LocalModelReadiness:
        """Confirm that LM Studio is reachable and the configured model is loaded."""

        try:
            response = self._client.get("models")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return LocalModelReadiness(
                ready=False,
                detail="LM Studio is unavailable. Start its local server on the configured URL.",
            )

        models = payload.get("models")
        if not isinstance(models, list):
            return LocalModelReadiness(
                ready=False,
                detail="LM Studio returned an unexpected model-list response.",
            )

        configured_model = next(
            (
                model
                for model in models
                if isinstance(model, dict) and model.get("key") == self.model
            ),
            None,
        )
        if configured_model is None:
            return LocalModelReadiness(
                ready=False,
                detail=f"The configured local model {self.model!r} is not installed.",
            )

        loaded_instances = configured_model.get("loaded_instances")
        if not isinstance(loaded_instances, list) or not loaded_instances:
            return LocalModelReadiness(
                ready=False,
                detail=f"The local model {self.model!r} is installed but not loaded.",
            )

        return LocalModelReadiness(
            ready=True,
            detail=f"The local model {self.model!r} is loaded and ready.",
        )

    def generate(self, *, system_prompt: str, user_prompt: str) -> LocalModelResult:
        """Generate one stateless answer and preserve useful local inference measurements."""

        request_body = {
            "model": self.model,
            "system_prompt": system_prompt,
            "input": user_prompt,
            "stream": False,
            "store": False,
            "temperature": 0.2,
            "max_output_tokens": self.max_output_tokens,
            "reasoning": self.reasoning,
            "context_length": self.context_length,
        }

        try:
            response = self._client.post("chat", json=request_body)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as error:
            raise LocalModelUnavailableError(
                "The local model timed out. Check LM Studio and the configured timeout."
            ) from error
        except httpx.HTTPError as error:
            raise LocalModelUnavailableError(
                "The local model request failed. Check that LM Studio and Qwen are ready."
            ) from error
        except ValueError as error:
            raise LocalModelResponseError(
                "The local model returned a response that was not valid JSON."
            ) from error

        output = payload.get("output")
        if not isinstance(output, list):
            raise LocalModelResponseError("The local model response did not contain output items.")

        answer_parts = [
            item.get("content", "").strip()
            for item in output
            if isinstance(item, dict)
            and item.get("type") == "message"
            and isinstance(item.get("content"), str)
            and item.get("content", "").strip()
        ]
        if not answer_parts:
            raise LocalModelResponseError("The local model did not return a usable answer.")

        stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
        input_tokens = _optional_number(stats.get("input_tokens"), int)
        output_tokens = _optional_number(stats.get("total_output_tokens"), int)
        reasoning_tokens = _optional_number(stats.get("reasoning_output_tokens"), int)
        tokens_per_second = _optional_number(stats.get("tokens_per_second"), float)
        time_to_first_token = _optional_number(
            stats.get("time_to_first_token_seconds"),
            float,
        )

        return LocalModelResult(
            text="\n\n".join(answer_parts),
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            reasoning_tokens=reasoning_tokens if isinstance(reasoning_tokens, int) else None,
            tokens_per_second=(tokens_per_second if isinstance(tokens_per_second, float) else None),
            time_to_first_token_seconds=(
                time_to_first_token if isinstance(time_to_first_token, float) else None
            ),
        )


@lru_cache(maxsize=1)
def get_local_llm_client() -> LocalLLMClient:
    """Reuse one local HTTP client and its connection pool for the process lifetime."""

    return LocalLLMClient(
        base_url=settings.local_llm_base_url,
        model=settings.local_llm_model,
        timeout_seconds=settings.local_llm_timeout_seconds,
        context_length=settings.local_llm_context_length,
        max_output_tokens=settings.local_llm_max_output_tokens,
        reasoning=settings.local_llm_reasoning,
    )
