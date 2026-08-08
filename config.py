"""Application configuration.

Static configuration for the Streamlit UI. Environment-variable loading
for Gemini, Make, and Slack credentials remains unimplemented until those
integrations are built.
"""

from __future__ import annotations

APP_TITLE = "Campaign QA Agent"
PAGE_ICON = "🧭"
LAYOUT = "wide"
SIDEBAR_STATE = "expanded"
