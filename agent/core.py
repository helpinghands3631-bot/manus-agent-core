"""
agent/core.py
--------------
BaseAgent: The elite ReAct (Reason-Act-Observe) execution loop.

Cycle:
  1. Build prompt from system prompt + memory context + tool schemas
  2. LLM generates: Thought + Action + Action Input
  3. ToolExecutor dispatches the chosen tool
  4. Observation appended to memory
  5. Repeat until FINISH action or max_steps reached
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import AgentConfig
from events.bus import EventBus
from exceptions import AgentMaxStepsError, AgentParseError, ToolNotFoundError
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
from tools.registry import ToolRegistry
from utils.logger import get_logger
from utils.tokens import count_tokens

logger = get_logger(__name__)


@dataclass
class AgentStep:
    step: int
    thought: str
    action: str
    action_input: Any
    observation: str
    tokens_used: int = 0
    duration_ms: float = 0.0


@dataclass
class AgentResult:
    goal: str
    output: str
    success: bool
    steps: List[AgentStep] = field(default_factory=list)
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    error: Optional[str] = None

    @property
    def trace(self) -> str:
        lines = [f"Goal: {self.goal}", ""]
        for s in self.steps:
            lines.append(f"--- Step {s.step} ({s.duration_ms:.0f}ms, {s.tokens_used} tokens) ---")
            lines.append(f"Thought: {s.thought}")
            lines.append(f"Action: {s.action}")
            lines.append(f"Input: {json.dumps(s.action_input, indent=2)}")
            lines.append(f"Observation: {s.observation}")
            lines.append("")
        lines.append(f"Output: {self.output}")
        return "\n".join(lines)


SYSTEM_PROMPT = """
You are an elite autonomous AI agent. Your job is to complete the user's goal
by reasoning step-by-step and using the available tools.

For each step, you MUST respond in this EXACT format:
Thought: <your reasoning about what to do next>
Action: <tool_name or FINISH>
Action Input: <JSON object with tool arguments, or {"output": "final answer"} for FINISH>

Rules:
- Think carefully before acting
- Use FINISH when the goal is fully achieved
- Never skip the Thought/Action/Action Input format
- Be precise with Action Input JSON
- If a tool fails, reason about why and try a different approach

