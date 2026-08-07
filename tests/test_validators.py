"""Tests for src.validators.

Covers each validator function's rules plus the validate_campaign
orchestration function. All launch-date-dependent tests use a fixed
reference date so results remain deterministic. Scoring/aggregation logic
does not exist yet and is not tested here.
"""

from datetime import date, timedelta

from src.constants import RULE_POINTS
from src.models import CampaignSubmission, ValidationSeverity, ValidationStatus
from src.validators import (
    normalize_campaign_name,
    validate_campaign,
    validate_campaign_naming,
    validate_cta,
    validate_destination_url,
    validate_landing_page_url,
    validate_launch_readiness,
    validate_required_fields,
    validate_utms,
)

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


def result_for(results, rule_id: str):
    matches = [r for r in results if r.rule_id == rule_id]
    assert len(matches) == 1, f"expected exactly one result for '{rule_id}'"
    return matches[0]


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


class TestRequiredFields:
    def test_valid_required_fields_pass(self) -> None:
        results = validate_required_fields(make_campaign())

        assert all(r.status == ValidationStatus.PASS for r in results)
        assert all(r.severity == ValidationSeverity.INFO for r in results)

    def test_blank_campaign_name(self) -> None:
        results = validate_required_fields(make_campaign(campaign_name=""))

        result = result_for(results, "required_campaign_name")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL
        assert result.points_earned == 0

    def test_whitespace_only_owner(self) -> None:
        results = validate_required_fields(make_campaign(campaign_owner="   "))

        result = result_for(results, "required_campaign_owner")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_cta(self) -> None:
        results = validate_required_fields(make_campaign(cta=""))

        result = result_for(results, "required_cta")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------


class TestUrls:
    def test_valid_https_landing_page(self) -> None:
        results = validate_landing_page_url(
            make_campaign(landing_page_url="https://example.com/demo")
        )

        assert result_for(results, "landing_url_format").status == ValidationStatus.PASS
        assert result_for(results, "landing_url_https").status == ValidationStatus.PASS

    def test_http_landing_page_warning(self) -> None:
        results = validate_landing_page_url(
            make_campaign(landing_page_url="http://example.com/demo")
        )

        assert result_for(results, "landing_url_format").status == ValidationStatus.PASS
        https_result = result_for(results, "landing_url_https")
        assert https_result.status == ValidationStatus.WARNING
        assert https_result.severity == ValidationSeverity.WARNING

    def test_malformed_landing_page(self) -> None:
        results = validate_landing_page_url(
            make_campaign(landing_page_url="not-a-url")
        )

        result = result_for(results, "landing_url_format")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_paid_destination_url(self) -> None:
        results = validate_destination_url(
            make_campaign(destination_url=None, campaign_type="Paid Search")
        )

        result = result_for(results, "destination_url_required")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_malformed_supplied_destination_url(self) -> None:
        results = validate_destination_url(
            make_campaign(destination_url="not-a-url")
        )

        result = result_for(results, "destination_url_format")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL


# ---------------------------------------------------------------------------
# UTMs
# ---------------------------------------------------------------------------


