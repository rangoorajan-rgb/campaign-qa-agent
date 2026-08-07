"""Rule-based validation checks for campaign QA.

Each ``validate_*`` function accepts a :class:`~src.models.CampaignSubmission`
and returns a list of :class:`~src.models.ValidationResult` objects for the
checks it owns. :func:`validate_campaign` orchestrates all of them.

Design principle — every rule always fires: every validator rule emits a
result for every campaign, even when the rule does not apply. This keeps
total points_available per category constant (matching CATEGORY_WEIGHTS)
regardless of campaign type or field presence, which is required so that
both paid and non-paid campaigns can reach a perfect score.

Two distinct "nothing wrong here" outcomes exist, and they are not
interchangeable:

- ``ValidationStatus.NOT_APPLICABLE`` — the rule genuinely does not apply
  to this campaign because of its type (e.g. ``paid_budget`` or
  ``utm_source_required`` on a non-paid campaign). Full points are still
  awarded, but the status says "not applicable," not "passed," so future
  UI/audit output never claims a non-paid campaign "passed" a paid-only
  requirement it was never subject to.
- ``ValidationStatus.PASS`` with a "not evaluated" message — the rule
  *does* apply to this campaign, but there is nothing to evaluate yet
  because a prerequisite universal field is missing (e.g. campaign name
  is blank, so naming-format checks have nothing to check). That missing
  prerequisite is itself reported as a separate CRITICAL failure
  elsewhere — this is not a loophole, just this rule declining to
  double-report it. NOT_APPLICABLE must never be used for this case, per
  Decision 002/003: an applicable field being missing must still surface
  as a FAIL where the rule directly concerns that field.

See project_management/DECISIONS.md, Decision 002 (rules) and Decision
003 (points allocation and both design principles above).

This module performs syntactic checks only — no network requests are made
to resolve URLs, and no qualitative analysis is performed. It is
independent of Streamlit and all external integrations.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import parse_qs, urlparse

from .constants import PAID_CAMPAIGN_TYPES, RULE_POINTS
from .models import (
    CampaignSubmission,
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)

_INVALID_NAME_CHARACTERS = re.compile(r"[^a-zA-Z0-9_ ]")


def _is_blank(value: str | None) -> bool:
    """Whether a string field is missing or contains only whitespace."""
    return value is None or value.strip() == ""


def _is_paid_campaign(campaign: CampaignSubmission) -> bool:
    """Whether a campaign's type is subject to paid-campaign requirements."""
    return campaign.campaign_type in PAID_CAMPAIGN_TYPES


def _parse_url(value: str) -> tuple[bool, str | None]:
    """Syntactically validate a URL. Returns ``(is_valid, scheme)``.

    Valid means an ``http``/``https`` scheme plus a non-empty host. This
    performs no network access — it never checks whether the URL resolves.
    """
    try:
        parsed = urlparse(value)
    except ValueError:
        return False, None
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, None
    return True, parsed.scheme


