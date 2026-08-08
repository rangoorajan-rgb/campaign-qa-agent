# Current Sprint

## Sprint Number

3

## Sprint Name

Gemini Qualitative Review

## Sprint Goal

Add Gemini as a second-stage, advisory-only qualitative reviewer that
runs automatically after the deterministic QA engine, without touching
the deterministic validation or scoring logic.

## Current Status

In progress — implementation complete and the full automated suite
passes; manual browser testing (with and without a configured
`GEMINI_API_KEY`) by a human is still required before this sprint can be
marked done.

## Tasks To Complete

- Manual application testing — a human needs to run the app with a real
  `GEMINI_API_KEY` configured and confirm the AI Review section renders
  correctly for a real Gemini response, in addition to the
  `NOT_CONFIGURED` state (verifiable without a key)

## Completed Tasks

- Domain models — `src/models.py`: added `GeminiReviewStatus`
  (OK/NOT_CONFIGURED/ERROR), `GeminiConcernSeverity` (LOW/MEDIUM/HIGH),
  `GeminiConcern`, `GeminiReview`, `GeminiReviewResult`. Purely additive;
  no existing model changed
- Config — `config.py`: loads `GEMINI_API_KEY` and `GEMINI_MODEL`
  (default `gemini-2.5-flash`) from the environment via `python-dotenv`;
  `.env.example` documents both
- Gemini analyzer — `src/gemini_analyzer.py` implemented:
  `analyze_campaign(campaign, qa_result, *, client=None) ->
  GeminiReviewResult`. Builds the qualitative-review prompt, calls
  `google-genai` with structured JSON output
  (`response_mime_type="application/json"` + explicit `response_schema`),
  parses the response, and never raises — all failure modes resolve to a
  valid `GeminiReviewResult`
- Tests — `tests/test_gemini_analyzer.py`, 19 tests, all using an
  injected fake client (no real network calls, no `GEMINI_API_KEY`
  required to run the suite): successful structured response, prompt
  content (campaign fields, deterministic QA context, explicit
  score/verdict prohibition), `NOT_CONFIGURED`, API-failure and
  malformed-response `ERROR` paths, non-propagation of unexpected
  exceptions, and non-mutation of the input `QAResult`
- Streamlit integration — `app.py`: `analyze_campaign()` is called
  automatically inside the same `if submitted:` branch as
  `score_campaign()`, wrapped in `st.spinner("Running AI review...")`;
  the deterministic `QAResult` is written to `st.session_state` *before*
  Gemini is ever called, so a Gemini failure cannot hide or alter it.
  New `render_ai_review()` renders a "6. AI Review" section after the
  deterministic results, with distinct handling for `OK` (summary,
  concerns, strengths, recommendation), `NOT_CONFIGURED`, and `ERROR`
  states — no raw exceptions shown, no PASS/REVIEW/FAIL colour styling
  reused for AI severity
- Session state — the Gemini call only happens inside the
  submission-triggered branch, so a rerun that isn't a new form
  submission (e.g. expanding an expander) never re-triggers a Gemini
  call; no caching layer was built
- Full regression run — all 138 tests pass (119 pre-Sprint-3 + 19 new)
- Streamlit startup smoke test — `streamlit run app.py` launched
  headlessly and served HTTP 200 with no errors, then stopped (no real
  Gemini call occurs without a configured API key, so this is safe to
  run in this environment)
- Documentation — added Decision 004 to `DECISIONS.md`; updated this
  document; updated `README.md` to note Gemini integration is in
  progress

## Technical Notes

- New files: `tests/test_gemini_analyzer.py`. `src/gemini_analyzer.py`
  was implemented (was a docstring stub). `src/models.py` and
  `config.py` were extended, not rewritten. `app.py` was extended with
  Gemini wiring on top of its Sprint 2 form/results code, which is
  otherwise unchanged.
- **Not touched:** `src/validators.py`, `src/scoring.py`,
  `src/constants.py`, `CATEGORY_WEIGHTS`, `RULE_POINTS`, and every
  Sprint 1/2 test file — per this sprint's explicit constraint that the
  deterministic engine and its rules are off-limits.
- See [DECISIONS.md](DECISIONS.md), Decision 004, for the full set of
  guardrails this integration was built against (Gemini is advisory
  only; structured output over prose parsing; two independent layers of
  failure isolation; automatic single-submission trigger; no new
  caching infrastructure).
- No `.env` file exists in this development environment, so
  `GEMINI_API_KEY` is unset locally — the Streamlit smoke test and any
  local manual click-through will exercise the `NOT_CONFIGURED` path
  only, until a real key is supplied.

## Known Issues

*None identified in automated testing. The `OK` (successful review)
path has only been exercised against a fake client in tests — it has
not yet been exercised against a real Gemini API response. Record any
issues found during manual testing with a real key here.*

## Blockers

*None.*

## Next Session Starting Point

Manually run `streamlit run app.py`, add a real `GEMINI_API_KEY` to a
local `.env` file, submit a campaign, and confirm: the spinner appears,
the AI Review section renders a real summary/concerns/strengths/
recommendation, and the deterministic result above it is unaffected.
Also confirm the `NOT_CONFIGURED` message appears correctly when no key
is set. Once both are confirmed, update this document's Current Status
to "Completed" and add a Sprint Retrospective (see Sprint 1's entry for
the expected format).

## Definition of Done

- [x] Gemini runs automatically after `score_campaign()` succeeds, in a
      single user submission
- [x] Gemini never produces a score or a PASS/REVIEW/FAIL verdict
- [x] Gemini failures (unconfigured, API error, malformed response)
      never hide or alter the deterministic QA result
- [x] `GEMINI_MODEL` is configurable via environment variable, not
      hard-coded
- [x] Structured JSON output is used, not prose parsing
- [x] No test makes a real network request; all 138 tests pass
- [x] Deterministic validation, scoring, `CATEGORY_WEIGHTS`, and
      `RULE_POINTS` are unmodified
- [ ] **A human has manually verified the AI Review section against a
      real Gemini API response** — pending, blocks marking this sprint
      complete
