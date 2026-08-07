# Current Sprint

## Sprint Number

1

## Sprint Name

Rule-Based QA Engine

## Sprint Goal

Build and test the deterministic campaign validation and scoring engine
that will become the foundation of the application.

## Current Status

In progress — domain models and validators complete, scoring not yet
started

## Tasks To Complete

- Implement weighted QA scoring
- Implement PASS / REVIEW / FAIL logic
- Implement critical-failure override logic
- Create representative sample campaign data
- Write pytest unit tests (scoring)
- Run tests and fix failures

## Completed Tasks

- Define campaign data model — `src/models.py::CampaignSubmission`
- Define validation result data structures — `src/models.py::ValidationResult`,
  `ValidationStatus`, `ValidationSeverity`, `ValidationCategory`, plus
  `QAResult`/`QAStatus`
- Define paid vs non-paid campaign logic (constants only) —
  `src/constants.py::PAID_CAMPAIGN_TYPES`, `CATEGORY_WEIGHTS`
- Implement required-field validation — `src/validators.py::validate_required_fields`
- Implement URL validation — `src/validators.py::validate_landing_page_url`,
  `validate_destination_url`
- Implement UTM validation — `src/validators.py::validate_utms`
- Implement campaign naming validation — `src/validators.py::validate_campaign_naming`
- Implement launch readiness validation — `src/validators.py::validate_launch_readiness`
- Implement CTA validation — `src/validators.py::validate_cta`
- Write pytest unit tests (validators) — `tests/test_validators.py`, 62 tests
  passing across `test_models.py` and `test_validators.py`
- Run tests and fix failures — full suite passing, no failures encountered
- Correct validation model: added `ValidationStatus.NOT_APPLICABLE` and
  `QAResult.not_applicable_checks` so paid-only rules evaluated against a
  non-paid campaign report as genuinely not applicable rather than as a
  misleading PASS — see Decision 003 amendment

## Technical Notes

The deterministic QA/scoring model referenced by this sprint's tasks is
locked and documented in
[project_management/DECISIONS.md](DECISIONS.md):

- **Decision 002** — category weights (Tracking & UTMs 30, Required
  campaign information incl. CTA 20, URL & destination integrity 20,
  Naming & governance 15, Launch readiness 15 — total 100), status
  thresholds (90–100 no critical failures = PASS; 90–100 with a critical
  failure = REVIEW; 70–89 = REVIEW; 0–69 = FAIL), and the full
  critical-failure/warning/naming/UTM/URL/CTA/owner rule set.
- **Decision 003** (amended) — the per-rule points table
  (`src/constants.py::RULE_POINTS`) and the "every rule always fires"
  design principle that keeps every category's available points constant
  (matching its Decision 002 weight) regardless of campaign type or field
  completeness. Amended to distinguish two "nothing wrong" outcomes:
  `ValidationStatus.NOT_APPLICABLE` (a paid-only rule evaluated on a
  non-paid campaign — e.g. `paid_budget`, `utm_source_required`,
  `destination_url_utms`) versus `PASS` with a "not evaluated" message (a
  universally-applicable rule with nothing to check because a prerequisite
  field is missing, already flagged critical elsewhere). Both award full
  points; only the semantic status differs. `scoring.py` can still sum
  `points_earned` flatly — this amendment does not change the scoring
  mathematics, only what status is reported per check.

`src/validators.py` orchestrates all rules via `validate_campaign()`. Do
not duplicate the rule tables here — refer to Decisions 002/003 during
scoring implementation. When building `scoring.py`'s critical-failure
override, note that `critical_failures` (severity CRITICAL + status FAIL)
is unaffected by NOT_APPLICABLE — NOT_APPLICABLE results are always
severity INFO.

## Known Issues

## Blockers

## Next Session Starting Point

Begin `src/scoring.py`: sum `points_earned`/`points_available` from
`validate_campaign()`'s results into a 0–100 score, then apply the
PASS/REVIEW/FAIL thresholds and critical-failure override from Decision
002 to produce a `QAResult`.

## Definition of Done

- Validators work independently of Streamlit
- Scoring produces deterministic results
- Critical failures prevent PASS
- Automated tests cover successful, warning and failure scenarios
- All tests pass
- No Gemini, Make, Slack or Google Sheets implementation is added during
  this sprint
