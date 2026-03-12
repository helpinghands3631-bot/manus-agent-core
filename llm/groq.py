"""
llm/groq.py
------------
GroqLLM: Full xAI Grok LLM integration for Manus agents.

Now powered by LiteLLM for automatic Opik tracing. Every call to
`complete()` or `stream()` is traced in the Comet/Opik UI.

Supports:
  - grok-beta / grok-2-latest (latest Grok models)
  - grok-vision-beta (vision-enabled Grok)
  - Streaming responses
  - Function calling
  - Token counting
  - Error retry with exponential backoff
  - Automatic Opik tracing via LiteLLM callbacks

Usage:
    llm = GroqLLM(api_key="gsk_...")
    response = await llm.complete(messages)
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Optional

import litellm

from exceptions import LLMError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMResponse:
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[LLMUsage] = None
    function_call: Optional[Dict] = None


class GroqLLM:
    """
    xAI Grok LLM client for Manus agents.

    Uses LiteLLM as the universal proxy layer, which provides:
    - Automatic Opik tracing of every LLM call
    - Consistent API across providers (Groq, xAI, OpenAI, Anthropic)
    - Built-in retry logic and error handling

    Environment variables:
        GROQ_API_KEY:  Your Groq API key (required)
        LLM_BASE_URL:  Override base URL (default: https://api.x.ai/v1)
        LLM_MODEL:     Default model (default: grok-2-latest)
    """

    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-2-latest"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY or XAI_API_KEY is required")

        self.base_url = base_url or os.getenv("LLM_BASE_URL", self.DEFAULT_BASE_URL)
        self.model = model or os.getenv("LLM_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout
        self.max_retries = max_retries

        # Set LiteLLM API base for routing
        litellm.api_base = self.base_url

        logger.info("GroqLLM initialized (LiteLLM backend)", extra={
            "model": self.model,
            "base_url": self.base_url,
        })

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        prompt_version: Optional[str] = None,
        agent_name: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Send messages to Grok and get a response.

        Args:
            messages:       List of {"role": ..., "content": ...} dicts.
            temperature:    Sampling temperature (0.0 - 2.0).
            max_tokens:     Max completion tokens (default: model-specific).
            tools:          OpenAI function-calling tool schemas.
            tool_choice:    "auto", "none", or {"type": "function", "function": {"name": "..."}}.
            prompt_version: Version tag for Opik trace metadata.
            agent_name:     Agent name for Opik trace metadata.

        Returns:
            LLMResponse with content, usage, optional function_call.

        Raises:
            LLMError: On API errors or max retries exceeded.
        """
        # Build Opik metadata for tracing
        metadata = {
            "opik": {
                "tags": ["manus-agent-core", self.model],
            }
        }
        if prompt_version:
            metadata["opik"]["prompt_version"] = prompt_version
        if agent_name:
            metadata["opik"]["agent_name"] = agent_name

        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "api_key": self.api_key,
            "api_base": self.base_url,
            "metadata": metadata,
            "timeout": self.timeout,
            "num_retries": self.max_retries,
        }
        if max_tokens:
            call_kwargs["max_tokens"] = max_tokens
        if tools:
            call_kwargs["tools"] = tools
            call_kwargs["tool_choice"] = tool_choice or "auto"

        call_kwargs.update(kwargs)

        try:
            response = await litellm.acompletion(**call_kwargs)
            return self._parse_response(response)

        except litellm.exceptions.APIError as exc:
            raise LLMError(f"LiteLLM API error: {exc}")
        except litellm.exceptions.Timeout as exc:
            raise LLMError(f"LiteLLM timeout: {exc}")
        except Exception as exc:
            raise LLMError(f"LiteLLM error: {type(exc).__name__}: {exc}")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from Grok in real-time via LiteLLM.

        Yields:
            String chunks as they arrive from the API.
        """
        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "api_key": self.api_key,
            "api_base": self.base_url,
            "timeout": self.timeout,
        }
        if max_tokens:
            call_kwargs["max_tokens"] = max_tokens
        call_kwargs.update(kwargs)

        try:
            response = await litellm.acompletion(**call_kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
        except Exception as exc:
            raise LLMError(f"LiteLLM stream error: {type(exc).__name__}: {exc}")

    def _parse_response(self, response) -> LLMResponse:
        """Parse LiteLLM response into LLMResponse."""
        choice = response.choices[0]
        message = choice.message

        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        function_call = None
        if hasattr(message, "tool_calls") and message.tool_calls:
            function_call = {
                "name": message.tool_calls[0].function.name,
                "arguments": message.tool_calls[0].function.arguments,
            }

        return LLMResponse(
            content=message.content or "",
            model=response.model,
            finish_reason=choice.finish_reason,
            usage=usage,
            function_call=function_call,
        )

    async def close(self):
        """Close the client (no-op for LiteLLM, kept for interface compatibility)."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
