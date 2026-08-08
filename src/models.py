"""Domain models for campaign submissions and QA results.

These models define the structured representations shared by the
rule-based QA engine, the scoring logic, and downstream consumers
(Streamlit UI, Google Sheets logging, Slack notifications). They contain
no validation or scoring logic themselves — only data structure and the
minimal internal consistency checks needed to keep that data trustworthy
(e.g. a result cannot award more points than were available).

The deterministic rules that will populate these models are defined in
project_management/DECISIONS.md, Decision 002.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ValidationStatus(str, Enum):
    """Outcome of a single validation check.

    ``NOT_APPLICABLE`` is distinct from ``PASS``: it means the rule
    genuinely does not apply to this campaign (e.g. a paid-only
    requirement evaluated against a non-paid campaign), not that the
    campaign satisfied it. Both award full points, but only ``PASS``
    represents an evaluated, satisfied check.
    """

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValidationSeverity(str, Enum):
    """Severity of a single validation check."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ValidationCategory(str, Enum):
    """QA scoring category a validation check belongs to."""

    TRACKING_UTMS = "TRACKING_UTMS"
    REQUIRED_INFORMATION = "REQUIRED_INFORMATION"
    URL_INTEGRITY = "URL_INTEGRITY"
    NAMING_GOVERNANCE = "NAMING_GOVERNANCE"
    LAUNCH_READINESS = "LAUNCH_READINESS"


class QAStatus(str, Enum):
    """Final launch-readiness outcome for a campaign submission."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass
class CampaignSubmission:
    """Campaign data submitted for pre-launch QA review.

    Required fields have no defaults: callers must supply real values
    rather than relying on placeholders, since a missing required field
    is itself something the QA engine must be able to detect.
    """

    campaign_name: str
    campaign_type: str
    channel: str
    objective: str
    target_audience: str
    landing_page_url: str
    cta: str
    campaign_owner: str
    launch_date: date
    destination_url: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    budget: float | None = None
    campaign_message: str | None = None


@dataclass
class ValidationResult:
    """Outcome of a single validation rule applied to a campaign.

    ``recommendation`` is optional: a passing check has nothing to
    recommend. ``points_earned`` cannot exceed ``points_available`` — this
    is enforced at construction time so an inconsistent result can never
    be created.
    """

    category: ValidationCategory
    rule_id: str
    status: ValidationStatus
    severity: ValidationSeverity
    message: str
    points_available: float
    points_earned: float
    recommendation: str | None = None

    def __post_init__(self) -> None:
        if self.points_earned > self.points_available:
            raise ValueError(
                f"rule '{self.rule_id}': points_earned "
                f"({self.points_earned}) cannot exceed points_available "
                f"({self.points_available})"
            )


@dataclass
class QAResult:
    """Overall QA outcome for a campaign submission.

    ``score`` and ``status`` are computed by scoring.py and passed in
    here — this model only stores the outcome, it does not calculate it.
    ``critical_failures`` and the other helper properties are derived
    from ``validation_results`` rather than stored separately, so they
    can never drift out of sync with the underlying results.
    """

    campaign: CampaignSubmission
    validation_results: list[ValidationResult]
    score: float
    status: QAStatus

    @property
    def critical_failures(self) -> list[ValidationResult]:
        """Results that are both CRITICAL severity and a FAIL status."""
        return [
            result
            for result in self.validation_results
            if result.severity == ValidationSeverity.CRITICAL
            and result.status == ValidationStatus.FAIL
        ]

    @property
    def passed_checks(self) -> list[ValidationResult]:
        """Results with a PASS status. Excludes NOT_APPLICABLE."""
        return [
            result
            for result in self.validation_results
            if result.status == ValidationStatus.PASS
        ]

    @property
    def not_applicable_checks(self) -> list[ValidationResult]:
        """Results with a NOT_APPLICABLE status."""
        return [
            result
            for result in self.validation_results
            if result.status == ValidationStatus.NOT_APPLICABLE
        ]

    @property
    def warnings(self) -> list[ValidationResult]:
        """Results with a WARNING status."""
        return [
            result
            for result in self.validation_results
            if result.status == ValidationStatus.WARNING
        ]

    @property
    def failed_checks(self) -> list[ValidationResult]:
        """Results with a FAIL status."""
        return [
            result
            for result in self.validation_results
            if result.status == ValidationStatus.FAIL
        ]


class GeminiReviewStatus(str, Enum):
    """Outcome of an attempted Gemini qualitative review.

    Distinguishing NOT_CONFIGURED from ERROR lets the UI show an
    appropriately calm message either way: an unconfigured API key is an
    expected local-dev state, not a failure worth alarming a user about.
    """

    OK = "OK"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    ERROR = "ERROR"


class GeminiConcernSeverity(str, Enum):
    """Gemini's own qualitative severity scale for a single concern.

    Deliberately distinct from ValidationSeverity: these are Gemini's
    subjective judgments, not deterministic rule outcomes, and must never
    be visually or semantically conflated with CRITICAL/WARNING/INFO.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class GeminiConcern:
    """One qualitative concern raised by the Gemini review."""

    title: str
    explanation: str
    severity: GeminiConcernSeverity


@dataclass
class GeminiReview:
    """The qualitative review content Gemini returned.

    Deliberately has no score and no PASS/REVIEW/FAIL-shaped field —
    Gemini is advisory only; the deterministic QAResult remains the sole
    source of the governance verdict.
    """

    summary: str
    concerns: list[GeminiConcern]
    strengths: list[str]
    recommendation: str


@dataclass
class GeminiReviewResult:
    """Outcome of calling src.gemini_analyzer.analyze_campaign().

    Always a valid, fully-formed object regardless of what happened
    internally (success, missing config, or an API/parsing failure) so
    callers never need to catch exceptions from a Gemini call themselves.
    """

    status: GeminiReviewStatus
    review: GeminiReview | None = None
    error_message: str | None = None


class WebhookDeliveryStatus(str, Enum):
    """Outcome of attempting to deliver a QA result to an outbound webhook.

    Mirrors GeminiReviewStatus's shape for the same reason: distinguishing
    NOT_CONFIGURED (expected when no webhook URL is set) from ERROR
    (delivery was attempted and failed) lets the UI stay calm either way,
    and lets NOT_CONFIGURED be rendered as nothing at all rather than a
    false alarm.
    """

    SENT = "SENT"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    ERROR = "ERROR"


@dataclass
class WebhookDeliveryResult:
    """Outcome of calling src.webhook.send_to_make().

    Deliberately generic (not Make-specific in name) since a future Slack
    webhook can reuse this same result shape rather than a near-duplicate
    type. Always a valid, fully-formed object regardless of what happened
    internally, so callers never need to catch exceptions themselves.
    """

    status: WebhookDeliveryStatus
    http_status_code: int | None = None
    error_message: str | None = None
