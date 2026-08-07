"""Shared constants for campaign QA governance rules.

Values here are drawn directly from the locked deterministic QA/scoring
model in project_management/DECISIONS.md, Decision 002. This module
defines fixed values only — no validation or scoring logic.
"""

from __future__ import annotations

from .models import ValidationCategory

PAID_CAMPAIGN_TYPES: frozenset[str] = frozenset(
    {
        "Paid Search",
        "Paid Social",
        "Display",
        "Content Syndication",
    }
)
"""Campaign types subject to paid-campaign tracking requirements."""

CATEGORY_WEIGHTS: dict[ValidationCategory, int] = {
    ValidationCategory.TRACKING_UTMS: 30,
    ValidationCategory.REQUIRED_INFORMATION: 20,
    ValidationCategory.URL_INTEGRITY: 20,
    ValidationCategory.NAMING_GOVERNANCE: 15,
    ValidationCategory.LAUNCH_READINESS: 15,
}
"""Points available per QA scoring category. Sums to 100."""

RULE_POINTS: dict[str, float] = {
    # Required campaign information — CATEGORY_WEIGHTS[REQUIRED_INFORMATION] = 20
    "required_campaign_name": 2,
    "required_campaign_type": 2,
    "required_channel": 2,
    "required_objective": 2,
    "required_target_audience": 2,
    "required_landing_page_url": 2,
    "required_campaign_owner": 2,
    "required_launch_date": 2,
    "required_cta": 2,
    "cta_length": 2,
    # URL & destination integrity — CATEGORY_WEIGHTS[URL_INTEGRITY] = 20
    "landing_url_format": 6,
    "landing_url_https": 4,
    "destination_url_required": 4,
    "destination_url_format": 4,
    "destination_url_https": 2,
    # Tracking & UTMs — CATEGORY_WEIGHTS[TRACKING_UTMS] = 30
    "utm_source_required": 6,
    "utm_medium_required": 6,
    "utm_campaign_required": 6,
    "utm_source_format": 2,
    "utm_medium_format": 2,
    "utm_campaign_format": 2,
    "utm_campaign_alignment": 2,
    "destination_url_utms": 4,
    # Naming & governance — CATEGORY_WEIGHTS[NAMING_GOVERNANCE] = 15
    "campaign_name_lowercase": 3,
    "campaign_name_no_spaces": 3,
    "campaign_name_characters": 3,
    "campaign_name_underscore_placement": 3,
    "campaign_name_consecutive_underscores": 3,
    # Launch readiness — CATEGORY_WEIGHTS[LAUNCH_READINESS] = 15
    "launch_date_timing": 10,
    "paid_budget": 5,
}
"""Points available per validation rule.

Every validator rule always emits a result for every campaign — when a
rule does not apply (e.g. a UTM field that is not required for a
non-paid campaign), it is reported as an automatic PASS at full points
rather than being omitted. This guarantees that the rules within each
category always sum to exactly that category's weight above, for both
paid and non-paid campaigns, so a non-paid campaign can still reach a
perfect score. See project_management/DECISIONS.md, Decision 003.
"""