def normalize_campaign_name(name: str) -> str:
    """Normalise a campaign name for comparison against ``utm_campaign``.

    Trims whitespace, lowercases, replaces whitespace runs with a single
    underscore, collapses repeated underscores, and strips leading/trailing
    underscores. E.g. ``"UK Enterprise Demo Q3 2026"`` becomes
    ``"uk_enterprise_demo_q3_2026"``.
    """
    normalized = name.strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def validate_required_fields(campaign: CampaignSubmission) -> list[ValidationResult]:
    """Validate presence of the universal required fields.

    Presence only — format-specific rules (URL syntax, CTA length, naming
    convention, launch-date timing) live in their own dedicated validators
    below, so as not to duplicate this check's concern.
    """
    string_fields: list[tuple[str, str, str | None]] = [
        ("required_campaign_name", "Campaign name", campaign.campaign_name),
        ("required_campaign_type", "Campaign type", campaign.campaign_type),
        ("required_channel", "Channel", campaign.channel),
        ("required_objective", "Objective", campaign.objective),
        (
            "required_target_audience",
            "Target audience",
            campaign.target_audience,
        ),
        (
            "required_landing_page_url",
            "Landing page URL",
            campaign.landing_page_url,
        ),
        ("required_campaign_owner", "Campaign owner", campaign.campaign_owner),
        ("required_cta", "CTA", campaign.cta),
    ]

    results: list[ValidationResult] = []
    for rule_id, label, value in string_fields:
        points = RULE_POINTS[rule_id]
        if _is_blank(value):
            results.append(
                ValidationResult(
                    category=ValidationCategory.REQUIRED_INFORMATION,
                    rule_id=rule_id,
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"{label} is missing.",
                    recommendation=f"Provide a {label.lower()} before launch.",
                    points_available=points,
                    points_earned=0,
                )
            )
        else:
            results.append(
                ValidationResult(
                    category=ValidationCategory.REQUIRED_INFORMATION,
                    rule_id=rule_id,
                    status=ValidationStatus.PASS,
                    severity=ValidationSeverity.INFO,
                    message=f"{label} is present.",
                    points_available=points,
                    points_earned=points,
                )
            )

    launch_date_points = RULE_POINTS["required_launch_date"]
    if campaign.launch_date is None:
        results.append(
            ValidationResult(
                category=ValidationCategory.REQUIRED_INFORMATION,
                rule_id="required_launch_date",
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.CRITICAL,
                message="Launch date is missing.",
                recommendation="Provide a launch date before launch.",
                points_available=launch_date_points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.REQUIRED_INFORMATION,
                rule_id="required_launch_date",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Launch date is present.",
                points_available=launch_date_points,
                points_earned=launch_date_points,
            )
        )

    return results


def validate_cta(campaign: CampaignSubmission) -> list[ValidationResult]:
    """Validate CTA length. Presence is handled by ``validate_required_fields``."""
    points = RULE_POINTS["cta_length"]
    cta = campaign.cta

    if _is_blank(cta):
        return [
            ValidationResult(
                category=ValidationCategory.REQUIRED_INFORMATION,
                rule_id="cta_length",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="CTA is missing; length not evaluated.",
                points_available=points,
                points_earned=points,
            )
        ]

    length = len(cta.strip())
    if length <= 60:
        return [
            ValidationResult(
                category=ValidationCategory.REQUIRED_INFORMATION,
                rule_id="cta_length",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message=f"CTA length ({length} characters) is within range.",
                points_available=points,
                points_earned=points,
            )
        ]

    return [
        ValidationResult(
            category=ValidationCategory.REQUIRED_INFORMATION,
            rule_id="cta_length",
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.WARNING,
            message=f"CTA is unusually long ({length} characters).",
            recommendation="Shorten the CTA to 60 characters or fewer.",
            points_available=points,
            points_earned=points / 2,
        )
    ]


def validate_landing_page_url(campaign: CampaignSubmission) -> list[ValidationResult]:
    """Validate landing page URL syntax and scheme (syntax only)."""
    format_points = RULE_POINTS["landing_url_format"]
    https_points = RULE_POINTS["landing_url_https"]
    url = campaign.landing_page_url

    if _is_blank(url):
        return [
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="landing_url_format",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Landing page URL is missing; format not evaluated.",
                points_available=format_points,
                points_earned=format_points,
            ),
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="landing_url_https",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Landing page URL is missing; scheme not evaluated.",
                points_available=https_points,
                points_earned=https_points,
            ),
        ]

    is_valid, scheme = _parse_url(url)
    if not is_valid:
        return [
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="landing_url_format",
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.CRITICAL,
                message=f"Landing page URL '{url}' is not a valid http(s) URL.",
                recommendation=(
                    "Provide a well-formed http:// or https:// URL with a "
                    "valid host."
                ),
                points_available=format_points,
                points_earned=0,
            ),
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="landing_url_https",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Landing page URL is malformed; scheme not evaluated.",
                points_available=https_points,
                points_earned=https_points,
            ),
        ]

    results = [
        ValidationResult(
            category=ValidationCategory.URL_INTEGRITY,
            rule_id="landing_url_format",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            message="Landing page URL is well-formed.",
            points_available=format_points,
            points_earned=format_points,
        )
    ]

    if scheme == "https":
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="landing_url_https",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Landing page URL uses HTTPS.",
                points_available=https_points,
                points_earned=https_points,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="landing_url_https",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message="Landing page URL uses HTTP instead of HTTPS.",
                recommendation="Use an HTTPS landing page URL.",
                points_available=https_points,
                points_earned=0,
            )
        )

    return results


