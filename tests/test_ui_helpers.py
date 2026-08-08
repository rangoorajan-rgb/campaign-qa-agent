"""Tests for src.ui_helpers.

Covers only the pure, Streamlit-independent helpers (category_breakdown,
format_points, the CATEGORY_LABELS/STATUS_META data, and the example
campaign presets). No Streamlit rendering is tested here — per Sprint 2
scope, UI rendering is verified manually in the browser, not with
brittle automated UI tests.
"""

from src.models import (
    QAStatus,
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from src.scoring import score_campaign
from src.ui_helpers import (
    CATEGORY_LABELS,
    STATUS_META,
    category_breakdown,
    category_status_label,
    example_campaigns,
    format_points,
    group_by_category,
)


def make_result(**overrides: object) -> ValidationResult:
    defaults: dict[str, object] = dict(
        category=ValidationCategory.TRACKING_UTMS,
        rule_id="fake_rule",
        status=ValidationStatus.PASS,
        severity=ValidationSeverity.INFO,
        message="fake",
        points_available=10,
        points_earned=10,
    )
    defaults.update(overrides)
    return ValidationResult(**defaults)  # type: ignore[arg-type]


class TestCategoryBreakdown:
    def test_includes_every_category_even_with_no_results(self) -> None:
        breakdown = category_breakdown([])

        assert set(breakdown.keys()) == set(ValidationCategory)
        assert all(value == (0.0, 0.0) for value in breakdown.values())

    def test_sums_points_within_a_category(self) -> None:
        results = [
            make_result(
                category=ValidationCategory.NAMING_GOVERNANCE,
                points_available=3,
                points_earned=3,
            ),
            make_result(
                category=ValidationCategory.NAMING_GOVERNANCE,
                points_available=3,
                points_earned=0,
            ),
        ]

        breakdown = category_breakdown(results)

        assert breakdown[ValidationCategory.NAMING_GOVERNANCE] == (3.0, 6.0)

    def test_keeps_categories_independent(self) -> None:
        results = [
            make_result(category=ValidationCategory.TRACKING_UTMS, points_available=6, points_earned=6),
            make_result(category=ValidationCategory.LAUNCH_READINESS, points_available=10, points_earned=5),
        ]

        breakdown = category_breakdown(results)

        assert breakdown[ValidationCategory.TRACKING_UTMS] == (6.0, 6.0)
        assert breakdown[ValidationCategory.LAUNCH_READINESS] == (5.0, 10.0)
        assert breakdown[ValidationCategory.REQUIRED_INFORMATION] == (0.0, 0.0)


class TestGroupByCategory:
    def test_includes_every_category_even_with_no_results(self) -> None:
        grouped = group_by_category([])

        assert set(grouped.keys()) == set(ValidationCategory)
        assert all(value == [] for value in grouped.values())

    def test_groups_results_under_their_own_category_only(self) -> None:
        utm_result = make_result(category=ValidationCategory.TRACKING_UTMS)
        naming_result = make_result(category=ValidationCategory.NAMING_GOVERNANCE)

        grouped = group_by_category([utm_result, naming_result])

        assert grouped[ValidationCategory.TRACKING_UTMS] == [utm_result]
        assert grouped[ValidationCategory.NAMING_GOVERNANCE] == [naming_result]
        assert grouped[ValidationCategory.URL_INTEGRITY] == []


class TestCategoryStatusLabel:
    def test_no_results_is_clear(self) -> None:
        assert category_status_label([]) == ("Clear", "cat-status-pass")

    def test_all_passing_is_clear(self) -> None:
        results = [make_result(status=ValidationStatus.PASS)]

        assert category_status_label(results) == ("Clear", "cat-status-pass")

    def test_not_applicable_only_is_clear(self) -> None:
        results = [
            make_result(
                status=ValidationStatus.NOT_APPLICABLE,
                severity=ValidationSeverity.INFO,
            )
        ]

        assert category_status_label(results) == ("Clear", "cat-status-pass")

    def test_a_warning_needs_review(self) -> None:
        results = [
            make_result(status=ValidationStatus.PASS),
            make_result(
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
            ),
        ]

        assert category_status_label(results) == ("Needs Review", "cat-status-review")

    def test_a_critical_failure_is_critical(self) -> None:
        results = [
            make_result(status=ValidationStatus.PASS),
            make_result(
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.WARNING,
            ),
            make_result(
                status=ValidationStatus.FAIL,
                severity=ValidationSeverity.CRITICAL,
            ),
        ]

        assert category_status_label(results) == ("Critical", "cat-status-fail")

    def test_a_non_critical_fail_alone_is_needs_review_not_critical(self) -> None:
        """A FAIL that isn't CRITICAL severity shouldn't happen in
        practice (the engine always pairs FAIL with CRITICAL), but a FAIL
        must never silently read as fully "Clear" regardless."""
        results = [
            make_result(status=ValidationStatus.FAIL, severity=ValidationSeverity.WARNING)
        ]

        assert category_status_label(results) == ("Needs Review", "cat-status-review")


class TestFormatPoints:
    def test_whole_numbers_render_without_decimal(self) -> None:
        assert format_points(24, 30) == "24 / 30"

    def test_fractional_points_render_with_decimal(self) -> None:
        assert format_points(1.5, 2) == "1.5 / 2"


class TestCategoryLabels:
    def test_every_validation_category_has_a_label(self) -> None:
        assert set(CATEGORY_LABELS.keys()) == set(ValidationCategory)
        assert all(isinstance(label, str) and label for label in CATEGORY_LABELS.values())


class TestStatusMeta:
    def test_every_qa_status_has_metadata(self) -> None:
        assert set(STATUS_META.keys()) == set(QAStatus)

    def test_recommendation_copy_matches_spec(self) -> None:
        assert STATUS_META[QAStatus.PASS]["recommendation"] == (
            "Campaign meets the deterministic launch-readiness threshold."
        )
        assert STATUS_META[QAStatus.REVIEW]["recommendation"] == (
            "Resolve flagged issues before launch approval."
        )
        assert STATUS_META[QAStatus.FAIL]["recommendation"] == (
            "Campaign is not launch-ready and requires remediation."
        )


class TestExampleCampaigns:
    def test_returns_exactly_the_three_expected_presets(self) -> None:
        examples = example_campaigns()

        assert set(examples.keys()) == {
            "Clean Paid Search",
            "Warning-heavy Paid Social",
            "Failing Campaign",
        }

    def test_clean_paid_search_passes(self) -> None:
        qa_result = score_campaign(example_campaigns()["Clean Paid Search"])

        assert qa_result.status == QAStatus.PASS
        assert qa_result.critical_failures == []

    def test_warning_heavy_paid_social_reviews(self) -> None:
        qa_result = score_campaign(example_campaigns()["Warning-heavy Paid Social"])

        assert qa_result.status == QAStatus.REVIEW

    def test_failing_campaign_fails(self) -> None:
        qa_result = score_campaign(example_campaigns()["Failing Campaign"])

        assert qa_result.status == QAStatus.FAIL
        assert qa_result.critical_failures != []

    def test_launch_dates_are_never_in_the_past_for_the_clean_and_warning_examples(
        self,
    ) -> None:
        from datetime import date

        examples = example_campaigns()
        assert examples["Clean Paid Search"].launch_date > date.today()
        assert examples["Warning-heavy Paid Social"].launch_date > date.today()
