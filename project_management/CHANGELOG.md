# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

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
