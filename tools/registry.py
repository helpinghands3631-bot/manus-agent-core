"""
tools/registry.py
------------------
ToolRegistry: Central registry for discovering, validating,
and executing tools in the Manus agent ecosystem.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterator, List, Optional

from exceptions import ToolNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Central store for all agent tools.

    Usage:
        registry = ToolRegistry()
        registry.register(WebSearchTool())
        result = await registry.execute("web_search", {"query": "Python"})
    """

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def register(self, tool) -> None:
        """Register a tool instance. Raises ValueError if name conflicts."""
        if not hasattr(tool, "name") or not tool.name:
            raise ValueError(f"Tool {tool!r} must have a non-empty 'name' attribute")
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info("Tool registered", extra={"tool": tool.name})

    def unregister(self, name: str) -> None:
        """Remove a tool by name."""
        self._tools.pop(name, None)
        logger.info("Tool unregistered", extra={"tool": name})

    def get(self, name: str):
        """Return a tool by name or raise ToolNotFoundError."""
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")

    def names(self) -> Iterator[str]:
        """Iterate over registered tool names."""
        yield from self._tools.keys()

    def all(self) -> List:
        """Return all registered tool instances."""
        return list(self._tools.values())

    async def execute(
        self,
        name: str,
        args: Dict[str, Any],
        timeout: Optional[float] = 30.0,
    ) -> str:
        """
        Execute a registered tool with the given arguments.

        Args:
            name:    Tool name.
            args:    Dict of keyword arguments passed to tool.run().
            timeout: Per-tool timeout in seconds (None = no timeout).

        Returns:
            String observation from the tool.

        Raises:
            ToolNotFoundError: if tool is not registered.
            asyncio.TimeoutError: if tool exceeds timeout.
        """
        tool = self.get(name)  # raises ToolNotFoundError if missing

        # Validate required params
        missing = [
            k for k, spec in tool.parameters.items()
            if spec.get("required") and k not in args
        ]
        if missing:
            return f"ERROR: Tool '{name}' missing required parameters: {missing}"

        logger.debug("Executing tool", extra={"tool": name, "args": list(args.keys())})

        try:
            coro = tool.run(**args)
            if timeout is not None:
                result = await asyncio.wait_for(coro, timeout=timeout)
            else:
                result = await coro
            return str(result)
        except asyncio.TimeoutError:
            raise
        except Exception as exc:
            logger.warning("Tool raised exception", extra={"tool": name, "error": str(exc)})
            raise

    def schemas_as_text(self) -> str:
        """
        Render all tool schemas as a human-readable string for the LLM system prompt.
        """
        if not self._tools:
            return "(no tools registered)"

        lines = []
        for tool in self._tools.values():
            lines.append(f"Tool: {tool.name}")
            lines.append(f"  Description: {tool.description}")
            if tool.parameters:
                lines.append("  Parameters:")
                for param, spec in tool.parameters.items():
                    req = "required" if spec.get("required") else "optional"
                    t = spec.get("type", "any")
                    desc = spec.get("description", "")
                    lines.append(f"    - {param} ({t}, {req}): {desc}")
            lines.append("")
        return "\n".join(lines)

    def schemas_as_openai_functions(self) -> List[Dict]:
        """
        Render all tool schemas in OpenAI function-calling format.
        """
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            k: {
                                "type": v.get("type", "string"),
                                "description": v.get("description", ""),
                            }
                            for k, v in tool.parameters.items()
                        },
                        "required": [
                            k for k, v in tool.parameters.items()
                            if v.get("required")
                        ],
                    },
                },
            })
        return schemas

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={list(self._tools.keys())})"
