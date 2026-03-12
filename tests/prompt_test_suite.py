"""
tests/prompt_test_suite.py
---------------------------
A fixed set of test queries for the LeadOps platform.

Run this daily after making prompt changes to measure improvement.
Each test case is traced in Opik so you can compare versions over time.

Usage:
    python tests/prompt_test_suite.py "v1.0-baseline"
    python tests/prompt_test_suite.py "v1.1-tighter-email-constraints"

The version tag is attached to every trace, making it easy to filter
and compare runs in the Opik UI.
"""

import asyncio
import sys
import time

import observability  # noqa: F401 — bootstraps Opik

from agent.core import BaseAgent
from config import AgentConfig
from llm.groq import GroqLLM
from tools.registry import ToolRegistry
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Fixed Test Cases ────────────────────────────────────────────────────────
# These should NOT change between runs. The whole point is to measure the
# same queries against different prompt versions.

TEST_CASES = [
    {
        "id": "TC-001",
        "goal": "Scrape 10 electricians in Sydney and score them A/B/C by website quality.",
        "success_criteria": "Returns a table with name, website, and score column.",
    },
    {
        "id": "TC-002",
        "goal": "Write a 3-step cold email sequence for a plumber in Melbourne. Keep each email under 120 words.",
        "success_criteria": "Returns 3 emails, each clearly labelled, each under 120 words.",
    },
    {
        "id": "TC-003",
        "goal": "Given campaign stats (open rate 22%, reply rate 4%), recommend the next 3 optimisation actions.",
        "success_criteria": "Returns exactly 3 concrete, numbered actions.",
    },
    {
        "id": "TC-004",
        "goal": "Identify the ICP for a local SEO agency targeting tradies in Queensland.",
        "success_criteria": "Returns a structured ICP with industry, company size, pain points, and buying trigger.",
    },
    {
        "id": "TC-005",
        "goal": "Generate a one-page weekly client report template for a B2B outbound campaign.",
        "success_criteria": "Returns a template with sections for leads scraped, emails sent, open rate, reply rate, and next steps.",
    },
]


async def run_test_suite(prompt_version: str = "unversioned"):
    """
    Execute all test cases and collect results.

    Args:
        prompt_version: A version tag (e.g., "v1.0-baseline") attached to
                        each trace for filtering in the Opik UI.

    Returns:
        List of result dicts with test_id, goal, output, success, steps, tokens.
    """
    config = AgentConfig()
    llm = GroqLLM()
    registry = ToolRegistry()
    agent = BaseAgent(config=config, llm=llm, tool_registry=registry)

    results = []
    total_start = time.monotonic()

    print(f"\n{'='*60}")
    print(f"  Prompt Test Suite — version: {prompt_version}")
    print(f"  Running {len(TEST_CASES)} test cases")
    print(f"{'='*60}\n")

    for tc in TEST_CASES:
        print(f"  [{tc['id']}] {tc['goal'][:60]}...")
        tc_start = time.monotonic()

        try:
            result = await agent.run(tc["goal"])
            duration = time.monotonic() - tc_start

            results.append({
                "test_id": tc["id"],
                "goal": tc["goal"],
                "success_criteria": tc["success_criteria"],
                "output": result.output,
                "success": result.success,
                "steps": len(result.steps),
                "tokens": result.total_tokens,
                "duration_s": round(duration, 2),
                "prompt_version": prompt_version,
                "error": result.error,
            })
            status = "PASS" if result.success else "FAIL"
            print(f"    {status} — {len(result.steps)} steps, {result.total_tokens} tokens, {duration:.1f}s")

        except Exception as exc:
            duration = time.monotonic() - tc_start
            results.append({
                "test_id": tc["id"],
                "goal": tc["goal"],
                "success_criteria": tc["success_criteria"],
                "output": "",
                "success": False,
                "steps": 0,
                "tokens": 0,
                "duration_s": round(duration, 2),
                "prompt_version": prompt_version,
                "error": str(exc),
            })
            print(f"    ERROR — {type(exc).__name__}: {exc}")

    total_duration = time.monotonic() - total_start
    passed = sum(1 for r in results if r["success"])
    total_tokens = sum(r["tokens"] for r in results)

    print(f"\n{'─'*60}")
    print(f"  Results: {passed}/{len(results)} passed")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Total time: {total_duration:.1f}s")
    print(f"  Version: {prompt_version}")
    print(f"{'─'*60}")
    print(f"  Review traces at https://www.comet.com/opik")
    print(f"{'─'*60}\n")

    return results


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "unversioned"
    asyncio.run(run_test_suite(prompt_version=version))