def validate_destination_url(campaign: CampaignSubmission) -> list[ValidationResult]:
    """Validate destination/tracking URL requiredness and syntax.

    Required for paid campaigns; optional (but still syntax-validated if
    supplied) for non-paid campaigns. On a non-paid campaign the
    "required" rule is always NOT_APPLICABLE, regardless of whether a
    destination URL happens to be supplied — the requirement itself never
    applies. Format/scheme checks are NOT_APPLICABLE only when nothing was
    supplied; if a non-paid campaign does supply a destination URL, its
    syntax is validated exactly as it would be for a paid campaign.
    """
    required_points = RULE_POINTS["destination_url_required"]
    format_points = RULE_POINTS["destination_url_format"]
    https_points = RULE_POINTS["destination_url_https"]
    url = campaign.destination_url
    paid = _is_paid_campaign(campaign)
    blank = _is_blank(url)

    results: list[ValidationResult] = []

    if not paid:
        presence_note = "is present" if not blank else "is not supplied"
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_required",
                status=ValidationStatus.NOT_APPLICABLE,
                severity=ValidationSeverity.INFO,
                message=(
                    "Destination URL is not required for non-paid "
                    f"campaigns ({presence_note})."
                ),
                points_available=required_points,
                points_earned=required_points,
            )
        )
    elif blank:
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_required",
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.CRITICAL,
                message=(
                    "Destination/tracking URL is required for paid "
                    "campaigns but is missing."
                ),
                recommendation=(
                    "Provide a destination URL with UTM tracking "
                    "parameters."
                ),
                points_available=required_points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_required",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Destination URL is present.",
                points_available=required_points,
                points_earned=required_points,
            )
        )

    if blank:
        if paid:
            results.append(
                ValidationResult(
                    category=ValidationCategory.URL_INTEGRITY,
                    rule_id="destination_url_format",
                    status=ValidationStatus.PASS,
                    severity=ValidationSeverity.INFO,
                    message="Destination URL is missing; format not evaluated.",
                    points_available=format_points,
                    points_earned=format_points,
                )
            )
            results.append(
                ValidationResult(
                    category=ValidationCategory.URL_INTEGRITY,
                    rule_id="destination_url_https",
                    status=ValidationStatus.PASS,
                    severity=ValidationSeverity.INFO,
                    message="Destination URL is missing; scheme not evaluated.",
                    points_available=https_points,
                    points_earned=https_points,
                )
            )
        else:
            results.append(
                ValidationResult(
                    category=ValidationCategory.URL_INTEGRITY,
                    rule_id="destination_url_format",
                    status=ValidationStatus.NOT_APPLICABLE,
                    severity=ValidationSeverity.INFO,
                    message=(
                        "Destination URL not supplied; not applicable for "
                        "non-paid campaigns."
                    ),
                    points_available=format_points,
                    points_earned=format_points,
                )
            )
            results.append(
                ValidationResult(
                    category=ValidationCategory.URL_INTEGRITY,
                    rule_id="destination_url_https",
                    status=ValidationStatus.NOT_APPLICABLE,
                    severity=ValidationSeverity.INFO,
                    message=(
                        "Destination URL not supplied; not applicable for "
                        "non-paid campaigns."
                    ),
                    points_available=https_points,
                    points_earned=https_points,
                )
            )
        return results

    is_valid, scheme = _parse_url(url)

    if not is_valid:
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_format",
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.CRITICAL,
                message=f"Destination URL '{url}' is not a valid http(s) URL.",
                recommendation=(
                    "Provide a well-formed http:// or https:// destination "
                    "URL."
                ),
                points_available=format_points,
                points_earned=0,
            )
        )
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_https",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Destination URL is malformed; scheme not evaluated.",
                points_available=https_points,
                points_earned=https_points,
            )
        )
        return results

    results.append(
        ValidationResult(
            category=ValidationCategory.URL_INTEGRITY,
            rule_id="destination_url_format",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            message="Destination URL is well-formed.",
            points_available=format_points,
            points_earned=format_points,
        )
    )

    if scheme == "https":
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_https",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Destination URL uses HTTPS.",
                points_available=https_points,
                points_earned=https_points,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.URL_INTEGRITY,
                rule_id="destination_url_https",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message="Destination URL uses HTTP instead of HTTPS.",
                recommendation="Use an HTTPS destination URL.",
                points_available=https_points,
                points_earned=0,
            )
        )

    return results


