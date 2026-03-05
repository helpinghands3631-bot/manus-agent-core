# 🧠 manus-agent-core

> **Elite open-source base agent framework for Manus** — autonomous planning, tool use, memory, multi-step reasoning, and full observability.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![CI](https://github.com/helpinghands3631-bot/manus-agent-core/actions/workflows/ci.yml/badge.svg)](https://github.com/helpinghands3631-bot/manus-agent-core/actions)

---

## What Is This?

`manus-agent-core` is the **brain** of the Manus open-source agent ecosystem. It provides:

- 🔄 **ReAct loop** — Reason → Act → Observe, repeated until goal is complete
- 🧰 **Tool registry** — plug in any tool (web search, code exec, file I/O, API calls)
- 🧠 **Memory system** — short-term (context window) + long-term (vector/JSON store)
- 📋 **Task planner** — break complex goals into atomic subtasks with dependency tracking
- 🔌 **LLM agnostic** — works with OpenAI, Anthropic, Groq, Ollama, or any OpenAI-compatible API
- 📡 **Event bus** — emit/subscribe to agent lifecycle events
- 🪵 **Full observability** — structured JSON logs, step traces, token usage tracking

---

## Architecture

```
manus-agent-core/
├── agent/
│   ├── core.py          # BaseAgent — the ReAct execution loop
│   ├── planner.py       # TaskPlanner — goal decomposition
│   ├── executor.py      # ToolExecutor — safe tool dispatch
│   └── observer.py      # Observer — step recording + trace output
├── memory/
│   ├── short_term.py    # ConversationBuffer — sliding window context
│   └── long_term.py     # LongTermMemory — JSON-backed persistent store
├── tools/
│   ├── registry.py      # ToolRegistry — register/discover tools
│   ├── base.py          # BaseTool — abstract base class
│   ├── web_search.py    # WebSearchTool
│   ├── code_exec.py     # CodeExecutorTool — sandboxed Python exec
│   ├── file_io.py       # FileIOTool — read/write files safely
│   └── http_client.py   # HttpClientTool — make HTTP requests
├── llm/
│   ├── base.py          # BaseLLM — abstract interface
│   ├── openai.py        # OpenAILLM
│   ├── anthropic.py     # AnthropicLLM
│   └── groq.py          # GroqLLM
├── events/
│   └── bus.py           # EventBus — pub/sub for agent events
├── config.py            # AgentConfig — all settings via env or dataclass
├── exceptions.py        # Domain exceptions
└── utils/
    ├── logger.py        # Structured JSON logger
    └── tokens.py        # Token counting utilities
```

---

## Quick Start

```bash
pip install manus-agent-core
```

```python
from agent.core import BaseAgent
from agent.config import AgentConfig
from tools.registry import ToolRegistry
from tools.web_search import WebSearchTool
from tools.code_exec import CodeExecutorTool
from llm.openai import OpenAILLM

# Configure
config = AgentConfig(
    llm_provider="openai",
    model="gpt-4o",
    max_steps=20,
    memory_window=10,
)

# Register tools
registry = ToolRegistry()
registry.register(WebSearchTool())
registry.register(CodeExecutorTool())

# Build agent
llm = OpenAILLM(api_key="sk-...")
agent = BaseAgent(config=config, llm=llm, tool_registry=registry)

# Run
result = await agent.run("Research the top 5 Python web frameworks and write a comparison report")
print(result.output)
print(result.trace)  # Full step-by-step trace
```

---

## Features In Depth

### ReAct Loop (`agent/core.py`)

The agent follows the **Reason-Act-Observe** pattern:

1. **Reason** — LLM generates thought + chosen action
2. **Act** — tool is called with arguments
3. **Observe** — result is appended to context
4. Repeat until `FINISH` action or max steps reached

### Tool Registry (`tools/registry.py`)

```python
# Register a custom tool
from tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    parameters = {
        "query": {"type": "string", "required": True}
    }

    async def run(self, query: str) -> str:
        return f"Result for: {query}"

registry.register(MyTool())
```

### Memory (`memory/`)

```python
# Short-term — last N messages
agent.memory.short_term.add(role="user", content="Hello")
context = agent.memory.short_term.get_context()

# Long-term — persist across sessions
agent.memory.long_term.save(key="user_prefs", value={"lang": "python"})
prefs = agent.memory.long_term.load("user_prefs")
```

### Event Bus (`events/bus.py`)

```python
# Subscribe to agent events
bus = agent.event_bus

@bus.on("step_complete")
def on_step(event):
    print(f"Step {event.step}: {event.action} -> {event.result[:100]}")

@bus.on("agent_finish")
def on_finish(event):
    print(f"Done in {event.steps} steps, {event.tokens} tokens")
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM backend (`openai`, `anthropic`, `groq`, `ollama`) |
| `LLM_MODEL` | `gpt-4o` | Model name |
| `LLM_API_KEY` | — | API key |
| `LLM_BASE_URL` | — | Custom base URL (Ollama, etc.) |
| `AGENT_MAX_STEPS` | `25` | Max ReAct iterations |
| `AGENT_MEMORY_WINDOW` | `10` | Short-term memory message count |
| `AGENT_LONG_TERM_PATH` | `./data/memory.json` | Long-term memory file path |
| `AGENT_LOG_LEVEL` | `INFO` | Log level |
| `TOOL_TIMEOUT_SECS` | `30` | Per-tool timeout |
| `CODE_EXEC_ALLOWED` | `true` | Enable code execution tool |

---

## Development

```bash
git clone https://github.com/helpinghands3631-bot/manus-agent-core
cd manus-agent-core
pip install -e ".[dev]"
pytest tests/ -v --cov=agent
```

---

## Part of the Manus Ecosystem

| Repo | Description |
|---|---|
| **manus-agent-core** | Base agent framework (this repo) |
| [manus-memory-store](https://github.com/helpinghands3631-bot/manus-memory-store) | Redis/JSON persistent memory |
| [manus-task-runner](https://github.com/helpinghands3631-bot/manus-task-runner) | Autonomous task queue + retry engine |
| [manus-api-gateway](https://github.com/helpinghands3631-bot/manus-api-gateway) | FastAPI gateway + auth + rate limiting |
| [manus-skill-library](https://github.com/helpinghands3631-bot/manus-skill-library) | Pluggable skills for agents |
| [manus-dashboard](https://github.com/helpinghands3631-bot/manus-dashboard) | Real-time agent monitoring UI |
| [manus-telegram-agent](https://github.com/helpinghands3631-bot/manus-telegram-agent) | Telegram bot + Manus integration |

---

## License

MIT — see [LICENSE](LICENSE). Built by the Helping Hands Team.
