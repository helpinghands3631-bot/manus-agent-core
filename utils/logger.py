"""Structured logging with JSON output, step traces, and token counting for Manus Agent Core."""

import json
import logging
import sys
from datetime import datetime
from typing import Any
from pathlib import Path


class AgentLogger:
    """Structured logger for agent execution with JSON output and token tracking.
    
    Features:
    - Structured JSON logs
    - Step-by-step execution traces
    - Token usage tracking
    - Multiple output formats (console, file)
    - Context-aware logging
    """
    
    def __init__(
        self,
        name: str = "manus-agent",
        log_level: str = "INFO",
        log_to_file: bool = False,
        log_file_path: str | Path = "./logs/agent.jsonl"
    ):
        """Initialize agent logger.
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_to_file: Whether to log to file
            log_file_path: Path to log file (JSONL format)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Token tracking
        self._total_tokens = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        
        # Step tracking
        self._current_step = 0
        self._step_history: list[dict] = []
        
        # Configure console handler with JSON formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # Configure file handler if requested
        if log_to_file:
            log_file_path = Path(log_file_path)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
    
    def _log_structured(self, level: str, message: str, **kwargs) -> None:
        """Log with structured data.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data
        """
        extra = {
            "structured_data": {
                "timestamp": datetime.now().isoformat(),
                "step": self._current_step,
                **kwargs
            }
        }
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log_structured("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log_structured("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log_structured("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log_structured("ERROR", message, **kwargs)
    
    def log_step(self, action: str, thought: str = "", observation: str = "", **kwargs) -> None:
        """Log an agent reasoning step.
        
        Args:
            action: Action taken
            thought: Agent's reasoning
            observation: Result of action
            **kwargs: Additional step data
        """
        self._current_step += 1
        
        step_data = {
            "step_number": self._current_step,
            "action": action,
            "thought": thought,
            "observation": observation,
            **kwargs
        }
        
        self._step_history.append(step_data)
        self.info(
            f"Step {self._current_step}: {action}",
            step_type="reasoning",
            **step_data
        )
    
    def log_tokens(self, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        """Log token usage.
        
        Args:
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion
            total_tokens: Total tokens used
        """
        self._prompt_tokens += prompt_tokens
        self._completion_tokens += completion_tokens
        self._total_tokens += total_tokens
        
        self.info(
            f"Token usage: {total_tokens} total",
            event_type="token_usage",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cumulative_total=self._total_tokens
        )
    
    def get_token_stats(self) -> dict[str, int]:
        """Get cumulative token statistics.
        
        Returns:
            Dict with token counts
        """
        return {
            "total_tokens": self._total_tokens,
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens
        }
    
    def get_step_history(self) -> list[dict]:
        """Get full step-by-step execution history.
        
        Returns:
            List of step data dicts
        """
        return self._step_history.copy()
    
    def reset_stats(self) -> None:
        """Reset token and step counters."""
        self._total_tokens = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._current_step = 0
        self._step_history.clear()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record
        
        Returns:
            JSON string
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # Add structured data if present
        if hasattr(record, "structured_data"):
            log_data.update(record.structured_data)
        
        return json.dumps(log_data)


def get_logger(
    name: str = "manus-agent",
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str | Path = "./logs/agent.jsonl"
) -> AgentLogger:
    """Get or create an agent logger.
    
    Args:
        name: Logger name
        log_level: Logging level
        log_to_file: Enable file logging
        log_file_path: Log file path
    
    Returns:
        Configured AgentLogger instance
    """
    return AgentLogger(
        name=name,
        log_level=log_level,
        log_to_file=log_to_file,
        log_file_path=log_file_path
    )