Available tools:
{tool_schemas}
"""


class BaseAgent:
    """
    Elite autonomous agent with ReAct loop, tool use, memory, and event bus.

    Usage:
        agent = BaseAgent(config=config, llm=llm, tool_registry=registry)
        result = await agent.run("Your goal here")
    """

    def __init__(
        self,
        config: AgentConfig,
        llm,
        tool_registry: ToolRegistry,
        event_bus: Optional[EventBus] = None,
    ):
        self.config = config
        self.llm = llm
        self.tool_registry = tool_registry
        self.event_bus = event_bus or EventBus()

        self.memory = _AgentMemory(
            short_term=ShortTermMemory(window=config.memory_window),
            long_term=LongTermMemory(path=config.long_term_memory_path),
        )

        logger.info("BaseAgent initialised", extra={
            "model": config.model,
            "max_steps": config.max_steps,
            "tools": list(tool_registry.names()),
        })

    async def run(self, goal: str, context: Optional[Dict] = None) -> AgentResult:
        """
        Run the ReAct loop to completion.

        Args:
            goal:    The natural-language goal to achieve.
            context: Optional extra context injected into memory.

        Returns:
            AgentResult with output, trace, token counts, timings.
        """
        start = time.monotonic()
        steps: List[AgentStep] = []
        total_tokens = 0

        logger.info("Agent run started", extra={"goal": goal})
        await self.event_bus.emit("agent_start", {"goal": goal})

        # Reset short-term memory for this run
        self.memory.short_term.reset()
        if context:
            self.memory.short_term.add(role="system", content=json.dumps(context))

        # Build system prompt with tool schemas
        tool_schemas = self.tool_registry.schemas_as_text()
        system = SYSTEM_PROMPT.format(tool_schemas=tool_schemas)

        # Add the user goal
        self.memory.short_term.add(role="user", content=goal)

        for step_num in range(1, self.config.max_steps + 1):
            step_start = time.monotonic()

            # Build messages for LLM
            messages = [{"role": "system", "content": system}]
            messages += self.memory.short_term.get_context()

            # LLM call
            try:
                response = await self.llm.complete(messages)
            except Exception as exc:
                logger.error("LLM call failed", extra={"error": str(exc)})
                return AgentResult(
                    goal=goal, output="", success=False,
                    steps=steps, total_tokens=total_tokens,
                    error=str(exc),
                )

            raw_text = response.content
            tokens_used = response.usage.total_tokens if response.usage else count_tokens(raw_text)
            total_tokens += tokens_used

            # Parse Thought / Action / Action Input
            try:
                thought, action, action_input = self._parse_response(raw_text)
            except AgentParseError as exc:
                logger.warning("Parse error", extra={"raw": raw_text, "error": str(exc)})
                # Feed the error back so LLM can self-correct
                self.memory.short_term.add(role="assistant", content=raw_text)
                self.memory.short_term.add(
                    role="user",
                    content=f"[PARSE ERROR] Your response was not in the required format. Error: {exc}. Please retry."
                )
                continue

            duration_ms = (time.monotonic() - step_start) * 1000

            # FINISH action
            if action.upper() == "FINISH":
                output = action_input.get("output", raw_text) if isinstance(action_input, dict) else str(action_input)
                step = AgentStep(
                    step=step_num, thought=thought, action=action,
                    action_input=action_input, observation="[DONE]",
                    tokens_used=tokens_used, duration_ms=duration_ms,
                )
                steps.append(step)

                result = AgentResult(
                    goal=goal, output=output, success=True, steps=steps,
                    total_tokens=total_tokens,
                    total_duration_ms=(time.monotonic() - start) * 1000,
                )
                await self.event_bus.emit("agent_finish", {
                    "goal": goal, "steps": step_num, "tokens": total_tokens,
                })
                logger.info("Agent run complete", extra={"steps": step_num, "tokens": total_tokens})
                return result

            # Execute tool
            try:
                observation = await self.tool_registry.execute(
                    name=action,
                    args=action_input,
                    timeout=self.config.tool_timeout_secs,
                )
            except ToolNotFoundError:
                observation = f"ERROR: Tool '{action}' not found. Available: {list(self.tool_registry.names())}"
            except asyncio.TimeoutError:
                observation = f"ERROR: Tool '{action}' timed out after {self.config.tool_timeout_secs}s"
            except Exception as exc:
                observation = f"ERROR: Tool '{action}' raised {type(exc).__name__}: {exc}"

            step = AgentStep(
                step=step_num, thought=thought, action=action,
                action_input=action_input, observation=observation,
                tokens_used=tokens_used, duration_ms=duration_ms,
            )
            steps.append(step)

            # Add to memory
            self.memory.short_term.add(role="assistant", content=raw_text)
            self.memory.short_term.add(role="user", content=f"Observation: {observation}")

            await self.event_bus.emit("step_complete", {
                "step": step_num, "action": action,
                "result": observation[:200], "tokens": tokens_used,
            })
            logger.debug("Step complete", extra={
                "step": step_num, "action": action,
                "obs_len": len(observation), "tokens": tokens_used,
            })

        # Max steps reached
        raise AgentMaxStepsError(
            f"Agent did not finish within {self.config.max_steps} steps."
        )

    # ── Parsing ───────────────────────────────────────────────────────────

    def _parse_response(self, text: str):
        thought = action = action_input_raw = ""
        for line in text.splitlines():
            if line.startswith("Thought:"):
                thought = line[len("Thought:"):].strip()
            elif line.startswith("Action:"):
                action = line[len("Action:"):].strip()
            elif line.startswith("Action Input:"):
                action_input_raw = line[len("Action Input:"):].strip()

        if not action:
            raise AgentParseError("Missing 'Action:' line in LLM response")

        # Multi-line JSON fallback
        if not action_input_raw:
            in_block = False
            block_lines = []
            for line in text.splitlines():
                if line.startswith("Action Input:"):
                    in_block = True
                    block_lines.append(line[len("Action Input:"):].strip())
                elif in_block:
                    block_lines.append(line)
            action_input_raw = "\n".join(block_lines).strip()

        try:
            action_input = json.loads(action_input_raw) if action_input_raw else {}
        except json.JSONDecodeError:
            action_input = {"raw": action_input_raw}

        return thought, action, action_input


@dataclass
class _AgentMemory:
    short_term: ShortTermMemory
    long_term: LongTermMemory
