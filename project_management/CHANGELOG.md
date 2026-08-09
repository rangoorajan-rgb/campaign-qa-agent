# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-08-09

### Summary

Slack notification integration, added as the final step of the existing
Make automation, verified end-to-end live.

### Added

- Slack notification module inside the existing Make.com scenario
  (external configuration, not repository code), triggered immediately
  after a successful Google Sheets audit-log write
- Notifications post to the `#campaign-qa` Slack channel containing
  Campaign Name, Campaign Owner, Channel, QA Score, QA Status, Critical
  Failure Count, Warning Count, AI Summary, and AI Recommendation —
  sourced from the same `campaign.qa.completed` webhook payload already
  used for Google Sheets logging (Decision 005), with no payload changes
  required

### Testing

- Live end-to-end verification (human-performed): full workflow executed
  — Streamlit → QA Engine → Gemini → Make Webhook → Google Sheets →
  Slack — with the resulting message confirmed inside the TaskFlowAI
  Slack workspace
- Regression check: Google Sheets audit logging confirmed still
  operational; all previously verified functionality (deterministic QA,
  Gemini review, Make webhook delivery) continues working with no
  regressions found
- No automated test coverage exists for this capability, since it lives
  entirely in external Make configuration rather than in `src/` — see
  `project_management/CURRENT_SPRINT.md` (Sprint 6) for why this can
  only be confirmed by live verification, not by `pytest`

### Notes

Google Sheets audit logging (also implemented via Make.com, downstream
of the same webhook) was completed and live-verified prior to this
release but was not given its own changelog entry at the time; see
`README.md`'s Architecture section and
`project_management/FUTURE_PRODUCT_ROADMAP.md` for its implementation
details. With this release, the originally scoped integration roadmap
(Streamlit, Gemini, Make, Google Sheets, Slack) is complete end-to-end.
Future product direction beyond this MVP is tracked separately in
`project_management/FUTURE_PRODUCT_ROADMAP.md`.

## [0.3.0] - 2026-08-08

### Summary

Make webhook integration, verified end-to-end against a live Make
scenario.

### Added

- Webhook delivery module (`src/webhook.py`): `send_to_make(qa_result,
  gemini_review_result, *, client=None, now=None) ->
  WebhookDeliveryResult`, sending a `campaign.qa.completed` event to a
  configured Make scenario as a side effect after the deterministic QA
  engine and Gemini review have both already completed
- Domain models (`src/models.py`): `WebhookDeliveryStatus`
  (SENT/NOT_CONFIGURED/ERROR) and `WebhookDeliveryResult`, named
  generically so a future Slack integration can reuse them
- Retry logic: up to `MAKE_WEBHOOK_MAX_ATTEMPTS` attempts (default 2),
  retrying only on connection errors, timeouts, and HTTP 5xx — never on
  HTTP 4xx
- A stable `event_id` (UUID4) and `sent_at` (UTC ISO 8601) generated
  once per delivery and reused across retries, for future idempotency
  and audit tracing
- Configuration: `MAKE_WEBHOOK_URL`, `MAKE_WEBHOOK_TIMEOUT_SECONDS`
  (default 5), `MAKE_WEBHOOK_MAX_ATTEMPTS` (default 2)
- Streamlit integration: automatic delivery after every successful QA
  submission, with a "Sending to Make..." spinner and a minimal
  status caption ("Sent to Make" / a calm failure message); no UI output
  at all when the webhook is unconfigured
- Tests (`tests/test_webhook.py`, 24 tests): payload shape and exclusion
  assertions, retry behaviour, event-identity stability across retries,
  and non-mutation of both the deterministic and AI review results — all
  using an injected fake HTTP client, no real network calls

### Changed

- `README.md` updated: Gemini qualitative review and Make webhook
  automation both now listed as implemented, not planned

### Testing

- 162 passing tests (138 prior + 24 new for the webhook module)
- Live-verified against a real Make scenario: 1 operation received with
  the expected `campaign.qa.completed` payload shape and no secrets
  present in the payload

### Notes

The Streamlit dashboard (Sprint 2) and the Gemini qualitative review
(Sprint 3) were also completed prior to this release but were not given
their own changelog entries at the time; see
[project_management/DECISIONS.md](DECISIONS.md) (Decisions 004 and 005)
and `CURRENT_SPRINT.md`'s sprint history for their implementation
details. Google Sheets logging and Slack notifications remain planned,
not yet built.

## [0.2.0] - 2026-08-07

### Summary

Completed deterministic QA engine.

### Added

- Typed domain models for campaign submissions and QA results
  (`src/models.py`): `CampaignSubmission`, `ValidationResult`, `QAResult`,
  and the `ValidationStatus` / `ValidationSeverity` / `ValidationCategory`
  / `QAStatus` enums, including the `NOT_APPLICABLE` validation status
- Governance constants (`src/constants.py`): paid campaign types and the
  per-rule points table
- Deterministic rule-based validation engine (`src/validators.py`):
  required-field, URL, UTM, campaign-naming, launch-readiness, and CTA
  validators, orchestrated by `validate_campaign()`
- Deterministic scoring engine (`src/scoring.py`): `score_campaign()`,
  producing a 0–100 score, PASS/REVIEW/FAIL status, and the
  critical-failure override
- Representative sample dataset (`data/sample_campaigns.csv`): 35
  campaigns across 8 channel types (Paid Search, Paid Social, Display,
  Content Syndication, Email, Organic Social, Webinar, Partner
  Marketing), spanning excellent, PASS-ready, warning, and
  critical-failure quality tiers
- Integration tests (`tests/test_integration.py`) exercising the real
  `CampaignSubmission -> validate_campaign() -> score_campaign() ->
  QAResult` pipeline against the sample dataset, without mocking

### Changed

- `data/sample_campaigns.csv` replaced its placeholder header-only
  content with the representative dataset above
- `README.md` and `docs/architecture.md` updated to reflect that the QA
  engine is implemented (previously described as entirely unimplemented)

### Testing

- 84+ passing tests: unit tests for models, validators, and scoring, plus
  end-to-end integration tests over the full sample dataset
- No Streamlit, Gemini, Make, Google Sheets, or Slack code exists yet —
  this release is the deterministic QA engine only

## [0.1.1] - 2026-08-07

### Summary

Project planning and dependency maintenance.

### Added

- Master Project Plan content
- Sprint 1 definition
- Engineering Decision 001

### Changed

- Gemini dependency migrated to `google-genai`

### Fixed

- N/A

### Notes

This version adds project planning documentation only. No application
functionality has been implemented.

## [0.1.0] - 2026-08-07

### Summary

Initial repository bootstrap. No application logic implemented.

### Added

- Repository directory structure (`src/`, `tests/`, `data/`, `docs/`,
  `assets/`, `.github/workflows/`)
- Project documentation (`README.md`, `docs/architecture.md`,
  `docs/roadmap.md`)
- Module stubs for all planned `src/` and `tests/` files (docstrings only)
- Packaging configuration (`pyproject.toml`, `requirements.txt`)
- `LICENSE` (MIT), `.gitignore`, `.env.example`

### Changed

- N/A

### Fixed

- N/A

### Notes

This version establishes the repository foundation only. No QA logic,
scoring, UI, or integrations have been implemented.
