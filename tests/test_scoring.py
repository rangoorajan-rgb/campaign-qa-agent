"""Tests for src.scoring.

Covers score calculation, PASS/REVIEW/FAIL status determination, the
critical-failure override, defensive validation of the validator output,
and reference_date pass-through. Boundary scores (69/70/89/90) and the
defensive-validation error paths are tested by constructing
ValidationResult lists directly and calling the internal helpers, per the
task's own guidance that this is acceptable where it's the cleanest way
to hit an exact value.
"""

from datetime import date, timedelta

import pytest

from src.models import (
    CampaignSubmission,
    QAStatus,
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from src.scoring import _calculate_score, _critical_failures, _determine_status, score_campaign
from src.validators import validate_campaign

REFERENCE_DATE = date(2026, 8, 7)


def make_campaign(**overrides: object) -> CampaignSubmission:
    """A fully compliant paid campaign, overridable per test."""
    defaults: dict[str, object] = dict(
        campaign_name="uk_enterprise_demo_q3_2026",
        campaign_type="Paid Search",
        channel="Google Ads",
        objective="Demo Signups",
        target_audience="UK Enterprise",
        landing_page_url="https://example.com/demo",
        cta="Book a demo",
        campaign_owner="Jane Doe",
        launch_date=REFERENCE_DATE + timedelta(days=5),
        destination_url=(
            "https://example.com/demo?utm_source=google&utm_medium=cpc"
            "&utm_campaign=uk_enterprise_demo_q3_2026"
        ),
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="uk_enterprise_demo_q3_2026",
        budget=5000.0,
    )
    defaults.update(overrides)
    return CampaignSubmission(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> ValidationResult:
    defaults: dict[str, object] = dict(
        category=ValidationCategory.REQUIRED_INFORMATION,
        rule_id="fake_rule",
        status=ValidationStatus.PASS,
        severity=ValidationSeverity.INFO,
        message="fake",
        points_available=100,
        points_earned=100,
    )
    defaults.update(overrides)
    return ValidationResult(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# score_campaign — realistic end-to-end scenarios
# ---------------------------------------------------------------------------


class TestScoreCampaign:
    def test_compliant_paid_campaign_scores_100_and_passes(self) -> None:
        qa_result = score_campaign(make_campaign(), reference_date=REFERENCE_DATE)

        assert qa_result.score == 100
        assert qa_result.status == QAStatus.PASS
        assert qa_result.critical_failures == []

    def test_compliant_non_paid_campaign_scores_100_and_passes(self) -> None:
        qa_result = score_campaign(
            make_campaign(
                campaign_type="Email",
                destination_url=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                budget=None,
            ),
            reference_date=REFERENCE_DATE,
        )

        assert qa_result.score == 100
        assert qa_result.status == QAStatus.PASS
        assert qa_result.critical_failures == []

    def test_not_applicable_does_not_behave_as_failure(self) -> None:
        """A non-paid campaign's NOT_APPLICABLE results (paid_budget,
        utm_*_required, destination_url_required, destination_url_utms)
        must not count as warnings, failures, or critical failures."""
        qa_result = score_campaign(
            make_campaign(
                campaign_type="Organic Social",
                destination_url=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                budget=None,
            ),
            reference_date=REFERENCE_DATE,
        )

        assert qa_result.not_applicable_checks != []
        assert qa_result.warnings == []
        assert qa_result.failed_checks == []
        assert qa_result.critical_failures == []
        assert qa_result.score == 100
        assert qa_result.status == QAStatus.PASS

    def test_score_between_90_and_100_with_no_critical_failures_is_pass(
        self,
    ) -> None:
        qa_result = score_campaign(
            make_campaign(landing_page_url="http://example.com/demo"),
            reference_date=REFERENCE_DATE,
        )

        assert 90 <= qa_result.score < 100
        assert qa_result.critical_failures == []
        assert qa_result.status == QAStatus.PASS

    def test_score_between_90_and_100_with_a_critical_failure_is_review(
        self,
    ) -> None:
        qa_result = score_campaign(
            make_campaign(channel=""), reference_date=REFERENCE_DATE
        )

        assert 90 <= qa_result.score < 100
        assert len(qa_result.critical_failures) == 1
        assert qa_result.status == QAStatus.REVIEW

    def test_warning_deductions_move_pass_into_review(self) -> None:
        """Without the warnings below this campaign would score 100/PASS;
        with them, it drops into the 70-89 REVIEW band despite having no
        critical failures at all."""
        qa_result = score_campaign(
            make_campaign(
                campaign_name="UK Enterprise Demo Q3 2026",
                landing_page_url="http://example.com/demo",
                cta="x" * 61,
            ),
            reference_date=REFERENCE_DATE,
        )

        assert qa_result.critical_failures == []
        assert 70 <= qa_result.score <= 89
        assert qa_result.status == QAStatus.REVIEW

    def test_score_below_70_is_fail(self) -> None:
        qa_result = score_campaign(
            make_campaign(
                campaign_name="",
                channel="",
                objective="",
                target_audience="",
                campaign_owner="",
                destination_url=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                budget=None,
            ),
            reference_date=REFERENCE_DATE,
        )

        assert qa_result.score < 70
        assert qa_result.status == QAStatus.FAIL

    def test_score_equals_sum_of_points_earned(self) -> None:
        campaign = make_campaign(utm_source="Google")
        qa_result = score_campaign(campaign, reference_date=REFERENCE_DATE)

        assert qa_result.score == sum(
            r.points_earned for r in qa_result.validation_results
        )

    def test_qa_result_contains_exactly_the_validator_output(self) -> None:
        campaign = make_campaign()
        qa_result = score_campaign(campaign, reference_date=REFERENCE_DATE)
        expected_results = validate_campaign(campaign, reference_date=REFERENCE_DATE)

        assert qa_result.validation_results == expected_results
        assert qa_result.campaign is campaign

    def test_reference_date_passes_through_correctly(self) -> None:
        campaign = make_campaign(launch_date=REFERENCE_DATE + timedelta(days=1))

        near_result = score_campaign(campaign, reference_date=REFERENCE_DATE)
        far_result = score_campaign(
            campaign, reference_date=REFERENCE_DATE - timedelta(days=10)
        )

        near_timing = next(
            r
            for r in near_result.validation_results
            if r.rule_id == "launch_date_timing"
        )
        far_timing = next(
            r
            for r in far_result.validation_results
            if r.rule_id == "launch_date_timing"
        )

        assert near_timing.status == ValidationStatus.WARNING
        assert far_timing.status == ValidationStatus.PASS
        assert near_result.score != far_result.score


# ---------------------------------------------------------------------------
# _calculate_score — boundaries and defensive validation
# ---------------------------------------------------------------------------


class TestCalculateScore:
    def test_score_equals_sum_of_points_earned(self) -> None:
        results = [
            make_result(rule_id="a", points_available=60, points_earned=60),
            make_result(rule_id="b", points_available=40, points_earned=29),
        ]

        assert _calculate_score(results) == 89

    def test_malformed_denominator_raises_value_error(self) -> None:
        results = [
            make_result(rule_id="a", points_available=50, points_earned=50),
        ]

        with pytest.raises(ValueError):
            _calculate_score(results)

    def test_invalid_negative_score_raises_value_error(self) -> None:
        results = [
            make_result(rule_id="a", points_available=100, points_earned=-5),
        ]

        with pytest.raises(ValueError):
            _calculate_score(results)


# ---------------------------------------------------------------------------
# _determine_status — exact boundary values
# ---------------------------------------------------------------------------


class TestDetermineStatus:
    def test_score_90_no_critical_failures_is_pass(self) -> None:
        assert _determine_status(90, []) == QAStatus.PASS

    def test_score_100_no_critical_failures_is_pass(self) -> None:
        assert _determine_status(100, []) == QAStatus.PASS

    def test_score_90_with_critical_failure_is_review(self) -> None:
        critical = make_result(
            status=ValidationStatus.FAIL, severity=ValidationSeverity.CRITICAL
        )
        assert _determine_status(90, [critical]) == QAStatus.REVIEW

    def test_score_89_is_review(self) -> None:
        assert _determine_status(89, []) == QAStatus.REVIEW

    def test_score_70_is_review(self) -> None:
        assert _determine_status(70, []) == QAStatus.REVIEW

    def test_score_69_is_fail(self) -> None:
        assert _determine_status(69, []) == QAStatus.FAIL

    def test_score_0_is_fail(self) -> None:
        assert _determine_status(0, []) == QAStatus.FAIL

    def test_score_69_with_critical_failure_is_still_fail_not_review(self) -> None:
        """The critical-failure override only ever downgrades PASS to
        REVIEW — it never upgrades a low score."""
        critical = make_result(
            status=ValidationStatus.FAIL, severity=ValidationSeverity.CRITICAL
        )
        assert _determine_status(69, [critical]) == QAStatus.FAIL


# ---------------------------------------------------------------------------
# _critical_failures
# ---------------------------------------------------------------------------


class TestCriticalFailures:
    def test_requires_both_critical_severity_and_fail_status(self) -> None:
        critical_fail = make_result(
            rule_id="a",
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.CRITICAL,
        )
        warning = make_result(
            rule_id="b",
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.WARNING,
        )
        not_applicable = make_result(
            rule_id="c",
            status=ValidationStatus.NOT_APPLICABLE,
            severity=ValidationSeverity.INFO,
        )
        critical_pass = make_result(
            rule_id="d",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.CRITICAL,
        )

        results = [critical_fail, warning, not_applicable, critical_pass]

        assert _critical_failures(results) == [critical_fail]