def _validate_utm_field(
    field_name: str, value: str | None, paid: bool
) -> list[ValidationResult]:
    """Validate one UTM field's presence (paid only) and formatting.

    On a non-paid campaign the "required" concept never applies, so that
    rule is always NOT_APPLICABLE — even if a value happens to be
    supplied. The format rule tracks the *value*, not campaign type: it is
    NOT_APPLICABLE only when nothing was supplied to check (and, on a
    non-paid campaign, nothing was required to be supplied); if a value
    is present it is always format-checked, whether paid or not.
    """
    required_points = RULE_POINTS[f"{field_name}_required"]
    format_points = RULE_POINTS[f"{field_name}_format"]
    results: list[ValidationResult] = []

    if not paid:
        presence_note = "is present" if not _is_blank(value) else "is not supplied"
        results.append(
            ValidationResult(
                category=ValidationCategory.TRACKING_UTMS,
                rule_id=f"{field_name}_required",
                status=ValidationStatus.NOT_APPLICABLE,
                severity=ValidationSeverity.INFO,
                message=(
                    f"{field_name} is not required for non-paid campaigns "
                    f"({presence_note})."
                ),
                points_available=required_points,
                points_earned=required_points,
            )
        )
    elif _is_blank(value):
        results.append(
            ValidationResult(
                category=ValidationCategory.TRACKING_UTMS,
                rule_id=f"{field_name}_required",
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.CRITICAL,
                message=(
                    f"{field_name} is required for paid campaigns but "
                    "is missing."
                ),
                recommendation=f"Provide a value for {field_name}.",
                points_available=required_points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.TRACKING_UTMS,
                rule_id=f"{field_name}_required",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message=f"{field_name} is present.",
                points_available=required_points,
                points_earned=required_points,
            )
        )

    if _is_blank(value):
        if paid:
            results.append(
                ValidationResult(
                    category=ValidationCategory.TRACKING_UTMS,
                    rule_id=f"{field_name}_format",
                    status=ValidationStatus.PASS,
                    severity=ValidationSeverity.INFO,
                    message=f"{field_name} not supplied; format not evaluated.",
                    points_available=format_points,
                    points_earned=format_points,
                )
            )
        else:
            results.append(
                ValidationResult(
                    category=ValidationCategory.TRACKING_UTMS,
                    rule_id=f"{field_name}_format",
                    status=ValidationStatus.NOT_APPLICABLE,
                    severity=ValidationSeverity.INFO,
                    message=(
                        f"{field_name} not supplied; not applicable for "
                        "non-paid campaigns."
                    ),
                    points_available=format_points,
                    points_earned=format_points,
                )
            )
        return results

    issues = []
    if value != value.strip() or " " in value:
        issues.append("contains spaces")
    if value != value.lower():
        issues.append("contains uppercase characters")

    if issues:
        results.append(
            ValidationResult(
                category=ValidationCategory.TRACKING_UTMS,
                rule_id=f"{field_name}_format",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message=f"{field_name} value '{value}' {' and '.join(issues)}.",
                recommendation=(
                    f"Use a lowercase, space-free value for {field_name}."
                ),
                points_available=format_points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.TRACKING_UTMS,
                rule_id=f"{field_name}_format",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message=f"{field_name} value is well-formatted.",
                points_available=format_points,
                points_earned=format_points,
            )
        )

    return results


