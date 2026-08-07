"""Integration tests for the deterministic QA pipeline.

Exercises the real pipeline — CampaignSubmission -> validate_campaign() ->
score_campaign() -> QAResult — against the representative sample dataset
in data/sample_campaigns.csv. No mocking: every row runs through the
actual validators and scoring engine, not a stand-in.

The dataset's `quality_tier` column (dataset metadata, not a
CampaignSubmission field — see data/README.md) groups rows by intended
outcome, which these tests verify against the real pipeline's output.
"""

import csv
from datetime import date
from pathlib import Path

import pytest

from src.constants import PAID_CAMPAIGN_TYPES
from src.models import CampaignSubmission, QAStatus, ValidationStatus
from src.scoring import score_campaign

REFERENCE_DATE = date(2026, 8, 7)
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_campaigns.csv"

# Rules whose NOT_APPLICABLE-ness is governed by paid vs. non-paid status
# (see project_management/DECISIONS.md, Decision 003 amendment).
PAID_ONLY_RULE_IDS = {
    "utm_source_required",
    "utm_medium_required",
    "utm_campaign_required",
    "destination_url_required",
    "destination_url_utms",
    "paid_budget",
    "utm_campaign_alignment",
}


def _load_rows() -> list[dict[str, str]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _row_to_campaign(row: dict[str, str]) -> CampaignSubmission:
    return CampaignSubmission(
        campaign_name=row["campaign_name"],
        campaign_type=row["campaign_type"],
        channel=row["channel"],
        objective=row["objective"],
        target_audience=row["target_audience"],
        landing_page_url=row["landing_page_url"],
        cta=row["cta"],
        campaign_owner=row["campaign_owner"],
        launch_date=(
            date.fromisoformat(row["launch_date"]) if row["launch_date"] else None
        ),
        destination_url=row["destination_url"] or None,
        utm_source=row["utm_source"] or None,
        utm_medium=row["utm_medium"] or None,
        utm_campaign=row["utm_campaign"] or None,
        budget=float(row["budget"]) if row["budget"] else None,
        campaign_message=row["campaign_message"] or None,
    )


ROWS = _load_rows()


def _rows_for_tier(tier: str) -> list[dict[str, str]]:
    return [row for row in ROWS if row["quality_tier"] == tier]


class TestDatasetLoads:
    def test_dataset_has_35_campaigns(self) -> None:
        assert len(ROWS) == 35

    def test_every_row_has_a_recognised_quality_tier(self) -> None:
        valid_tiers = {"excellent", "pass_ready", "warning", "critical"}
        assert all(row["quality_tier"] in valid_tiers for row in ROWS)


class TestPipelineExecutesForEveryRow:
    def test_every_sample_row_executes_without_error(self) -> None:
        for row in ROWS:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            assert qa_result is not None

    def test_score_always_between_0_and_100(self) -> None:
        for row in ROWS:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            assert 0 <= qa_result.score <= 100

    def test_denominator_remains_100_for_every_row(self) -> None:
        for row in ROWS:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            total_available = sum(
                r.points_available for r in qa_result.validation_results
            )
            assert total_available == 100


class TestExcellentAndPassReadyCampaignsPass:
    @pytest.mark.parametrize("tier", ["excellent", "pass_ready"])
    def test_tier_produces_pass(self, tier: str) -> None:
        rows = _rows_for_tier(tier)
        assert rows, f"expected at least one '{tier}' row"
        for row in rows:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            assert qa_result.status == QAStatus.PASS, row["campaign_name"]
            assert qa_result.critical_failures == []


class TestWarningCampaignsReview:
    def test_warning_tier_produces_review_with_no_critical_failures(self) -> None:
        rows = _rows_for_tier("warning")
        assert rows, "expected at least one 'warning' row"
        for row in rows:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            assert qa_result.status == QAStatus.REVIEW, row["campaign_name"]
            assert qa_result.critical_failures == []
            assert qa_result.warnings != []


class TestCriticalCampaigns:
    def test_critical_tier_never_passes_and_has_a_critical_failure(self) -> None:
        rows = _rows_for_tier("critical")
        assert rows, "expected at least one 'critical' row"
        for row in rows:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            assert qa_result.status != QAStatus.PASS, row["campaign_name"]
            assert qa_result.critical_failures != []

    def test_severe_critical_campaigns_produce_fail(self) -> None:
        """At least one 'critical' row must be broken badly enough to
        cross into FAIL (score < 70) — not every critical failure should
        only ever produce REVIEW."""
        fail_statuses = [
            score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            ).status
            for row in _rows_for_tier("critical")
        ]
        assert QAStatus.FAIL in fail_statuses


class TestPaidVsNonPaidRuleApplicability:
    def test_paid_campaigns_evaluate_paid_only_rules(self) -> None:
        """For paid campaigns, paid-only rules must be genuinely
        evaluated (PASS, WARNING, or FAIL) — never NOT_APPLICABLE."""
        paid_rows = [r for r in ROWS if r["campaign_type"] in PAID_CAMPAIGN_TYPES]
        assert paid_rows, "expected at least one paid campaign row"

        for row in paid_rows:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            for result in qa_result.validation_results:
                if result.rule_id in PAID_ONLY_RULE_IDS:
                    assert result.status != ValidationStatus.NOT_APPLICABLE, (
                        row["campaign_name"],
                        result.rule_id,
                    )

    def test_non_paid_campaigns_report_paid_only_rules_not_applicable(self) -> None:
        """For non-paid campaigns that didn't supply the optional paid
        fields, the paid-only rules must be NOT_APPLICABLE, never PASS —
        they were never evaluated, not satisfied."""
        non_paid_rows = [
            r
            for r in ROWS
            if r["campaign_type"] not in PAID_CAMPAIGN_TYPES
            and not r["utm_source"]
            and not r["utm_medium"]
            and not r["utm_campaign"]
            and not r["destination_url"]
            and not r["budget"]
        ]
        assert non_paid_rows, "expected at least one fully non-paid campaign row"

        for row in non_paid_rows:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            for result in qa_result.validation_results:
                if result.rule_id in PAID_ONLY_RULE_IDS:
                    assert result.status == ValidationStatus.NOT_APPLICABLE, (
                        row["campaign_name"],
                        result.rule_id,
                    )


class TestQAResultHelperProperties:
    def test_helper_properties_partition_validation_results(self) -> None:
        """passed_checks, warnings, failed_checks, and
        not_applicable_checks must partition validation_results exactly —
        no overlaps, full coverage — for every sample row."""
        for row in ROWS:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            buckets = [
                qa_result.passed_checks,
                qa_result.warnings,
                qa_result.failed_checks,
                qa_result.not_applicable_checks,
            ]
            total_bucketed = sum(len(bucket) for bucket in buckets)
            assert total_bucketed == len(qa_result.validation_results), row[
                "campaign_name"
            ]

    def test_critical_failures_is_subset_of_failed_checks(self) -> None:
        for row in ROWS:
            qa_result = score_campaign(
                _row_to_campaign(row), reference_date=REFERENCE_DATE
            )
            failed_ids = {r.rule_id for r in qa_result.failed_checks}
            critical_ids = {r.rule_id for r in qa_result.critical_failures}
            assert critical_ids <= failed_ids, row["campaign_name"]
