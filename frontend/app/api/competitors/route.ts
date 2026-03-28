from __future__ import annotations
import time
import uuid
from enum import StrEnum
from typing import TypeVar
import structlog
from groq import APIError, AsyncGroq
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from app.config import settings
from app.shared.exceptions import LLMException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class GroqModel(StrEnum):
    PRIMARY   = "llama-3.3-70b-versatile"
    FAST      = "llama-3.1-8b-instant"
    REASONING = "deepseek-r1-distill-llama-70b"


class GroqClient:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(APIError),
    )
    async def complete(
        self,
        *,
        model: GroqModel,
        system_prompt: str | None,
        user_prompt: str,
        output_schema: type[T],
        lang: LangContext | None = None,
        trace_id: str | None = None,
        company_id: str | None = None,
        temperature: float = 0.7,
    ) -> T:
        _trace = trace_id or str(uuid.uuid4())
        start = time.monotonic()

        is_deepseek = model == GroqModel.REASONING
        if is_deepseek:
            temperature = 0.6
            messages = [{"role": "user", "content": user_prompt}]
        else:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

        try:
            response = await self._client.chat.completions.create(
                model=model.value,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=30,
            )
        except APIError as e:
            logger.error("groq_api_error", trace_id=_trace, error=str(e), model=model.value)
            raise LLMException(f"LLM call failed: {e}") from e

        elapsed = round((time.monotonic() - start) * 1000)
        content = response.choices[0].message.content

        logger.info(
            "llm_call_complete",
            trace_id=_trace,
            company_id=company_id,
            model=model.value,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=elapsed,
        )

        try:
            return output_schema.model_validate_json(content)
        except Exception as e:
            logger.error("llm_parse_error", trace_id=_trace, raw=content, error=str(e))
            raise LLMException(f"Failed to parse LLM response: {e}") from e
