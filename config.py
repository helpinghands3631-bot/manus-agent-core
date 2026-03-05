"""
config.py
---------
AgentConfig: Central configuration for Manus agents.
All settings can be loaded from environment variables or set explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for BaseAgent and all subcomponents."""

    # LLM settings
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "grok-beta"))
    llm_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    llm_base_url: Optional[str] = field(default_factory=lambda: os.getenv("GROQ_BASE_URL"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))

    # Agent execution
    max_steps: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_STEPS", "25")))
    tool_timeout_secs: float = field(default_factory=lambda: float(os.getenv("TOOL_TIMEOUT_SECS", "30.0")))

    # Memory
    memory_window: int = field(default_factory=lambda: int(os.getenv("AGENT_MEMORY_WINDOW", "10")))
    long_term_memory_path: str = field(default_factory=lambda: os.getenv("AGENT_LONG_TERM_PATH", "./data/memory.json"))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("AGENT_LOG_LEVEL", "INFO"))
    log_to_file: bool = field(default_factory=lambda: os.getenv("AGENT_LOG_TO_FILE", "false").lower() == "true")
    log_file_path: str = field(default_factory=lambda: os.getenv("AGENT_LOG_FILE", "./logs/agent.jsonl"))

    # Tools
    code_exec_allowed: bool = field(default_factory=lambda: os.getenv("CODE_EXEC_ALLOWED", "true").lower() == "true")
    web_search_api_key: Optional[str] = field(default_factory=lambda: os.getenv("WEB_SEARCH_API_KEY"))

    # Optional: Admin/monitoring
    admin_chat_id: Optional[str] = field(default_factory=lambda: os.getenv("ADMIN_CHAT_ID"))

    def __post_init__(self):
        """Validate required settings."""
        if self.llm_provider == "groq" and not self.llm_api_key:
            raise ValueError("GROQ_API_KEY is required when using Groq LLM")
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        if self.memory_window < 1:
            raise ValueError("memory_window must be >= 1")
