"""Outbound webhook delivery to Make.

Third-stage, side-effect-only integration that runs after the
deterministic QA engine and the Gemini qualitative review have both
already produced their results. This module never influences either —
send_to_make() only reads a QAResult and a GeminiReviewResult and posts a
summary of them onward; it never raises to its caller, and a delivery
failure can never change a score, a status, or hide either result.

See project_management/DECISIONS.md, Decision 005, for the full webhook
contract and the reasoning behind its failure-isolation boundaries.

Slack notifications are not yet implemented; this module is scoped to
Make only for now, despite its generic name (see src/models.py,
WebhookDeliveryResult, for why the result type itself is kept generic).
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import requests

import config

from .models import (
    CampaignSubmission,
    GeminiReviewResult,
    GeminiReviewStatus,
    QAResult,
    ValidationCategory,
    ValidationResult,
    WebhookDeliveryResult,
    WebhookDeliveryStatus,
)

logger = logging.getLogger(__name__)

_EVENT_NAME = "campaign.qa.completed"
_RETRY_DELAY_SECONDS = 1
_SAFE_ERROR_MESSAGE = "The webhook could not be delivered to Make."


def _build_campaign_payload(campaign: CampaignSubmission) -> dict[str, Any]:
    return {
        "campaign_name": campaign.campaign_name,
        "campaign_type": campaign.campaign_type,
        "channel": campaign.channel,
        "objective": campaign.objective,
        "target_audience": campaign.target_audience,
        "campaign_owner": campaign.campaign_owner,
        "cta": campaign.cta,
        "launch_date": (
            campaign.launch_date.isoformat() if campaign.launch_date else None
        ),
        "landing_page_url": campaign.landing_page_url,
        "destination_url": campaign.destination_url,
        "utm_source": campaign.utm_source,
        "utm_medium": campaign.utm_medium,
        "utm_campaign": campaign.utm_campaign,
    }


def _result_summary(result: ValidationResult) -> dict[str, Any]:
    return {
        "rule_id": result.rule_id,
        "category": result.category.value,
        "message": result.message,
    }


def _category_breakdown(
    results: list[ValidationResult],
) -> dict[str, dict[str, float]]:
    totals: dict[ValidationCategory, list[float]] = {
        category: [0.0, 0.0] for category in ValidationCategory
    }
    for result in results:
        entry = totals[result.category]
        entry[0] += result.points_earned
        entry[1] += result.points_available
    return {
        category.value: {"earned": earned, "available": available}
        for category, (earned, available) in totals.items()
    }


def _build_qa_result_payload(qa_result: QAResult) -> dict[str, Any]:
    return {
        "score": qa_result.score,
        "status": qa_result.status.value,
        "critical_failure_count": len(qa_result.critical_failures),
        "warning_count": len(qa_result.warnings),
        "critical_failures": [
            _result_summary(result) for result in qa_result.critical_failures
        ],
        "warnings": [_result_summary(result) for result in qa_result.warnings],
        "category_breakdown": _category_breakdown(qa_result.validation_results),
    }


def _build_ai_review_payload(
    review_result: GeminiReviewResult,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": review_result.status.value}
    if review_result.status == GeminiReviewStatus.OK and review_result.review is not None:
        review = review_result.review
        payload["summary"] = review.summary
        payload["concerns"] = [
            {
                "title": concern.title,
                "severity": concern.severity.value,
                "explanation": concern.explanation,
            }
            for concern in review.concerns
        ]
        payload["recommendation"] = review.recommendation
    return payload


def _build_payload(
    qa_result: QAResult,
    gemini_review_result: GeminiReviewResult,
    *,
    event_id: str,
    sent_at: str,
) -> dict[str, Any]:
    return {
        "event": _EVENT_NAME,
        "event_id": event_id,
        "sent_at": sent_at,
        "campaign": _build_campaign_payload(qa_result.campaign),
        "qa_result": _build_qa_result_payload(qa_result),
        "ai_review": _build_ai_review_payload(gemini_review_result),
    }


def send_to_make(
    qa_result: QAResult,
    gemini_review_result: GeminiReviewResult,
    *,
    client: Any = None,
    now: Callable[[], datetime] | None = None,
) -> WebhookDeliveryResult:
    """Deliver a QA result (plus its AI review) to the Make webhook.

    Purely additive to the pipeline: reads ``qa_result`` and
    ``gemini_review_result`` without mutating either, and always returns a
    valid WebhookDeliveryResult — callers never need to catch exceptions
    from this function themselves.

    ``client`` is dependency-injected, mirroring
    ``analyze_campaign()``'s ``client`` parameter: production code leaves
    it as None, which uses the real ``requests`` module against
    ``config.MAKE_WEBHOOK_URL``. If no client is injected and no URL is
    configured, delivery is reported as NOT_CONFIGURED rather than
    attempted. ``now`` is similarly injectable so tests can assert an
    exact ``sent_at`` value.

    One ``event_id`` and one ``sent_at`` are generated once, before any
    HTTP attempt, and reused across every retry within this call — they
    identify the logical event being delivered, not the individual
    delivery attempt.
    """
    if client is None:
        if not config.MAKE_WEBHOOK_URL:
            return WebhookDeliveryResult(status=WebhookDeliveryStatus.NOT_CONFIGURED)
        client = requests

    clock = now or (lambda: datetime.now(timezone.utc))
    event_id = str(uuid.uuid4())
    sent_at = clock().isoformat()
    payload = _build_payload(
        qa_result, gemini_review_result, event_id=event_id, sent_at=sent_at
    )

    max_attempts = config.MAKE_WEBHOOK_MAX_ATTEMPTS
    for attempt in range(1, max_attempts + 1):
        is_last_attempt = attempt == max_attempts
        try:
            response = client.post(
                config.MAKE_WEBHOOK_URL,
                json=payload,
                timeout=config.MAKE_WEBHOOK_TIMEOUT_SECONDS,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            logger.exception(
                "Webhook delivery attempt %d/%d failed for event_id=%s",
                attempt,
                max_attempts,
                event_id,
            )
            if is_last_attempt:
                return WebhookDeliveryResult(
                    status=WebhookDeliveryStatus.ERROR,
                    error_message=_SAFE_ERROR_MESSAGE,
                )
            time.sleep(_RETRY_DELAY_SECONDS)
            continue
        except Exception:
            logger.exception(
                "Unexpected failure delivering webhook for event_id=%s", event_id
            )
            return WebhookDeliveryResult(
                status=WebhookDeliveryStatus.ERROR,
                error_message=_SAFE_ERROR_MESSAGE,
            )

        if 200 <= response.status_code < 300:
            logger.info(
                "Webhook delivered for event_id=%s (campaign=%s, status_code=%d)",
                event_id,
                qa_result.campaign.campaign_name,
                response.status_code,
            )
            return WebhookDeliveryResult(
                status=WebhookDeliveryStatus.SENT,
                http_status_code=response.status_code,
            )

        if response.status_code >= 500:
            logger.warning(
                "Webhook delivery attempt %d/%d received HTTP %d for event_id=%s",
                attempt,
                max_attempts,
                response.status_code,
                event_id,
            )
            if is_last_attempt:
                return WebhookDeliveryResult(
                    status=WebhookDeliveryStatus.ERROR,
                    http_status_code=response.status_code,
                    error_message=_SAFE_ERROR_MESSAGE,
                )
            time.sleep(_RETRY_DELAY_SECONDS)
            continue

        # 4xx (or any other non-2xx/5xx code): not retryable.
        logger.error(
            "Webhook delivery rejected with HTTP %d for event_id=%s",
            response.status_code,
            event_id,
        )
        return WebhookDeliveryResult(
            status=WebhookDeliveryStatus.ERROR,
            http_status_code=response.status_code,
            error_message=_SAFE_ERROR_MESSAGE,
        )

    # Defensive fallback; every branch above returns before the loop can
    # exhaust normally. Kept so the function's return type is total.
    return WebhookDeliveryResult(
        status=WebhookDeliveryStatus.ERROR, error_message=_SAFE_ERROR_MESSAGE
    )