def _validate_utm_campaign_alignment(
    campaign: CampaignSubmission, paid: bool
) -> ValidationResult:
    """Compare ``utm_campaign`` against the normalised campaign name.

    utm_campaign is optional for non-paid campaigns, so an absent
    utm_campaign on a non-paid campaign is genuinely NOT_APPLICABLE. An
    absent utm_campaign on a paid campaign is instead an applicable field
    that's missing (already reported as a critical failure by
    ``utm_campaign_required``), so this stays a "not evaluated" PASS. A
    missing campaign_name is always the latter case, regardless of paid
    status, since campaign_name is universally required.
    """
    points = RULE_POINTS["utm_campaign_alignment"]

    if _is_blank(campaign.utm_campaign):
        if not paid:
            return ValidationResult(
                category=ValidationCategory.TRACKING_UTMS,
                rule_id="utm_campaign_alignment",
                status=ValidationStatus.NOT_APPLICABLE,
                severity=ValidationSeverity.INFO,
                message=(
                    "utm_campaign not supplied; not applicable for "
                    "non-paid campaigns."
                ),
                points_available=points,
                points_earned=points,
            )
        return ValidationResult(
            category=ValidationCategory.TRACKING_UTMS,
            rule_id="utm_campaign_alignment",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            message="utm_campaign not supplied; alignment not evaluated.",
            points_available=points,
            points_earned=points,
        )

    if _is_blank(campaign.campaign_name):
        return ValidationResult(
            category=ValidationCategory.TRACKING_UTMS,
            rule_id="utm_campaign_alignment",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            message="Campaign name not supplied; alignment not evaluated.",
            points_available=points,
            points_earned=points,
        )

    normalised_name = normalize_campaign_name(campaign.campaign_name)
    utm_campaign = campaign.utm_campaign
    assert utm_campaign is not None  # narrowed by the blank check above

    if utm_campaign == normalised_name:
        return ValidationResult(
            category=ValidationCategory.TRACKING_UTMS,
            rule_id="utm_campaign_alignment",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            message="utm_campaign matches the normalised campaign name.",
            points_available=points,
            points_earned=points,
        )

    return ValidationResult(
        category=ValidationCategory.TRACKING_UTMS,
        rule_id="utm_campaign_alignment",
        status=ValidationStatus.WARNING,
        severity=ValidationSeverity.WARNING,
        message=(
            f"utm_campaign '{utm_campaign}' does not match the normalised "
            f"campaign name '{normalised_name}'."
        ),
        recommendation="Align utm_campaign with the normalised campaign name.",
        points_available=points,
        points_earned=0,
    )


def _validate_destination_url_utms(
    campaign: CampaignSubmission, paid: bool
) -> ValidationResult:
    """Validate that a paid campaign's destination URL contains the
    required UTM query parameters, using real query-string parsing
    (never substring matching).
    """
    points = RULE_POINTS["destination_url_utms"]
    destination_url = campaign.destination_url

    if not paid:
        return ValidationResult(
            category=ValidationCategory.TRACKING_UTMS,
            rule_id="destination_url_utms",
            status=ValidationStatus.NOT_APPLICABLE,
            severity=ValidationSeverity.INFO,
            message=(
                "Destination URL UTM coverage is not required for "
                "non-paid campaigns."
            ),
            points_available=points,
            points_earned=points,
        )

    if _is_blank(destination_url) or not _parse_url(destination_url)[0]:
        return ValidationResult(
            category=ValidationCategory.TRACKING_UTMS,
            rule_id="destination_url_utms",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.INFO,
            message=(
                "Destination URL is missing or malformed; UTM coverage is "
                "reported by the URL validators instead."
            ),
            points_available=points,
            points_earned=points,
        )

    assert destination_url is not None  # narrowed by the blank check above
    query_params = parse_qs(urlparse(destination_url).query)
    missing = [
        key
        for key in ("utm_source", "utm_medium", "utm_campaign")
        if key not in query_params
    ]

    if missing:
        return ValidationResult(
            category=ValidationCategory.TRACKING_UTMS,
            rule_id="destination_url_utms",
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.CRITICAL,
            message=(
                "Destination URL is missing required UTM query "
                f"parameter(s): {', '.join(missing)}."
            ),
            recommendation=(
                "Add the missing UTM parameters to the destination URL "
                "query string."
            ),
            points_available=points,
            points_earned=0,
        )

    return ValidationResult(
        category=ValidationCategory.TRACKING_UTMS,
        rule_id="destination_url_utms",
        status=ValidationStatus.PASS,
        severity=ValidationSeverity.INFO,
        message="Destination URL contains all required UTM query parameters.",
        points_available=points,
        points_earned=points,
    )