class TestUtms:
    def test_valid_paid_utms(self) -> None:
        results = validate_utms(make_campaign())

        for field in ("utm_source", "utm_medium", "utm_campaign"):
            assert result_for(results, f"{field}_required").status == ValidationStatus.PASS
            assert result_for(results, f"{field}_format").status == ValidationStatus.PASS

    def test_missing_paid_utm_source(self) -> None:
        results = validate_utms(make_campaign(utm_source=None))

        result = result_for(results, "utm_source_required")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_paid_utm_medium(self) -> None:
        results = validate_utms(make_campaign(utm_medium=None))

        result = result_for(results, "utm_medium_required")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_paid_utm_campaign(self) -> None:
        results = validate_utms(make_campaign(utm_campaign=None))

        result = result_for(results, "utm_campaign_required")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_uppercase_utm_warning(self) -> None:
        results = validate_utms(make_campaign(utm_source="Google"))

        result = result_for(results, "utm_source_format")
        assert result.status == ValidationStatus.WARNING

    def test_spaces_in_utm_warning(self) -> None:
        results = validate_utms(make_campaign(utm_medium="cost per click"))

        result = result_for(results, "utm_medium_format")
        assert result.status == ValidationStatus.WARNING

    def test_utm_campaign_alignment_success(self) -> None:
        results = validate_utms(
            make_campaign(
                campaign_name="uk_enterprise_demo_q3_2026",
                utm_campaign="uk_enterprise_demo_q3_2026",
            )
        )

        result = result_for(results, "utm_campaign_alignment")
        assert result.status == ValidationStatus.PASS

    def test_utm_campaign_mismatch_warning(self) -> None:
        results = validate_utms(
            make_campaign(
                campaign_name="uk_enterprise_demo_q3_2026",
                utm_campaign="something_else",
            )
        )

        result = result_for(results, "utm_campaign_alignment")
        assert result.status == ValidationStatus.WARNING

    def test_non_paid_required_utm_rules_are_not_applicable(self) -> None:
        results = validate_utms(
            make_campaign(
                campaign_type="Email",
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
            )
        )

        for field in ("utm_source", "utm_medium", "utm_campaign"):
            required_result = result_for(results, f"{field}_required")
            assert required_result.status == ValidationStatus.NOT_APPLICABLE
            assert required_result.points_earned == required_result.points_available

    def test_non_paid_required_utm_rule_not_applicable_even_when_supplied(
        self,
    ) -> None:
        """The 'required' concept never applies to non-paid campaigns, so
        it must be NOT_APPLICABLE even if a value happens to be supplied
        — supplying an optional field doesn't retroactively make it
        required."""
        results = validate_utms(
            make_campaign(campaign_type="Email", utm_source="facebook")
        )

        result = result_for(results, "utm_source_required")
        assert result.status == ValidationStatus.NOT_APPLICABLE

    def test_non_paid_supplied_malformed_utm_still_produces_warning(self) -> None:
        """Once an optional UTM is supplied on a non-paid campaign, its
        format must still be validated — NOT_APPLICABLE only applies to
        the requirement, never to a value that was actually given."""
        results = validate_utms(
            make_campaign(campaign_type="Email", utm_source="FACEBOOK")
        )

        required_result = result_for(results, "utm_source_required")
        format_result = result_for(results, "utm_source_format")
        assert required_result.status == ValidationStatus.NOT_APPLICABLE
        assert format_result.status == ValidationStatus.WARNING

    def test_non_paid_absent_optional_utm_format_is_not_applicable(self) -> None:
        results = validate_utms(
            make_campaign(campaign_type="Email", utm_source=None)
        )

        result = result_for(results, "utm_source_format")
        assert result.status == ValidationStatus.NOT_APPLICABLE
        assert result.points_earned == result.points_available

    def test_destination_url_contains_all_utm_params(self) -> None:
        results = validate_utms(
            make_campaign(
                destination_url=(
                    "https://example.com/demo?utm_source=google"
                    "&utm_medium=cpc&utm_campaign=uk_enterprise_demo_q3_2026"
                )
            )
        )

        result = result_for(results, "destination_url_utms")
        assert result.status == ValidationStatus.PASS

    def test_paid_destination_url_missing_one_utm_query_param(self) -> None:
        results = validate_utms(
            make_campaign(
                destination_url="https://example.com/demo?utm_source=google&utm_medium=cpc"
            )
        )

        result = result_for(results, "destination_url_utms")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL
        assert "utm_campaign" in result.message

    def test_query_parsing_not_substring_matching(self) -> None:
        """A key that merely *contains* 'utm_source' must not satisfy the
        utm_source requirement — only an actual utm_source query key does.
        """
        results = validate_utms(
            make_campaign(
                destination_url=(
                    "https://example.com/demo?other_utm_source_extra=1"
                    "&utm_medium=cpc&utm_campaign=uk_enterprise_demo_q3_2026"
                )
            )
        )

        result = result_for(results, "destination_url_utms")
        assert result.status == ValidationStatus.FAIL
        assert "utm_source" in result.message


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


