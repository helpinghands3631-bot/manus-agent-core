"""Custom exceptions for Manus Agent Core."""


class ManusAgentError(Exception):
    """Base exception for all Manus agent errors."""
    pass


class AgentMaxStepsError(ManusAgentError):
    """Raised when agent exceeds maximum reasoning steps."""
    
    def __init__(self, max_steps: int):
        self.max_steps = max_steps
        super().__init__(f"Agent exceeded maximum steps: {max_steps}")


class AgentParseError(ManusAgentError):
    """Raised when agent fails to parse LLM response."""
    
    def __init__(self, response: str, reason: str = ""):
        self.response = response
        self.reason = reason
        msg = f"Failed to parse agent response: {reason}" if reason else "Failed to parse agent response"
        super().__init__(msg)


class ToolNotFoundError(ManusAgentError):
    """Raised when requested tool is not registered."""
    
    def __init__(self, tool_name: str, available_tools: list[str] | None = None):
        self.tool_name = tool_name
        self.available_tools = available_tools
        msg = f"Tool '{tool_name}' not found"
        if available_tools:
            msg += f". Available tools: {', '.join(available_tools)}"
        super().__init__(msg)


class ToolExecutionError(ManusAgentError):
    """Raised when tool execution fails."""
    
    def __init__(self, tool_name: str, error: Exception):
        self.tool_name = tool_name
        self.original_error = error
        super().__init__(f"Tool '{tool_name}' execution failed: {str(error)}")


class LLMError(ManusAgentError):
    """Raised when LLM request fails."""
    
    def __init__(self, provider: str, error: Exception):
        self.provider = provider
        self.original_error = error
        super().__init__(f"LLM ({provider}) request failed: {str(error)}")


class ConfigurationError(ManusAgentError):
    """Raised when agent configuration is invalid."""
    pass


class MemoryError(ManusAgentError):
    """Raised when memory operations fail."""
    pass