def validate_utms(campaign: CampaignSubmission) -> list[ValidationResult]:
    """Validate UTM parameter presence, formatting, campaign-name
    alignment, and destination URL UTM coverage.
    """
    paid = _is_paid_campaign(campaign)
    results: list[ValidationResult] = []

    results.extend(_validate_utm_field("utm_source", campaign.utm_source, paid))
    results.extend(_validate_utm_field("utm_medium", campaign.utm_medium, paid))
    results.extend(
        _validate_utm_field("utm_campaign", campaign.utm_campaign, paid)
    )
    results.append(_validate_utm_campaign_alignment(campaign, paid))
    results.append(_validate_destination_url_utms(campaign, paid))

    return results


def validate_campaign_naming(campaign: CampaignSubmission) -> list[ValidationResult]:
    """Validate campaign name against deterministic naming convention rules.

    Sprint 1 checks syntax only (casing, spacing, underscore placement,
    allowed characters) — it does not attempt semantic validation of the
    market/audience/objective/period structure. All violations are
    warnings; naming issues are never critical.
    """
    name = campaign.campaign_name
    rule_ids = (
        "campaign_name_lowercase",
        "campaign_name_no_spaces",
        "campaign_name_characters",
        "campaign_name_underscore_placement",
        "campaign_name_consecutive_underscores",
    )

    if _is_blank(name):
        return [
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id=rule_id,
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Campaign name is missing; naming format not evaluated.",
                points_available=RULE_POINTS[rule_id],
                points_earned=RULE_POINTS[rule_id],
            )
            for rule_id in rule_ids
        ]

    results: list[ValidationResult] = []

    points = RULE_POINTS["campaign_name_lowercase"]
    if name != name.lower():
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_lowercase",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message=f"Campaign name '{name}' contains uppercase characters.",
                recommendation="Use lowercase letters in the campaign name.",
                points_available=points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_lowercase",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Campaign name is lowercase.",
                points_available=points,
                points_earned=points,
            )
        )

    points = RULE_POINTS["campaign_name_no_spaces"]
    if " " in name:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_no_spaces",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message=f"Campaign name '{name}' contains spaces.",
                recommendation=(
                    "Separate words with underscores instead of spaces."
                ),
                points_available=points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_no_spaces",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Campaign name contains no spaces.",
                points_available=points,
                points_earned=points,
            )
        )

    points = RULE_POINTS["campaign_name_characters"]
    if _INVALID_NAME_CHARACTERS.search(name):
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_characters",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Campaign name '{name}' contains characters other than "
                    "letters, digits, and underscores."
                ),
                recommendation=(
                    "Use only letters, digits, and underscores in the "
                    "campaign name."
                ),
                points_available=points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_characters",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Campaign name uses only allowed characters.",
                points_available=points,
                points_earned=points,
            )
        )

    points = RULE_POINTS["campaign_name_underscore_placement"]
    if name.startswith("_") or name.endswith("_"):
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_underscore_placement",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Campaign name '{name}' has a leading or trailing "
                    "underscore."
                ),
                recommendation=(
                    "Remove leading and trailing underscores from the "
                    "campaign name."
                ),
                points_available=points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_underscore_placement",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Campaign name has no leading or trailing underscore.",
                points_available=points,
                points_earned=points,
            )
        )

    points = RULE_POINTS["campaign_name_consecutive_underscores"]
    if "__" in name:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_consecutive_underscores",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
                message=f"Campaign name '{name}' contains consecutive underscores.",
                recommendation="Use a single underscore between words.",
                points_available=points,
                points_earned=0,
            )
        )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.NAMING_GOVERNANCE,
                rule_id="campaign_name_consecutive_underscores",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Campaign name contains no consecutive underscores.",
                points_available=points,
                points_earned=points,
            )
        )

    return results


