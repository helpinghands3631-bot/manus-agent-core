"""
observability.py
-----------------
Bootstrap Comet/Opik tracing and wire it into LiteLLM.

Import this module once at the start of your application.
All subsequent LiteLLM calls will be automatically traced in the Opik UI.

Required environment variables (set in .env):
    OPIK_API_KEY          — Your Comet API key
    OPIK_WORKSPACE        — Your Comet workspace slug
    OPIK_PROJECT_NAME     — The Opik project name (default: manus-agent-platform)
"""

from dotenv import load_dotenv
load_dotenv()  # Must be called before importing opik or litellm

import os
import opik
import litellm
from litellm.integrations.opik import OpikLogger

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Configure Opik SDK ──────────────────────────────────────────────────────
# Reads OPIK_API_KEY, OPIK_WORKSPACE, OPIK_PROJECT_NAME from env automatically
opik.configure(use_local=False)

# ── Attach Opik logger to LiteLLM ──────────────────────────────────────────
# Every litellm.completion / litellm.acompletion call is now traced
opik_logger = OpikLogger()
litellm.callbacks = [opik_logger]

# ── Suppress noisy LiteLLM logs ────────────────────────────────────────────
litellm.set_verbose = False

logger.info(
    "Opik observability initialised",
    extra={
        "workspace": os.getenv("OPIK_WORKSPACE", "unknown"),
        "project": os.getenv("OPIK_PROJECT_NAME", "manus-agent-platform"),
    },
)
