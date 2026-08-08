"""Pure presentation helpers for the Streamlit submission interface.

Everything here is plain data and pure functions — no Streamlit imports,
no I/O, nothing that requires a running app to exercise. app.py is the
only module that talks to Streamlit; it composes these helpers with
`src.scoring.score_campaign()` output. This split is what keeps the
helpers in this module unit-testable (see tests/test_ui_helpers.py)
without resorting to brittle UI tests.
"""

from __future__ import annotations

from datetime import date, timedelta

from .models import (
    CampaignSubmission,
    QAStatus,
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)

CATEGORY_LABELS: dict[ValidationCategory, str] = {
    ValidationCategory.TRACKING_UTMS: "Tracking & UTMs",
    ValidationCategory.REQUIRED_INFORMATION: "Required Information",
    ValidationCategory.URL_INTEGRITY: "URL & Destination Integrity",
    ValidationCategory.NAMING_GOVERNANCE: "Naming & Governance",
    ValidationCategory.LAUNCH_READINESS: "Launch Readiness",
}
"""Human-readable labels for each ValidationCategory, in display order."""

STATUS_META: dict[QAStatus, dict[str, str]] = {
    QAStatus.PASS: {
        "label": "✓ PASS",
        "css_class": "status-pass",
        "recommendation": (
            "Campaign meets the deterministic launch-readiness threshold."
        ),
    },
    QAStatus.REVIEW: {
        "label": "! REVIEW",
        "css_class": "status-review",
        "recommendation": "Resolve flagged issues before launch approval.",
    },
    QAStatus.FAIL: {
        "label": "✕ FAIL",
        "css_class": "status-fail",
        "recommendation": (
            "Campaign is not launch-ready and requires remediation."
        ),
    },
}
"""Presentation copy per QAStatus. Purely cosmetic — never used to derive
status; the UI always renders QAResult.status as computed by scoring.py."""


def category_breakdown(
    results: list[ValidationResult],
) -> dict[ValidationCategory, tuple[float, float]]:
    """Sum (points_earned, points_available) per category.

    Every ValidationCategory is always present in the returned dict, even
    if no results belong to it, so the UI can render a stable 5-row
    breakdown without special-casing missing categories.
    """
    totals = {category: [0.0, 0.0] for category in ValidationCategory}
    for result in results:
        entry = totals[result.category]
        entry[0] += result.points_earned
        entry[1] += result.points_available
    return {category: (earned, available) for category, (earned, available) in totals.items()}


def format_points(earned: float, available: float) -> str:
    """Render a points pair without noisy trailing '.0' (e.g. '24 / 30')."""
    return f"{earned:g} / {available:g}"


def group_by_category(
    results: list[ValidationResult],
) -> dict[ValidationCategory, list[ValidationResult]]:
    """Group results by category.

    Every ValidationCategory is always present (possibly with an empty
    list), matching category_breakdown()'s behaviour so callers never
    need to special-case a missing category.
    """
    grouped: dict[ValidationCategory, list[ValidationResult]] = {
        category: [] for category in ValidationCategory
    }
    for result in results:
        grouped[result.category].append(result)
    return grouped


def category_status_label(results: list[ValidationResult]) -> tuple[str, str]:
    """Derive a presentational status label for one category's results.

    Purely cosmetic — computed from already-scored ValidationResult data
    and never fed back into scoring or QAResult.status. A category reads
    "Critical" if any of its results is a critical failure, "Needs
    Review" if any result is a WARNING or a (non-critical) FAIL,
    otherwise "Clear". Returns (label, css_class).

    Every FAIL in the real engine is always CRITICAL severity (see
    validators.py), so the "Needs Review" FAIL case is a defensive
    fallback rather than a scenario this engine currently produces — but
    a FAIL must never silently read as "Clear" regardless.
    """
    if any(
        result.severity == ValidationSeverity.CRITICAL
        and result.status == ValidationStatus.FAIL
        for result in results
    ):
        return "Critical", "cat-status-fail"
    if any(
        result.status in (ValidationStatus.WARNING, ValidationStatus.FAIL)
        for result in results
    ):
        return "Needs Review", "cat-status-review"
    return "Clear", "cat-status-pass"


def example_campaigns() -> dict[str, CampaignSubmission]:
    """Curated example campaigns for the Streamlit demo loader.

    Built directly as CampaignSubmission objects rather than read from
    data/sample_campaigns.csv: launch dates stay valid relative to
    "today" this way, and the UI's demo loader carries no dependency on
    file I/O or on that dataset's fixed reference-date anchoring.
    """
    today = date.today()
    return {
        "Clean Paid Search": CampaignSubmission(
            campaign_name="uk_enterprise_demo_q3_2026",
            campaign_type="Paid Search",
            channel="Google Ads",
            objective="Demo Signups",
            target_audience="UK Enterprise",
            landing_page_url="https://acme.io/demo",
            destination_url=(
                "https://acme.io/demo?utm_source=google&utm_medium=cpc"
                "&utm_campaign=uk_enterprise_demo_q3_2026"
            ),
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="uk_enterprise_demo_q3_2026",
            cta="Book a Demo",
            campaign_owner="Sarah Chen",
            launch_date=today + timedelta(days=14),
            budget=15000.0,
            campaign_message="Enterprise Q3 demo push for UK named accounts.",
        ),
        "Warning-heavy Paid Social": CampaignSubmission(
            campaign_name="Enterprise ABM LinkedIn Q4",
            campaign_type="Paid Social",
            channel="LinkedIn Ads",
            objective="Pipeline Acceleration",
            target_audience="Enterprise IT Decision Makers",
            landing_page_url="http://acme.io/abm",
            destination_url=(
                "https://acme.io/abm?utm_source=LinkedIn&utm_medium=paid social"
                "&utm_campaign=different_name"
            ),
            utm_source="LinkedIn",
            utm_medium="paid social",
            utm_campaign="different_name",
            cta="Request a Consultation",
            campaign_owner="Maria Gonzalez",
            launch_date=today + timedelta(days=14),
            budget=20000.0,
            campaign_message="",
        ),
        "Failing Campaign": CampaignSubmission(
            campaign_name="",
            campaign_type="Paid Search",
            channel="",
            objective="",
            target_audience="",
            landing_page_url="",
            destination_url=None,
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            cta="",
            campaign_owner="",
            launch_date=today - timedelta(days=1),
            budget=0.0,
            campaign_message="",
        ),
    }
