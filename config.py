"""Application configuration.

Static configuration for the Streamlit UI, plus environment-variable
loading for the Gemini and Make webhook integrations. Slack credentials
remain unimplemented until that integration is built.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "Campaign QA Agent"
PAGE_ICON = "🧭"
LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
"""Gemini API key. Empty string when unset — never a hard failure at
import time, since running without AI review configured is a supported
state (see src/gemini_analyzer.py::GeminiReviewStatus.NOT_CONFIGURED)."""

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
"""Gemini model name, configurable via the GEMINI_MODEL env var so it is
never hard-coded elsewhere in the application."""

MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
"""Make (Integromat) webhook URL. Empty string when unset — never a hard
failure at import time, since running without Make configured is a
supported state (see src/webhook.py::WebhookDeliveryStatus.NOT_CONFIGURED)."""

MAKE_WEBHOOK_TIMEOUT_SECONDS = float(os.getenv("MAKE_WEBHOOK_TIMEOUT_SECONDS", "5"))
"""Per-attempt HTTP timeout (seconds) for the Make webhook call."""

MAKE_WEBHOOK_MAX_ATTEMPTS = int(os.getenv("MAKE_WEBHOOK_MAX_ATTEMPTS", "2"))
"""Total delivery attempts (first attempt plus retries) for the Make
webhook call. Worst-case blocking latency is approximately
MAKE_WEBHOOK_TIMEOUT_SECONDS * MAKE_WEBHOOK_MAX_ATTEMPTS, plus a ~1s
delay between attempts — see project_management/DECISIONS.md,
Decision 005."""
