"""Tests for src.webhook.

No test makes a real network request or requires MAKE_WEBHOOK_URL to be
set: the HTTP client is always a fake object injected via
send_to_make()'s `client` parameter, exercising exactly the same code
path production code uses (client.post(...).status_code) without
touching the network. Retry-delay sleeps are patched out so this suite
stays fast despite exercising the real ~1s retry delay logic.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import requests

import config
from src.models import (
    CampaignSubmission,
    GeminiConcern,
    GeminiConcernSeverity,
    GeminiReview,
    GeminiReviewResult,
    GeminiReviewStatus,
    WebhookDeliveryStatus,
)
from src.scoring import score_campaign
from src.webhook import send_to_make

REFERENCE_DATE = date(2026, 8, 8)
FAKE_WEBHOOK_URL = "https://hook.make.com/test-scenario-token"


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


def make_gemini_ok_result() -> GeminiReviewResult:
    return GeminiReviewResult(
        status=GeminiReviewStatus.OK,
        review=GeminiReview(
            summary="Solid campaign overall.",
            concerns=[
                GeminiConcern(
                    title="Generic CTA",
                    explanation="The CTA does not reflect the enterprise objective.",
                    severity=GeminiConcernSeverity.MEDIUM,
                )
            ],
            strengths=["Clear audience targeting"],
            recommendation="Tighten the CTA to reference the specific offer.",
        ),
    )


def make_gemini_not_configured_result() -> GeminiReviewResult:
    return GeminiReviewResult(status=GeminiReviewStatus.NOT_CONFIGURED)


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeClient:
    """Each entry in `results` is consumed by one `.post()` call, in
    order: an Exception instance is raised, anything else is returned."""

    def __init__(self, *results: object) -> None:
        self._results = list(results)
        self.calls: list[dict[str, object]] = []

    def post(self, url, *, json, timeout):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch out the retry delay so tests exercising retries stay fast."""
    monkeypatch.setattr("src.webhook.time.sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def _fake_webhook_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most tests inject a client directly and don't need a real URL, but
    give them a realistic one anyway so payload/call assertions are
    meaningful; NOT_CONFIGURED tests override this explicitly."""
    monkeypatch.setattr(config, "MAKE_WEBHOOK_URL", FAKE_WEBHOOK_URL)


# ---------------------------------------------------------------------------
# Successful delivery
# ---------------------------------------------------------------------------


class TestSuccessfulDelivery:
    def test_sent_status_on_2xx(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        result = send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert result.status == WebhookDeliveryStatus.SENT
        assert result.http_status_code == 200
        assert result.error_message is None

    def test_exact_payload_top_level_structure(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        payload = client.calls[0]["json"]
        assert set(payload.keys()) == {
            "event",
            "event_id",
            "sent_at",
            "campaign",
            "qa_result",
            "ai_review",
        }

    def test_event_name(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        payload = client.calls[0]["json"]
        assert payload["event"] == "campaign.qa.completed"

    def test_campaign_fields(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        campaign_payload = client.calls[0]["json"]["campaign"]
        assert campaign_payload == {
            "campaign_name": "uk_enterprise_demo_q3_2026",
            "campaign_type": "Paid Search",
            "channel": "Google Ads",
            "objective": "Demo Signups",
            "target_audience": "UK Enterprise",
            "campaign_owner": "Sarah Chen",
            "cta": "Book a Demo",
            "launch_date": (REFERENCE_DATE + timedelta(days=14)).isoformat(),
            "landing_page_url": "https://acme.io/demo",
            "destination_url": (
                "https://acme.io/demo?utm_source=google&utm_medium=cpc"
                "&utm_campaign=uk_enterprise_demo_q3_2026"
            ),
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "uk_enterprise_demo_q3_2026",
        }

    def test_deterministic_qa_block(self) -> None:
        qa_result = make_qa_result()
        client = _FakeClient(_FakeResponse(200))
        send_to_make(qa_result, make_gemini_ok_result(), client=client)

        qa_payload = client.calls[0]["json"]["qa_result"]
        assert qa_payload["score"] == qa_result.score
        assert qa_payload["status"] == qa_result.status.value
        assert qa_payload["critical_failure_count"] == len(qa_result.critical_failures)
        assert qa_payload["warning_count"] == len(qa_result.warnings)
        assert qa_payload["critical_failures"] == []
        assert qa_payload["warnings"] == []
        assert qa_payload["category_breakdown"]["TRACKING_UTMS"] == {
            "earned": 30.0,
            "available": 30.0,
        }

    def test_critical_failures_and_warnings_are_summarised(self) -> None:
        qa_result = make_qa_result(campaign_owner="")  # forces a critical failure
        client = _FakeClient(_FakeResponse(200))
        send_to_make(qa_result, make_gemini_ok_result(), client=client)

        qa_payload = client.calls[0]["json"]["qa_result"]
        assert qa_payload["critical_failure_count"] == 1
        assert qa_payload["critical_failures"] == [
            {
                "rule_id": "required_campaign_owner",
                "category": "REQUIRED_INFORMATION",
                "message": "Campaign owner is missing.",
            }
        ]

    def test_full_gemini_concerns_array(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        ai_payload = client.calls[0]["json"]["ai_review"]
        assert ai_payload["status"] == "OK"
        assert ai_payload["summary"] == "Solid campaign overall."
        assert ai_payload["concerns"] == [
            {
                "title": "Generic CTA",
                "severity": "MEDIUM",
                "explanation": "The CTA does not reflect the enterprise objective.",
            }
        ]
        assert ai_payload["recommendation"] == (
            "Tighten the CTA to reference the specific offer."
        )

    def test_ai_review_omits_qualitative_fields_when_not_configured(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(
            make_qa_result(), make_gemini_not_configured_result(), client=client
        )

        ai_payload = client.calls[0]["json"]["ai_review"]
        assert ai_payload == {"status": "NOT_CONFIGURED"}

    def test_excluded_fields_are_absent(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        payload = client.calls[0]["json"]
        campaign_payload = payload["campaign"]
        ai_payload = payload["ai_review"]

        assert "budget" not in campaign_payload
        assert "campaign_message" not in campaign_payload
        assert "strengths" not in ai_payload

        payload_text = str(payload)
        assert "GEMINI_API_KEY" not in payload_text
        assert config.MAKE_WEBHOOK_URL not in payload_text
        assert "Traceback" not in payload_text


# ---------------------------------------------------------------------------
# NOT_CONFIGURED
# ---------------------------------------------------------------------------


class TestNotConfigured:
    def test_not_configured_when_no_url_and_no_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(config, "MAKE_WEBHOOK_URL", "")

        result = send_to_make(make_qa_result(), make_gemini_ok_result())

        assert result.status == WebhookDeliveryStatus.NOT_CONFIGURED
        assert result.http_status_code is None
        assert result.error_message is None

    def test_injected_client_bypasses_not_configured_even_without_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(config, "MAKE_WEBHOOK_URL", "")
        client = _FakeClient(_FakeResponse(200))

        result = send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert result.status == WebhookDeliveryStatus.SENT
        assert len(client.calls) == 1


# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------


class TestRetries:
    def test_retry_then_success_after_connection_error(self) -> None:
        client = _FakeClient(
            requests.exceptions.ConnectionError("connection refused"),
            _FakeResponse(200),
        )

        result = send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert result.status == WebhookDeliveryStatus.SENT
        assert len(client.calls) == 2

    def test_retry_then_success_after_5xx(self) -> None:
        client = _FakeClient(_FakeResponse(503), _FakeResponse(200))

        result = send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert result.status == WebhookDeliveryStatus.SENT
        assert len(client.calls) == 2

    def test_both_attempts_fail_returns_error(self) -> None:
        client = _FakeClient(
            requests.exceptions.Timeout("timed out"),
            requests.exceptions.Timeout("timed out"),
        )

        result = send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert result.status == WebhookDeliveryStatus.ERROR
        assert result.error_message is not None
        assert len(client.calls) == 2

    def test_4xx_performs_exactly_one_attempt(self) -> None:
        client = _FakeClient(_FakeResponse(422))

        result = send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert result.status == WebhookDeliveryStatus.ERROR
        assert result.http_status_code == 422
        assert len(client.calls) == 1


# ---------------------------------------------------------------------------
# event_id and sent_at
# ---------------------------------------------------------------------------


class TestEventIdAndTimestamp:
    def test_event_id_is_valid_uuid(self) -> None:
        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        event_id = client.calls[0]["json"]["event_id"]
        uuid.UUID(event_id)  # raises ValueError if not a valid UUID

    def test_same_event_id_reused_across_retries(self) -> None:
        client = _FakeClient(_FakeResponse(503), _FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        first_event_id = client.calls[0]["json"]["event_id"]
        second_event_id = client.calls[1]["json"]["event_id"]
        assert first_event_id == second_event_id

    def test_same_sent_at_reused_across_retries(self) -> None:
        client = _FakeClient(_FakeResponse(503), _FakeResponse(200))
        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        first_sent_at = client.calls[0]["json"]["sent_at"]
        second_sent_at = client.calls[1]["json"]["sent_at"]
        assert first_sent_at == second_sent_at

    def test_injectable_timestamp(self) -> None:
        fixed_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        client = _FakeClient(_FakeResponse(200))

        send_to_make(
            make_qa_result(),
            make_gemini_ok_result(),
            client=client,
            now=lambda: fixed_time,
        )

        assert client.calls[0]["json"]["sent_at"] == fixed_time.isoformat()


# ---------------------------------------------------------------------------
# Timeout configuration
# ---------------------------------------------------------------------------


class TestTimeoutConfiguration:
    def test_configured_timeout_passed_to_http_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(config, "MAKE_WEBHOOK_TIMEOUT_SECONDS", 2.5)
        client = _FakeClient(_FakeResponse(200))

        send_to_make(make_qa_result(), make_gemini_ok_result(), client=client)

        assert client.calls[0]["timeout"] == 2.5


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_unexpected_exception_does_not_propagate(self) -> None:
        class _UnexpectedSdkError(Exception):
            pass

        client = _FakeClient(_UnexpectedSdkError("unexpected internal state"))

        try:
            result = send_to_make(
                make_qa_result(), make_gemini_ok_result(), client=client
            )
        except Exception as exc:  # pragma: no cover - failure path
            pytest.fail(f"send_to_make() raised {exc!r} instead of returning ERROR")

        assert result.status == WebhookDeliveryStatus.ERROR
        # An unexpected exception is not retried.
        assert len(client.calls) == 1


# ---------------------------------------------------------------------------
# Inputs are never mutated
# ---------------------------------------------------------------------------


class TestInputsNotMutated:
    def test_qa_result_unchanged_after_successful_delivery(self) -> None:
        qa_result = make_qa_result()
        original_score = qa_result.score
        original_status = qa_result.status
        original_results = list(qa_result.validation_results)

        client = _FakeClient(_FakeResponse(200))
        send_to_make(qa_result, make_gemini_ok_result(), client=client)

        assert qa_result.score == original_score
        assert qa_result.status == original_status
        assert qa_result.validation_results == original_results

    def test_gemini_review_result_unchanged_after_successful_delivery(self) -> None:
        gemini_result = make_gemini_ok_result()
        original_summary = gemini_result.review.summary
        original_concerns = list(gemini_result.review.concerns)

        client = _FakeClient(_FakeResponse(200))
        send_to_make(make_qa_result(), gemini_result, client=client)

        assert gemini_result.review.summary == original_summary
        assert gemini_result.review.concerns == original_concerns

    def test_qa_result_unchanged_after_failed_delivery(self) -> None:
        qa_result = make_qa_result()
        original_score = qa_result.score
        original_status = qa_result.status

        client = _FakeClient(
            requests.exceptions.ConnectionError("down"),
            requests.exceptions.ConnectionError("down"),
        )
        send_to_make(qa_result, make_gemini_ok_result(), client=client)

        assert qa_result.score == original_score
        assert qa_result.status == original_status
