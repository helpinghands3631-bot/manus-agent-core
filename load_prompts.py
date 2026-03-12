"""
load_prompts.py
----------------
Registers all agency-agents markdown prompts into the Opik Prompt Library.

Run this script whenever you update a prompt in the agency-agents repo.
Each run creates a new version if the content has changed.

Usage:
    python load_prompts.py

Prerequisites:
    - agency-agents repo cloned alongside manus-agent-core
    - OPIK_API_KEY, OPIK_WORKSPACE, OPIK_PROJECT_NAME set in .env
"""

import os
import sys

import observability  # noqa: F401 — bootstraps Opik
import opik

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Agent prompt directories ────────────────────────────────────────────────
# These paths are relative to this file's location. Adjust if your repo layout
# differs. The script scans each directory for .md files.
AGENTS_DIRS = [
    "../agency-agents/engineering",
    "../agency-agents/marketing",
    "../agency-agents/sales",
    "../agency-agents/design",
    "../agency-agents/product",
    "../agency-agents/strategy",
    "../agency-agents/support",
    "../agency-agents/testing",
    "../agency-agents/integrations",
    "../agency-agents/project-management",
    "../agency-agents/paid-media",
    "../agency-agents/specialized",
    "../agency-agents/spatial-computing",
    "../agency-agents/game-development",
]


def register_prompts():
    """Scan all agent directories and register each .md file as an Opik prompt."""
    registered = 0
    skipped = 0

    for directory in AGENTS_DIRS:
        abs_dir = os.path.join(os.path.dirname(__file__), directory)
        if not os.path.isdir(abs_dir):
            logger.warning(f"Directory not found, skipping: {directory}")
            skipped += 1
            continue

        category = os.path.basename(abs_dir)

        for filename in sorted(os.listdir(abs_dir)):
            if not filename.endswith(".md"):
                continue

            agent_name = filename.replace(".md", "")
            filepath = os.path.join(abs_dir, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                prompt_text = f.read()

            if not prompt_text.strip():
                logger.warning(f"Empty prompt file, skipping: {filepath}")
                continue

            try:
                prompt = opik.Prompt(
                    name=agent_name,
                    prompt=prompt_text,
                    metadata={
                        "source_repo": "agency-agents",
                        "category": category,
                        "file": filename,
                    },
                )
                print(f"  [{category}] {agent_name} → version {prompt.commit}")
                registered += 1
            except Exception as exc:
                logger.error(f"Failed to register {agent_name}: {exc}")

    return registered, skipped


if __name__ == "__main__":
    print("=" * 60)
    print("Opik Prompt Library — Registering agency-agents prompts")
    print("=" * 60)
    print()

    registered, skipped = register_prompts()

    print()
    print("-" * 60)
    print(f"Done. {registered} prompts registered, {skipped} directories skipped.")
    print("View them at https://www.comet.com/opik → Prompt Library")
    print("-" * 60)
