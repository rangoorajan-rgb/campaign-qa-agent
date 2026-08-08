"""Tests for src.gemini_analyzer.

No test makes a real network request or requires a GEMINI_API_KEY: the
Gemini client is always a fake object injected via analyze_campaign()'s
`client` parameter, exercising exactly the same code path production
code uses (client.models.generate_content(...).text) without touching
the network.
"""

import json
from datetime import date, timedelta

import pytest

import config
from src.gemini_analyzer import _build_prompt, analyze_campaign
from src.models import CampaignSubmission, GeminiConcernSeverity, GeminiReviewStatus
from src.scoring import score_campaign

REFERENCE_DATE = date(2026, 8, 8)


def make_campaign(**overrides: object) -> CampaignSubmission:
    defaults: dict[str, object] = dict(
        campaign_name="uk_enterprise_demo_q3_2026",
        campaign_type="Paid Search",
        channel="Google Ads",
        objective="Demo Signups",
        target_audience="UK Enterprise",
        landing_page_url="https://acme.io/demo",
        cta="Book a Demo",
        campaign_owner="Sarah Chen",
        launch_date=REFERENCE_DATE + timedelta(days=14),
        destination_url=(
            "https://acme.io/demo?utm_source=google&utm_medium=cpc"
            "&utm_campaign=uk_enterprise_demo_q3_2026"
        ),
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="uk_enterprise_demo_q3_2026",
        budget=15000.0,
        campaign_message="Enterprise Q3 demo push for UK named accounts.",
    )
    defaults.update(overrides)
    return CampaignSubmission(**defaults)  # type: ignore[arg-type]


def make_qa_result(**campaign_overrides: object):
    return score_campaign(
        make_campaign(**campaign_overrides), reference_date=REFERENCE_DATE
    )


_VALID_PAYLOAD = {
    "summary": "The campaign is well targeted but the CTA is generic.",
    "concerns": [
        {
            "title": "Generic CTA",
            "explanation": "The CTA does not reflect the enterprise objective.",
            "severity": "MEDIUM",
        }
    ],
    "strengths": ["Clear audience targeting", "Coherent channel choice"],
    "recommendation": "Tighten the CTA to reference the specific offer.",
}


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, response: _FakeResponse | None = None, exception: Exception | None = None):
        self._response = response
        self._exception = exception
        self.calls: list[dict[str, object]] = []

    def generate_content(self, *, model, contents, config):  # noqa: A002 - matches SDK signature
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self._exception is not None:
            raise self._exception
        assert self._response is not None
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse | None = None, exception: Exception | None = None):
        self.models = _FakeModels(response=response, exception=exception)


# ---------------------------------------------------------------------------
# Successful structured response
# ---------------------------------------------------------------------------


class TestSuccessfulReview:
    def test_ok_status_and_summary(self) -> None:
        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))
        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.status == GeminiReviewStatus.OK
        assert result.error_message is None
        assert result.review is not None
        assert result.review.summary == _VALID_PAYLOAD["summary"]

    def test_concerns_parse_correctly(self) -> None:
        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))
        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.review is not None
        assert len(result.review.concerns) == 1
        concern = result.review.concerns[0]
        assert concern.title == "Generic CTA"
        assert concern.explanation == (
            "The CTA does not reflect the enterprise objective."
        )
        assert concern.severity == GeminiConcernSeverity.MEDIUM

    def test_strengths_parse_correctly(self) -> None:
        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))
        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.review is not None
        assert result.review.strengths == [
            "Clear audience targeting",
            "Coherent channel choice",
        ]

    def test_recommendation_parses_correctly(self) -> None:
        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))
        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.review is not None
        assert result.review.recommendation == _VALID_PAYLOAD["recommendation"]

    def test_uses_configured_model_not_hardcoded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-test-model")
        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))

        analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert client.models.calls[0]["model"] == "gemini-test-model"


# ---------------------------------------------------------------------------
# Prompt content
# ---------------------------------------------------------------------------


