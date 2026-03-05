"""
llm/groq.py
------------
GroqLLM: Full xAI Grok LLM integration for Manus agents.

Supports:
  - grok-beta (latest Grok model)
  - grok-vision-beta (vision-enabled Grok)
  - Streaming responses
  - Function calling
  - Token counting
  - Error retry with exponential backoff

Usage:
    llm = GroqLLM(api_key="gsk_...")
    response = await llm.complete(messages)
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Optional

import httpx

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

    Connects to the official Groq API (https://api.groq.com/openai/v1/chat/completions)
    which powers xAI's Grok models.

    Environment variables:
        GROQ_API_KEY:  Your Groq API key (required)
        GROQ_BASE_URL: Override base URL (default: https://api.groq.com/openai/v1)
        GROQ_MODEL:    Default model (default: grok-beta)
    """

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "grok-beta"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")

        self.base_url = base_url or os.getenv("GROQ_BASE_URL", self.DEFAULT_BASE_URL)
        self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        logger.info("GroqLLM initialized", extra={"model": self.model, "base_url": self.base_url})

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Send messages to Grok and get a response.

        Args:
            messages:     List of {"role": ..., "content": ...} dicts.
            temperature:  Sampling temperature (0.0 - 2.0).
            max_tokens:   Max completion tokens (default: model-specific).
            tools:        OpenAI function-calling tool schemas.
            tool_choice:  "auto", "none", or {"type": "function", "function": {"name": "..."}}.

        Returns:
            LLMResponse with content, usage, optional function_call.

        Raises:
            LLMError: On API errors or max retries exceeded.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

        payload.update(kwargs)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return self._parse_response(data)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503, 504):
                    # Rate limit or server error — retry with backoff
                    if attempt < self.max_retries:
                        delay = 2 ** attempt
                        logger.warning(
                            f"API error {exc.response.status_code}, retry {attempt}/{self.max_retries} after {delay}s",
                            extra={"status": exc.response.status_code},
                        )
                        await asyncio.sleep(delay)
                        continue
                raise LLMError(f"Groq API error: {exc.response.status_code} - {exc.response.text}")

            except httpx.RequestError as exc:
                raise LLMError(f"Groq request error: {exc}")

        raise LLMError(f"Max retries ({self.max_retries}) exceeded")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from Grok in real-time.

        Yields:
            String chunks as they arrive from the API.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(chunk)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError) as exc:
                        logger.warning(f"Failed to parse stream chunk: {exc}")
                        continue

    def _parse_response(self, data: Dict) -> LLMResponse:
        """Parse Groq API JSON response into LLMResponse."""
        choice = data["choices"][0]
        message = choice["message"]

        usage = None
        if "usage" in data:
            usage = LLMUsage(
                prompt_tokens=data["usage"]["prompt_tokens"],
                completion_tokens=data["usage"]["completion_tokens"],
                total_tokens=data["usage"]["total_tokens"],
            )

        function_call = None
        if "tool_calls" in message and message["tool_calls"]:
            function_call = {
                "name": message["tool_calls"][0]["function"]["name"],
                "arguments": message["tool_calls"][0]["function"]["arguments"],
            }

        return LLMResponse(
            content=message.get("content", ""),
            model=data["model"],
            finish_reason=choice.get("finish_reason"),
            usage=usage,
            function_call=function_call,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