class TestNaming:
    def test_compliant_name(self) -> None:
        results = validate_campaign_naming(
            make_campaign(campaign_name="uk_enterprise_demo_q3_2026")
        )

        assert all(r.status == ValidationStatus.PASS for r in results)

    def test_uppercase_warning(self) -> None:
        results = validate_campaign_naming(
            make_campaign(campaign_name="UK_Enterprise_Demo_Q3_2026")
        )

        result = result_for(results, "campaign_name_lowercase")
        assert result.status == ValidationStatus.WARNING

    def test_spaces_warning(self) -> None:
        results = validate_campaign_naming(
            make_campaign(campaign_name="uk enterprise demo q3 2026")
        )

        result = result_for(results, "campaign_name_no_spaces")
        assert result.status == ValidationStatus.WARNING

    def test_consecutive_underscores_warning(self) -> None:
        results = validate_campaign_naming(
            make_campaign(campaign_name="uk__enterprise_demo_q3_2026")
        )

        result = result_for(results, "campaign_name_consecutive_underscores")
        assert result.status == ValidationStatus.WARNING

    def test_leading_trailing_underscore_warning(self) -> None:
        results = validate_campaign_naming(
            make_campaign(campaign_name="_uk_enterprise_demo_q3_2026_")
        )

        result = result_for(results, "campaign_name_underscore_placement")
        assert result.status == ValidationStatus.WARNING

    def test_invalid_characters_warning(self) -> None:
        results = validate_campaign_naming(
            make_campaign(campaign_name="uk-enterprise-demo!q3.2026")
        )

        result = result_for(results, "campaign_name_characters")
        assert result.status == ValidationStatus.WARNING

    def test_normalize_campaign_name(self) -> None:
        assert (
            normalize_campaign_name("UK Enterprise Demo Q3 2026")
            == "uk_enterprise_demo_q3_2026"
        )
        assert normalize_campaign_name("  Multi   Space  ") == "multi_space"
        assert normalize_campaign_name("_leading_trailing_") == "leading_trailing"


# ---------------------------------------------------------------------------
# Launch readiness
# ---------------------------------------------------------------------------


class TestLaunchReadiness:
    def test_past_date(self) -> None:
        results = validate_launch_readiness(
            make_campaign(launch_date=REFERENCE_DATE - timedelta(days=1)),
            REFERENCE_DATE,
        )

        result = result_for(results, "launch_date_timing")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_today(self) -> None:
        results = validate_launch_readiness(
            make_campaign(launch_date=REFERENCE_DATE), REFERENCE_DATE
        )

        result = result_for(results, "launch_date_timing")
        assert result.status == ValidationStatus.WARNING

    def test_tomorrow(self) -> None:
        results = validate_launch_readiness(
            make_campaign(launch_date=REFERENCE_DATE + timedelta(days=1)),
            REFERENCE_DATE,
        )

        result = result_for(results, "launch_date_timing")
        assert result.status == ValidationStatus.WARNING

    def test_two_days_away(self) -> None:
        results = validate_launch_readiness(
            make_campaign(launch_date=REFERENCE_DATE + timedelta(days=2)),
            REFERENCE_DATE,
        )

        result = result_for(results, "launch_date_timing")
        assert result.status == ValidationStatus.PASS

    def test_valid_paid_budget(self) -> None:
        results = validate_launch_readiness(
            make_campaign(budget=1000.0), REFERENCE_DATE
        )

        result = result_for(results, "paid_budget")
        assert result.status == ValidationStatus.PASS

    def test_zero_paid_budget(self) -> None:
        results = validate_launch_readiness(
            make_campaign(budget=0), REFERENCE_DATE
        )

        result = result_for(results, "paid_budget")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_paid_budget(self) -> None:
        results = validate_launch_readiness(
            make_campaign(budget=None), REFERENCE_DATE
        )

        result = result_for(results, "paid_budget")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_non_paid_budget_accepted(self) -> None:
        results = validate_launch_readiness(
            make_campaign(
                campaign_type="Email",
                budget=None,
                destination_url=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
            ),
            REFERENCE_DATE,
        )

        result = result_for(results, "paid_budget")
        assert result.status == ValidationStatus.NOT_APPLICABLE
        assert result.points_earned == result.points_available

    def test_non_paid_budget_is_not_applicable_not_pass(self) -> None:
        """A non-paid budget must be reported as NOT_APPLICABLE, never as
        a PASS, so audit/UI output never implies the requirement was
        evaluated and satisfied."""
        results = validate_launch_readiness(
            make_campaign(campaign_type="Email", budget=None), REFERENCE_DATE
        )

        result = result_for(results, "paid_budget")
        assert result.status != ValidationStatus.PASS
        assert result.status == ValidationStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# CTA
# ---------------------------------------------------------------------------


