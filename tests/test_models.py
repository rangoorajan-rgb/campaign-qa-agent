"""Tests for src.models.

Covers only the domain models themselves (construction, invariants, and
derived helper properties). Validation and scoring logic do not exist yet
and are not tested here.
"""

from datetime import date

import pytest

from src.models import (
    CampaignSubmission,
    QAResult,
    QAStatus,
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


def make_campaign(**overrides: object) -> CampaignSubmission:
    defaults: dict[str, object] = dict(
        campaign_name="UK Enterprise Demo Q3 2026",
        campaign_type="Paid Search",
        channel="Google Ads",
        objective="Demo Signups",
        target_audience="UK Enterprise",
        landing_page_url="https://example.com/demo",
        cta="Book a demo",
        campaign_owner="Jane Doe",
        launch_date=date(2026, 9, 1),
    )
    defaults.update(overrides)
    return CampaignSubmission(**defaults)  # type: ignore[arg-type]


def make_result(**overrides: object) -> ValidationResult:
    defaults: dict[str, object] = dict(
        category=ValidationCategory.TRACKING_UTMS,
        rule_id="utm_source_required",
        status=ValidationStatus.PASS,
        severity=ValidationSeverity.INFO,
        message="utm_source is present.",
        points_available=10,
        points_earned=10,
    )
    defaults.update(overrides)
    return ValidationResult(**defaults)  # type: ignore[arg-type]


class TestCampaignSubmission:
    def test_instantiates_with_required_fields(self) -> None:
        campaign = make_campaign()

        assert campaign.campaign_name == "UK Enterprise Demo Q3 2026"
        assert campaign.campaign_type == "Paid Search"
        assert campaign.launch_date == date(2026, 9, 1)

    def test_optional_fields_default_to_none(self) -> None:
        campaign = make_campaign()

        assert campaign.destination_url is None
        assert campaign.utm_source is None
        assert campaign.utm_medium is None
        assert campaign.utm_campaign is None
        assert campaign.budget is None
        assert campaign.campaign_message is None

    def test_optional_fields_can_be_supplied(self) -> None:
        campaign = make_campaign(
            destination_url="https://example.com/demo?utm_source=google",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="uk_enterprise_demo_q3_2026",
            budget=5000.0,
            campaign_message="Book your enterprise demo today.",
        )

        assert campaign.utm_source == "google"
        assert campaign.budget == 5000.0


class TestValidationResult:
    def test_stores_structured_data(self) -> None:
        result = make_result(
            category=ValidationCategory.URL_INTEGRITY,
            rule_id="landing_page_url_valid",
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.WARNING,
            message="Landing page URL uses HTTP instead of HTTPS.",
            recommendation="Use an HTTPS landing page URL.",
            points_available=20,
            points_earned=15,
        )

        assert result.category == ValidationCategory.URL_INTEGRITY
        assert result.rule_id == "landing_page_url_valid"
        assert result.status == ValidationStatus.WARNING
        assert result.severity == ValidationSeverity.WARNING
        assert result.recommendation == "Use an HTTPS landing page URL."
        assert result.points_available == 20
        assert result.points_earned == 15

    def test_recommendation_is_optional(self) -> None:
        result = make_result()

        assert result.recommendation is None

    def test_points_earned_cannot_exceed_points_available(self) -> None:
        with pytest.raises(ValueError):
            make_result(points_available=10, points_earned=15)

    def test_points_earned_equal_to_points_available_is_allowed(self) -> None:
        result = make_result(points_available=10, points_earned=10)

        assert result.points_earned == result.points_available


class TestQAResult:
    def test_helper_properties_separate_results_by_status(self) -> None:
        passed = make_result(rule_id="passed_check", status=ValidationStatus.PASS)
        warned = make_result(
            rule_id="warned_check",
            status=ValidationStatus.WARNING,
            severity=ValidationSeverity.WARNING,
            points_earned=5,
        )
        failed = make_result(
            rule_id="failed_check",
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.WARNING,
            points_earned=0,
        )
        not_applicable = make_result(
            rule_id="paid_budget",
            status=ValidationStatus.NOT_APPLICABLE,
            severity=ValidationSeverity.INFO,
        )

        qa_result = QAResult(
            campaign=make_campaign(),
            validation_results=[passed, warned, failed, not_applicable],
            score=75,
            status=QAStatus.REVIEW,
        )

        assert qa_result.passed_checks == [passed]
        assert qa_result.warnings == [warned]
        assert qa_result.failed_checks == [failed]
        assert qa_result.not_applicable_checks == [not_applicable]

    def test_passed_checks_excludes_not_applicable(self) -> None:
        """NOT_APPLICABLE is a distinct outcome from PASS: a rule that
        didn't apply must never be counted as one that was evaluated and
        satisfied."""
        not_applicable = make_result(
            rule_id="paid_budget",
            status=ValidationStatus.NOT_APPLICABLE,
            severity=ValidationSeverity.INFO,
        )

        qa_result = QAResult(
            campaign=make_campaign(),
            validation_results=[not_applicable],
            score=100,
            status=QAStatus.PASS,
        )

        assert qa_result.passed_checks == []
        assert qa_result.not_applicable_checks == [not_applicable]

    def test_critical_failures_requires_critical_severity_and_fail_status(
        self,
    ) -> None:
        critical_fail = make_result(
            rule_id="missing_campaign_owner",
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.CRITICAL,
            points_earned=0,
        )
        non_critical_fail = make_result(
            rule_id="cta_too_long",
            status=ValidationStatus.FAIL,
            severity=ValidationSeverity.WARNING,
            points_earned=0,
        )
        critical_pass = make_result(
            rule_id="campaign_owner_present",
            status=ValidationStatus.PASS,
            severity=ValidationSeverity.CRITICAL,
        )

        qa_result = QAResult(
            campaign=make_campaign(),
            validation_results=[critical_fail, non_critical_fail, critical_pass],
            score=60,
            status=QAStatus.FAIL,
        )

        assert qa_result.critical_failures == [critical_fail]

    def test_no_critical_failures_when_none_present(self) -> None:
        qa_result = QAResult(
            campaign=make_campaign(),
            validation_results=[make_result()],
            score=100,
            status=QAStatus.PASS,
        )

        assert qa_result.critical_failures == []
