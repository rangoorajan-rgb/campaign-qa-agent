"""Application configuration.

Static configuration for the Streamlit UI, plus environment-variable
loading for the Gemini integration. Make and Slack credentials remain
unimplemented until those integrations are built.
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