def validate_launch_readiness(
    campaign: CampaignSubmission, reference_date: date
) -> list[ValidationResult]:
    """Validate launch date timing and (for paid campaigns) budget.

    ``reference_date`` is the date launch timing is measured against —
    callers must supply "today" explicitly rather than this function
    calling ``date.today()`` itself, so tests remain deterministic.
    """
    timing_points = RULE_POINTS["launch_date_timing"]
    budget_points = RULE_POINTS["paid_budget"]
    results: list[ValidationResult] = []

    if campaign.launch_date is None:
        results.append(
            ValidationResult(
                category=ValidationCategory.LAUNCH_READINESS,
                rule_id="launch_date_timing",
                status=ValidationStatus.PASS,
                severity=ValidationSeverity.INFO,
                message="Launch date is missing; timing not evaluated.",
                points_available=timing_points,
                points_earned=timing_points,
            )
        )
    else:
        days_until_launch = (campaign.launch_date - reference_date).days
        if days_until_launch < 0:
            results.append(
                ValidationResult(
                    category=ValidationCategory.LAUNCH_READINESS,
                    rule_id="launch_date_timing",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        f"Launch date {campaign.launch_date.isoformat()} is "
                        "in the past."
                    ),
                    recommendation="Set a launch date that is today or later.",
                    points_available=timing_points,
                    points_earned=0,
                )
            )
        elif days_until_launch in (0, 1):
            when = "today" if days_until_launch == 0 else "tomorrow"
            results.append(
                ValidationResult(
                    category=ValidationCategory.LAUNCH_READINESS,
                    rule_id="launch_date_timing",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Launch date is {when}, leaving little time to "
                        "address issues."
                    ),
                    recommendation=(
                        "Allow at least 2 days between QA and launch where "
                        "possible."
                    ),
                    points_available=timing_points,
                    points_earned=timing_points / 2,
                )
            )
        else:
            results.append(
                ValidationResult(
                    category=ValidationCategory.LAUNCH_READINESS,
                    rule_id="launch_date_timing",
                    status=ValidationStatus.PASS,
                    severity=ValidationSeverity.INFO,
                    message="Launch date allows sufficient lead time.",
                    points_available=timing_points,
                    points_earned=timing_points,
                )
            )

    if _is_paid_campaign(campaign):
        budget = campaign.budget
        if budget is None or budget <= 0:
            results.append(
                ValidationResult(
                    category=ValidationCategory.LAUNCH_READINESS,
                    rule_id="paid_budget",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        "Budget is missing or not greater than zero for a "
                        "paid campaign."
                    ),
                    recommendation=(
                        "Set a budget greater than zero for paid campaigns."
                    ),
                    points_available=budget_points,
                    points_earned=0,
                )
            )
        else:
            results.append(
                ValidationResult(
                    category=ValidationCategory.LAUNCH_READINESS,
                    rule_id="paid_budget",
                    status=ValidationStatus.PASS,
                    severity=ValidationSeverity.INFO,
                    message="Budget is set and greater than zero.",
                    points_available=budget_points,
                    points_earned=budget_points,
                )
            )
    else:
        results.append(
            ValidationResult(
                category=ValidationCategory.LAUNCH_READINESS,
                rule_id="paid_budget",
                status=ValidationStatus.NOT_APPLICABLE,
                severity=ValidationSeverity.INFO,
                message="Budget is not required for non-paid campaigns.",
                points_available=budget_points,
                points_earned=budget_points,
            )
        )

    return results


def validate_campaign(
    campaign: CampaignSubmission, *, reference_date: date | None = None
) -> list[ValidationResult]:
    """Run every applicable validator for a campaign and return all results.

    ``reference_date`` defaults to today but can be supplied explicitly for
    deterministic testing of launch-date timing rules.
    """
    effective_reference_date = reference_date or date.today()

    results: list[ValidationResult] = []
    results.extend(validate_required_fields(campaign))
    results.extend(validate_cta(campaign))
    results.extend(validate_landing_page_url(campaign))
    results.extend(validate_destination_url(campaign))
    results.extend(validate_utms(campaign))
    results.extend(validate_campaign_naming(campaign))
    results.extend(validate_launch_readiness(campaign, effective_reference_date))
    return results
