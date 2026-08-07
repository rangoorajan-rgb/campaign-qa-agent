# Current Sprint

## Sprint Number

1

## Sprint Name

Rule-Based QA Engine

## Sprint Goal

Build and test the deterministic campaign validation and scoring engine
that will become the foundation of the application.

## Current Status

Completed

## Tasks To Complete

*None — Sprint 1 is complete.*

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
- Write pytest unit tests (validators) — `tests/test_validators.py`
- Correct validation model: added `ValidationStatus.NOT_APPLICABLE` and
  `QAResult.not_applicable_checks` so paid-only rules evaluated against a
  non-paid campaign report as genuinely not applicable rather than as a
  misleading PASS — see Decision 003 amendment
- Implement weighted QA scoring — `src/scoring.py::score_campaign`,
  `_calculate_score`
- Implement PASS / REVIEW / FAIL logic — `src/scoring.py::_determine_status`
- Implement critical-failure override logic — `src/scoring.py::_critical_failures`
- Write pytest unit tests (scoring) — `tests/test_scoring.py`
- Create representative sample campaign data — `data/sample_campaigns.csv`,
  35 campaigns across 8 channel types, tagged by intended QA outcome
  (`quality_tier`)
- Write integration tests — `tests/test_integration.py`, exercises the real
  `CampaignSubmission -> validate_campaign() -> score_campaign() ->
  QAResult` pipeline against all 35 sample campaigns, no mocking
- Run tests and fix failures — full suite (98 tests) passing, no failures
  encountered

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

*None.*

## Blockers

*None.*

## Next Session Starting Point

Sprint 1 is complete. Sprint 2 has not yet been scoped — begin by
defining its goal and task list in this document (Streamlit is the next
roadmap phase, per `docs/roadmap.md`, but Sprint 2's exact scope is a
planning decision for the next session, not assumed here).

## Definition of Done

- Validators work independently of Streamlit — ✅ confirmed;
  `src/validators.py` has no Streamlit/UI dependency
- Scoring produces deterministic results — ✅ confirmed; `score_campaign()`
  is a pure function of its inputs (and `reference_date`)
- Critical failures prevent PASS — ✅ confirmed; critical-failure override
  tested at exact score boundaries (69/70/89/90) and via the sample
  dataset
- Automated tests cover successful, warning and failure scenarios — ✅
  confirmed; 98 tests across unit (models, validators, scoring) and
  integration (sample dataset) layers
- All tests pass — ✅ 98/98 passing
- No Gemini, Make, Slack or Google Sheets implementation is added during
  this sprint — ✅ confirmed; only `src/models.py`, `src/constants.py`,
  `src/validators.py`, `src/scoring.py`, and their tests were touched

## Sprint Retrospective

### What Was Achieved

Sprint 1 delivered a complete, independently testable deterministic QA
engine: typed domain models (`CampaignSubmission`, `ValidationResult`,
`QAResult`), governance constants, seven rule-based validators covering
every check in Decision 002, a scoring engine applying the locked
weights/thresholds/critical-failure override, a 35-row representative
sample dataset spanning 8 channel types and four quality tiers, and a
98-test suite (unit + integration, no mocking) — all without touching
Streamlit, Gemini, or any external integration.

### Lessons Learned

- Locking the scoring model and point allocations as explicit, numbered
  decisions (002/003) before writing validators paid off — it turned
  ambiguous requirements into a checklist and gave later steps (scoring,
  sample data, integration tests) a single source of truth to verify
  against instead of re-deriving intent from code.
- Predicting exact scores by hand for the sample dataset was unreliable
  once more than two or three point deductions stacked up. Building the
  dataset by running it through the real `score_campaign()` pipeline and
  iterating until each row landed in its intended tier was far more
  reliable than manual arithmetic, and is the approach worth repeating
  for any future hand-authored test fixtures.
- The "every rule always fires" design principle (Decision 003), later
  refined to distinguish `NOT_APPLICABLE` from `PASS` (Decision 003
  amendment), was easy to get subtly wrong at the edges (e.g. an optional
  field that *was* supplied on a non-paid campaign). Writing the
  "supplied vs. required" test cases explicitly caught this before it
  reached the sample dataset.

### Preparation for Sprint 2

The QA engine's public surface for Sprint 2 to build against is
`src/scoring.py::score_campaign(campaign, *, reference_date=None) ->
QAResult`, consuming a `CampaignSubmission` and returning a `QAResult`
whose `passed_checks` / `warnings` / `failed_checks` /
`not_applicable_checks` / `critical_failures` properties are ready to
drive a UI, an audit log, or a notification without further
transformation. Per `docs/roadmap.md`, Phase 3 (Streamlit application) is
the next planned phase; Sprint 2 planning should confirm that scope
explicitly in this document before implementation begins.
