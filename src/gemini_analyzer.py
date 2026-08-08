"""Gemini-powered qualitative campaign review.

Second-stage, advisory-only reviewer that runs after the deterministic QA
engine (src.validators, src.scoring) has already produced a QAResult. This
module never re-scores a campaign, never produces a PASS/REVIEW/FAIL
verdict, and never raises Gemini/network/parsing exceptions to its
caller — analyze_campaign() always returns a valid GeminiReviewResult, so
a Gemini failure can never break or hide the deterministic result it
supplements.

See project_management/DECISIONS.md, Decision 004, for the reasoning
behind this module's boundaries and its structured-output design.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

import config

from .models import (
    CampaignSubmission,
    GeminiConcern,
    GeminiConcernSeverity,
    GeminiReview,
    GeminiReviewResult,
    GeminiReviewStatus,
    QAResult,
)

logger = logging.getLogger(__name__)

_SAFE_CALL_ERROR_MESSAGE = "The AI review service could not be reached."
_SAFE_PARSE_ERROR_MESSAGE = "The AI review response could not be understood."

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "concerns": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "explanation": {"type": "STRING"},
                    "severity": {
                        "type": "STRING",
                        "enum": ["LOW", "MEDIUM", "HIGH"],
                    },
                },
                "required": ["title", "explanation", "severity"],
            },
        },
        "strengths": {"type": "ARRAY", "items": {"type": "STRING"}},
        "recommendation": {"type": "STRING"},
    },
    "required": ["summary", "concerns", "strengths", "recommendation"],
}
"""JSON schema passed to Gemini's structured-output mode. Parsing in
_parse_review() is written against this shape explicitly, rather than
relying on the SDK's automatic Python-type-to-schema conversion, so the
expected shape is visible and testable in one place."""


def _format_qa_context(qa_result: QAResult) -> str:
    critical_lines = (
        "\n".join(
            f"- {result.rule_id}: {result.message}"
            for result in qa_result.critical_failures
        )
        or "none"
    )
    warning_lines = (
        "\n".join(
            f"- {result.rule_id}: {result.message}"
            for result in qa_result.warnings
        )
        or "none"
    )
    return (
        f"QA Score: {qa_result.score}/100\n"
        f"QA Status: {qa_result.status.value}\n"
        f"Critical failures already flagged:\n{critical_lines}\n"
        f"Warnings already flagged:\n{warning_lines}"
    )


def _build_prompt(campaign: CampaignSubmission, qa_result: QAResult) -> str:
    """Build the qualitative-review prompt sent to Gemini.

    Explicitly frames the deterministic QA result as context only, and
    explicitly prohibits Gemini from producing a score or a
    PASS/REVIEW/FAIL verdict — the deterministic engine already owns that
    decision (see Decision 004).
    """
    return f"""You are a Marketing Operations reviewer providing a qualitative second opinion on a campaign that has already passed automated, rule-based QA.

Deterministic QA has ALREADY been performed on this campaign. The QA score, status, and any critical failures or warnings below are provided as CONTEXT ONLY. Do not re-check formatting, UTM syntax, naming conventions, URL validity, or required fields — those have already been mechanically validated. Do not repeat a mechanical check unless it is directly relevant to explaining a qualitative issue you are raising.

Focus only on qualitative questions a deterministic rule cannot reliably judge:
- Objective and audience alignment
- Objective and CTA alignment
- Campaign message clarity
- Proposition relevance
- Message/channel coherence
- Obvious contextual inconsistencies
- Qualitative campaign risks
- Genuine strengths
- One practical improvement recommendation

Do NOT produce a numeric score. Do NOT produce a PASS, REVIEW, or FAIL verdict, and do not restate the deterministic result below as if it were your own judgment — the deterministic engine already owns that decision.

CAMPAIGN
Campaign Name: {campaign.campaign_name}
Campaign Type: {campaign.campaign_type}
Channel: {campaign.channel}
Objective: {campaign.objective}
Target Audience: {campaign.target_audience}
CTA: {campaign.cta}
Campaign Message / Proposition: {campaign.campaign_message or "(none provided)"}
Owner: {campaign.campaign_owner}
Launch Date: {campaign.launch_date}
Budget: {campaign.budget if campaign.budget else "(not applicable / not set)"}

DETERMINISTIC QA RESULT (context only — already computed, do not restate as your own verdict)
{_format_qa_context(qa_result)}

Respond only with JSON matching the provided response schema."""


def _parse_review(raw_text: str) -> GeminiReview:
    """Parse Gemini's structured JSON response into a GeminiReview.

    Raises on any missing/malformed field — analyze_campaign() catches
    this and converts it into an ERROR GeminiReviewResult rather than
    letting a malformed response propagate.
    """
    data = json.loads(raw_text)

    concerns = [
        GeminiConcern(
            title=str(item["title"]),
            explanation=str(item["explanation"]),
            severity=GeminiConcernSeverity(str(item["severity"]).upper()),
        )
        for item in data["concerns"]
    ]
    strengths = [str(item) for item in data["strengths"]]

    return GeminiReview(
        summary=str(data["summary"]),
        concerns=concerns,
        strengths=strengths,
        recommendation=str(data["recommendation"]),
    )


def _build_client() -> genai.Client:
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _generate_content_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=_RESPONSE_SCHEMA,
    )


def analyze_campaign(
    campaign: CampaignSubmission,
    qa_result: QAResult,
    *,
    client: Any = None,
) -> GeminiReviewResult:
    """Run Gemini's qualitative second-opinion review on a campaign.

    Purely additive to the deterministic pipeline: reads ``campaign`` and
    ``qa_result`` without mutating either, and always returns a valid
    GeminiReviewResult — callers never need to catch exceptions from this
    function themselves.

    ``client`` is dependency-injected, mirroring how
    ``score_campaign()``'s ``reference_date`` exists purely so tests can
    avoid a real dependency (there, real dates; here, a real network
    call). Production code leaves it as None, which builds a real
    ``genai.Client`` from ``config.GEMINI_API_KEY``. If no client is
    injected and no API key is configured, the review is reported as
    NOT_CONFIGURED rather than attempted.
    """
    if client is None:
        if not config.GEMINI_API_KEY:
            return GeminiReviewResult(status=GeminiReviewStatus.NOT_CONFIGURED)
        client = _build_client()

    prompt = _build_prompt(campaign, qa_result)

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=_generate_content_config(),
        )
        raw_text = response.text
    except Exception:
        logger.exception("Gemini API call failed")
        return GeminiReviewResult(
            status=GeminiReviewStatus.ERROR,
            error_message=_SAFE_CALL_ERROR_MESSAGE,
        )

    try:
        review = _parse_review(raw_text)
    except Exception:
        logger.exception("Failed to parse Gemini response")
        return GeminiReviewResult(
            status=GeminiReviewStatus.ERROR,
            error_message=_SAFE_PARSE_ERROR_MESSAGE,
        )

    return GeminiReviewResult(status=GeminiReviewStatus.OK, review=review)