class TestPromptContent:
    def test_prompt_contains_relevant_campaign_fields(self) -> None:
        campaign = make_campaign()
        prompt = _build_prompt(campaign, make_qa_result())

        assert campaign.campaign_name in prompt
        assert campaign.campaign_type in prompt
        assert campaign.channel in prompt
        assert campaign.objective in prompt
        assert campaign.target_audience in prompt
        assert campaign.cta in prompt
        assert campaign.campaign_message in prompt
        assert campaign.campaign_owner in prompt
        assert str(campaign.launch_date) in prompt

    def test_prompt_contains_deterministic_qa_context(self) -> None:
        qa_result = make_qa_result()
        prompt = _build_prompt(make_campaign(), qa_result)

        assert str(qa_result.score) in prompt
        assert qa_result.status.value in prompt
        assert "already flagged" in prompt

    def test_prompt_includes_critical_failure_details_when_present(self) -> None:
        qa_result = make_qa_result(campaign_owner="")  # forces a critical failure
        prompt = _build_prompt(make_campaign(campaign_owner=""), qa_result)

        assert qa_result.critical_failures  # sanity check on the fixture
        failing_rule = qa_result.critical_failures[0]
        assert failing_rule.rule_id in prompt
        assert failing_rule.message in prompt

    def test_prompt_prohibits_score_and_verdict_generation(self) -> None:
        prompt = _build_prompt(make_campaign(), make_qa_result())

        assert "Do NOT produce a numeric score" in prompt
        assert "Do NOT produce a PASS, REVIEW, or FAIL verdict" in prompt

    def test_prompt_frames_qa_result_as_context_only(self) -> None:
        prompt = _build_prompt(make_campaign(), make_qa_result())

        assert "CONTEXT ONLY" in prompt


# ---------------------------------------------------------------------------
# NOT_CONFIGURED
# ---------------------------------------------------------------------------


class TestNotConfigured:
    def test_not_configured_when_no_key_and_no_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(config, "GEMINI_API_KEY", "")

        result = analyze_campaign(make_campaign(), make_qa_result())

        assert result.status == GeminiReviewStatus.NOT_CONFIGURED
        assert result.review is None
        assert result.error_message is None

    def test_injected_client_bypasses_not_configured_even_without_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(config, "GEMINI_API_KEY", "")
        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))

        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.status == GeminiReviewStatus.OK


# ---------------------------------------------------------------------------
# ERROR paths
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_error_on_api_failure(self) -> None:
        client = _FakeClient(exception=RuntimeError("connection reset by peer"))

        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.status == GeminiReviewStatus.ERROR
        assert result.review is None
        assert result.error_message is not None
        assert "connection reset by peer" not in result.error_message

    def test_error_on_malformed_json(self) -> None:
        client = _FakeClient(response=_FakeResponse("not valid json at all"))

        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.status == GeminiReviewStatus.ERROR
        assert result.review is None

    def test_error_on_response_missing_required_fields(self) -> None:
        incomplete_payload = {"summary": "Looks fine."}
        client = _FakeClient(response=_FakeResponse(json.dumps(incomplete_payload)))

        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.status == GeminiReviewStatus.ERROR

    def test_error_on_invalid_severity_value(self) -> None:
        payload = dict(_VALID_PAYLOAD)
        payload["concerns"] = [
            {"title": "X", "explanation": "Y", "severity": "NOT_A_REAL_SEVERITY"}
        ]
        client = _FakeClient(response=_FakeResponse(json.dumps(payload)))

        result = analyze_campaign(make_campaign(), make_qa_result(), client=client)

        assert result.status == GeminiReviewStatus.ERROR

    def test_raw_exceptions_are_never_propagated(self) -> None:
        """An arbitrary/unexpected exception type raised by the client
        must never escape analyze_campaign() — it must always return a
        GeminiReviewResult, never raise.

        Deliberately not KeyboardInterrupt/SystemExit: those are
        BaseException, not Exception, and analyze_campaign() correctly
        lets them propagate rather than silently swallowing a user's
        interrupt — this test is about ordinary unexpected failures.
        """

        class _UnexpectedSdkError(Exception):
            pass

        client = _FakeClient(exception=_UnexpectedSdkError("unexpected internal state"))

        try:
            result = analyze_campaign(make_campaign(), make_qa_result(), client=client)
        except Exception as exc:  # pragma: no cover - failure path
            pytest.fail(f"analyze_campaign() raised {exc!r} instead of returning ERROR")

        assert result.status == GeminiReviewStatus.ERROR


# ---------------------------------------------------------------------------
# Deterministic QAResult is never mutated
# ---------------------------------------------------------------------------


class TestDeterministicResultUntouched:
    def test_qa_result_unchanged_after_successful_review(self) -> None:
        qa_result = make_qa_result()
        original_score = qa_result.score
        original_status = qa_result.status
        original_results = list(qa_result.validation_results)

        client = _FakeClient(response=_FakeResponse(json.dumps(_VALID_PAYLOAD)))
        analyze_campaign(make_campaign(), qa_result, client=client)

        assert qa_result.score == original_score
        assert qa_result.status == original_status
        assert qa_result.validation_results == original_results

    def test_qa_result_unchanged_after_failed_review(self) -> None:
        qa_result = make_qa_result()
        original_score = qa_result.score
        original_status = qa_result.status
        original_results = list(qa_result.validation_results)

        client = _FakeClient(exception=RuntimeError("boom"))
        analyze_campaign(make_campaign(), qa_result, client=client)

        assert qa_result.score == original_score
        assert qa_result.status == original_status
        assert qa_result.validation_results == original_results
