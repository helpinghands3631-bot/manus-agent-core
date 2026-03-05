"""Base tool interface for Manus Agent Core."""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result from tool execution."""
    
    success: bool
    output: Any
    error: str | None = None
    metadata: dict[str, Any] | None = None


class BaseTool(ABC):
    """Abstract base class for all agent tools.
    
    All tools must implement:
    - name: Unique tool identifier
    - description: What the tool does
    - execute: Main tool logic
    - get_schema: OpenAI function calling schema
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM understanding."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific arguments
        
        Returns:
            ToolResult with output or error
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Get OpenAI function calling schema.
        
        Returns:
            OpenAI-compatible function schema dict
        """
        pass
    
    def __str__(self) -> str:
        return f"Tool({self.name})"
    
    def __repr__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description}')"