class TestCta:
    def test_normal_cta(self) -> None:
        results = validate_cta(make_campaign(cta="Book a demo"))

        result = result_for(results, "cta_length")
        assert result.status == ValidationStatus.PASS

    def test_long_cta_warning(self) -> None:
        results = validate_cta(make_campaign(cta="x" * 61))

        result = result_for(results, "cta_length")
        assert result.status == ValidationStatus.WARNING

    def test_blank_cta(self) -> None:
        results = validate_cta(make_campaign(cta=""))

        result = result_for(results, "cta_length")
        assert result.status == ValidationStatus.PASS
        assert result.points_earned == result.points_available


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


class TestValidateCampaign:
    def test_returns_all_applicable_results(self) -> None:
        results = validate_campaign(make_campaign(), reference_date=REFERENCE_DATE)

        rule_ids = {r.rule_id for r in results}
        assert rule_ids == set(RULE_POINTS.keys())

    def test_points_available_always_sums_to_100(self) -> None:
        paid_results = validate_campaign(
            make_campaign(), reference_date=REFERENCE_DATE
        )
        non_paid_results = validate_campaign(
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
        blank_paid_results = validate_campaign(
            make_campaign(
                campaign_name="",
                landing_page_url="",
                destination_url=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                budget=None,
                cta="",
            ),
            reference_date=REFERENCE_DATE,
        )

        assert sum(r.points_available for r in paid_results) == 100
        assert sum(r.points_available for r in non_paid_results) == 100
        assert sum(r.points_available for r in blank_paid_results) == 100

    def test_paid_rules_are_included_for_paid_campaigns(self) -> None:
        results = validate_campaign(
            make_campaign(utm_source=None), reference_date=REFERENCE_DATE
        )

        result = result_for(results, "utm_source_required")
        assert result.status == ValidationStatus.FAIL
        assert result.severity == ValidationSeverity.CRITICAL

    def test_paid_only_critical_requirements_not_applied_to_non_paid(self) -> None:
        results = validate_campaign(
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

        paid_only_rule_ids = {
            "utm_source_required",
            "utm_medium_required",
            "utm_campaign_required",
            "destination_url_required",
            "destination_url_utms",
            "paid_budget",
        }
        critical_fail_rule_ids = {
            r.rule_id
            for r in results
            if r.status == ValidationStatus.FAIL
            and r.severity == ValidationSeverity.CRITICAL
        }

        assert critical_fail_rule_ids.isdisjoint(paid_only_rule_ids)

    def test_no_critical_failures_for_fully_compliant_paid_campaign(self) -> None:
        results = validate_campaign(make_campaign(), reference_date=REFERENCE_DATE)

        critical_failures = [
            r
            for r in results
            if r.status == ValidationStatus.FAIL
            and r.severity == ValidationSeverity.CRITICAL
        ]
        assert critical_failures == []

    def test_existing_paid_campaign_behaviour_is_unchanged(self) -> None:
        """A fully compliant paid campaign should still score every
        applicable rule as PASS — none of these become NOT_APPLICABLE,
        since every rule genuinely applies to a paid campaign."""
        results = validate_campaign(make_campaign(), reference_date=REFERENCE_DATE)

        not_applicable = [
            r for r in results if r.status == ValidationStatus.NOT_APPLICABLE
        ]
        assert not_applicable == []
        assert sum(r.points_earned for r in results) == 100

    def test_valid_non_paid_campaign_can_still_earn_100_points(self) -> None:
        results = validate_campaign(
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

        assert sum(r.points_available for r in results) == 100
        assert sum(r.points_earned for r in results) == 100

        critical_failures = [
            r
            for r in results
            if r.status == ValidationStatus.FAIL
            and r.severity == ValidationSeverity.CRITICAL
        ]
        assert critical_failures == []

    def test_non_paid_campaign_reports_not_applicable_for_paid_only_rules(
        self,
    ) -> None:
        """The six paid-only rules must show as NOT_APPLICABLE (not PASS)
        for a non-paid campaign, so future UI/audit output never implies
        a non-paid campaign 'passed' a requirement it was never subject
        to."""
        results = validate_campaign(
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

        paid_only_rule_ids = {
            "utm_source_required",
            "utm_medium_required",
            "utm_campaign_required",
            "destination_url_required",
            "destination_url_utms",
            "paid_budget",
        }
        for rule_id in paid_only_rule_ids:
            result = result_for(results, rule_id)
            assert result.status == ValidationStatus.NOT_APPLICABLE
            assert result.points_earned == result.points_available
