"""Campaign QA scoring logic.

Consumes the results of :func:`src.validators.validate_campaign` and turns
them into an overall :class:`~src.models.QAResult`. This module performs no
validation of its own — it never inspects `CampaignSubmission` fields
directly — and never recalculates category weights; those are the
validators' responsibility (see project_management/DECISIONS.md, Decision
002/003).

Because every validator rule always fires (Decision 003), the validators
guarantee ``sum(points_available) == 100`` for every campaign, so the score
is simply ``sum(points_earned)``. Status is then derived from that score
plus a critical-failure override, per Decision 002:

- 90-100 with no critical failures -> PASS
- 90-100 with one or more critical failures -> REVIEW
- 70-89 -> REVIEW
- 0-69 -> FAIL

A critical failure is a result with ``ValidationStatus.FAIL`` and
``ValidationSeverity.CRITICAL``. ``NOT_APPLICABLE`` results are always
``ValidationSeverity.INFO`` and can never count as a warning, a failure, or
a critical failure.
"""

from __future__ import annotations

from datetime import date

from .models import (
    CampaignSubmission,
    QAResult,
    QAStatus,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from .validators import validate_campaign

_PASS_THRESHOLD = 90
_REVIEW_THRESHOLD = 70


def _calculate_score(results: list[ValidationResult]) -> float:
    """Sum points_earned, after defensively verifying the denominator.

    The validators guarantee sum(points_available) == 100 (Decision 003),
    but this is re-verified here rather than trusted blindly, since a
    broken denominator would silently corrupt every score.
    """
    total_available = sum(result.points_available for result in results)
    if total_available != 100:
        raise ValueError(
            "Validation results do not sum to 100 available points "
            f"(got {total_available}); the validator layer has violated "
            "its Decision 003 guarantee."
        )

    score = sum(result.points_earned for result in results)
    if not (0 <= score <= 100):
        raise ValueError(
            f"Calculated score {score} is outside the valid 0-100 range."
        )

    return score


def _critical_failures(results: list[ValidationResult]) -> list[ValidationResult]:
    """Results that are both CRITICAL severity and a FAIL status.

    Matches QAResult.critical_failures exactly (see src/models.py) — this
    must be computed before a QAResult can be constructed, since QAStatus
    is one of QAResult's required fields.
    """
    return [
        result
        for result in results
        if result.severity == ValidationSeverity.CRITICAL
        and result.status == ValidationStatus.FAIL
    ]


def _determine_status(
    score: float, critical_failures: list[ValidationResult]
) -> QAStatus:
    """Apply the Decision 002 PASS/REVIEW/FAIL thresholds and
    critical-failure override."""
    if score >= _PASS_THRESHOLD:
        return QAStatus.REVIEW if critical_failures else QAStatus.PASS
    if score >= _REVIEW_THRESHOLD:
        return QAStatus.REVIEW
    return QAStatus.FAIL


def score_campaign(
    campaign: CampaignSubmission, *, reference_date: date | None = None
) -> QAResult:
    """Run the QA engine on a campaign and return its overall QA result.

    ``reference_date`` is passed straight through to
    :func:`~src.validators.validate_campaign` for deterministic launch-date
    timing evaluation; see that function for details.
    """
    results = validate_campaign(campaign, reference_date=reference_date)
    score = _calculate_score(results)
    status = _determine_status(score, _critical_failures(results))

    return QAResult(
        campaign=campaign,
        validation_results=results,
        score=score,
        status=status,
    )
