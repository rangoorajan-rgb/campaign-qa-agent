# Current Sprint

## Sprint Number

2

## Sprint Name

Professional Streamlit Submission Interface

## Sprint Goal

Build a polished marketer-facing interface on top of the tested
deterministic QA engine.

## Current Status

In progress — implementation and a presentation polish pass (based on
manual UI review) are both complete, and the app has been verified to
start successfully; manual browser testing by a human is still required
before this sprint can be marked done.

## Tasks To Complete

- Manual application testing — a human needs to walk through the running
  app in a browser (submit a real campaign, load each example campaign,
  check that results render correctly and legibly) before this sprint is
  considered complete

## Completed Tasks

### Presentation polish pass (based on manual UI review)

- Header — reduced whitespace above the form (`.block-container`
  `padding-top` 2rem → 1.25rem, `.app-header` `margin-bottom` 1.75rem →
  1rem); shortened supporting copy to "Validate campaign governance,
  tracking quality and launch readiness before publishing."
- Primary button — Streamlit's default red primary colour replaced with
  a business blue (`#1d4ed8`) via `.streamlit/config.toml`'s
  `[theme] primaryColor`, not a CSS override, so it applies cleanly
  wherever Streamlit uses the primary accent; red is now reserved for
  FAIL/critical status only (`st.error`, `.status-fail`). Removed
  `use_container_width=True` from the submit button so it's no longer
  full-width/dominant.
- Section hierarchy — each of the 4 form sections and the results area
  now sit in `st.container(border=True)` cards (light border, consistent
  padding) instead of being separated only by `st.divider()`; the
  dividers were removed since the card borders now do that job, which
  also reduces vertical whitespace
- Section labels — "Destination / Tracking URL" → "Tracking URL";
  Budget → "Campaign Budget (£)" (label text only — the underlying
  `destination_url`/`budget` fields, form keys, and validation logic are
  unchanged). Section headers shortened to match the task's own example
  naming: "Tracking", "Launch", "Message", "QA Results"
- Visual hierarchy — evaluated restrained icons for section headers and
  **deliberately omitted them** (see Technical Notes for reasoning);
  replaced `st.subheader`/`####` (larger, inconsistent default sizes)
  with a single compact `.section-title` style used consistently for
  every section and sub-heading
- Results presentation — status is no longer colour-only: the Status
  card now reads "✓ PASS" / "! REVIEW" / "✕ FAIL" (plain text symbols,
  not colour emoji), so status is distinguishable even without colour
  perception. `QAResult.status` is still rendered as-is — no status
  logic added to the UI
- Category breakdown — kept the same 5-card row computed from
  `ValidationResult` objects; tightened padding/font sizes for a cleaner
  scan, no charts added
- Critical Issues / Warnings — unchanged placement (always visible, never
  collapsed); recommendations now render as "**Recommendation:** ..."
  (bold label) instead of a plain-text prefix, for easier scanning
- Responsiveness — removed the `st.divider()` calls between sections
  (redundant with card borders), reduced header/card font sizes, so the
  page reads less tall on a normal laptop screen without removing any
  content
- Re-verified startup after the polish pass — `streamlit run app.py`
  launched headlessly and served HTTP 200 with no errors, then stopped
- Re-ran the full test suite after the polish pass — all 111 tests still
  pass unchanged (no test logic needed updating; only presentation copy
  changed, and no test asserted that copy)

### Sprint 2 initial implementation

- Streamlit page structure — `app.py`: page config, header, sidebar,
  4-section form, results section
- Campaign submission form — `app.py::render_form()`, `st.form()`-based
  so the app does not re-score on every keystroke
- `CampaignSubmission` integration — `app.py::_build_campaign_from_state()`
  constructs it directly from form/session-state values, no UI-side
  "fixing" of user input
- `score_campaign()` integration — `app.py::main()` calls the real
  Sprint 1 engine unmodified; no validation/scoring logic duplicated in
  the UI
- Result summary — 4 metric cards (QA Score, Status, Critical Issues,
  Warnings) plus a status-driven recommendation line
  (`src/ui_helpers.py::STATUS_META`)
- Category breakdown — `src/ui_helpers.py::category_breakdown()`,
  computed directly from `ValidationResult` objects, not invented
- Critical / Warning / Passed / Not-Applicable sections —
  `app.py::_render_result_group()`; critical and warnings are always
  visible (never collapsed), passed/not-applicable use expanders
- Error handling — scoring exceptions are caught, logged via `logging`,
  and shown to the user as a generic message with no stack trace exposed
- Responsive, restrained professional styling — custom CSS in `app.py`
  (`_CUSTOM_CSS`): capped content width, card/status styling, typography
  hierarchy; no rainbow colours, gradients, or decorative animation
- Maintain existing automated test suite — all 98 prior tests still pass;
  13 new tests added for the new pure helpers in `src/ui_helpers.py`
  (`tests/test_ui_helpers.py`); full suite is 111 tests, all passing
- Demo data support — `src/ui_helpers.py::example_campaigns()` provides
  3 curated presets (Clean Paid Search / Warning-heavy Paid Social /
  Failing Campaign) loadable via the sidebar; built as
  `CampaignSubmission` objects directly (not read from
  `data/sample_campaigns.csv`) so launch dates stay valid relative to
  "today" — see Technical Notes
- Verified the app starts — `streamlit run app.py` launched headlessly
  and served HTTP 200 with no startup errors (automated check, not a
  substitute for manual browser review)

## Technical Notes

- New files: `src/ui_helpers.py` (pure presentation helpers — category
  breakdown, status/category label maps, example campaign presets) and
  `tests/test_ui_helpers.py`. `app.py` and `config.py` were rewritten
  from their Sprint 1 stubs; no other `src/` module was touched.
- **Polish pass, `.streamlit/config.toml` added:** sets
  `[theme] primaryColor` to override Streamlit's default red primary
  button colour. This is the supported Streamlit mechanism for this —
  preferred over a brittle CSS selector targeting Streamlit's internal
  `data-testid`/`kind` attributes, which can change between Streamlit
  versions.
- **Polish pass, icons deliberately omitted:** the task allowed section
  icons "if they look professional" and explicitly permitted omitting
  them otherwise. Judgment call: colour emoji risked reinforcing the
  "default Streamlit tutorial" look this pass was meant to move away
  from; restrained internal B2B tools (the explicit target aesthetic)
  more often rely on typography and numbering alone. Numbering (1–5) plus
  the new card borders were judged sufficient for scanability without
  icons.
- **Polish pass, `STATUS_META` labels changed** (`src/ui_helpers.py`):
  `"PASS"`/`"REVIEW"`/`"FAIL"` → `"✓ PASS"`/`"! REVIEW"`/`"✕ FAIL"` so
  status is distinguishable without relying on colour, per this task's
  Results Presentation requirement. `recommendation` copy (which
  `tests/test_ui_helpers.py::TestStatusMeta::test_recommendation_copy_matches_spec`
  asserts exactly) was left untouched; no test asserted `label` content,
  so no test updates were required.
- **Demo data decision:** the sidebar's "Example Campaign" loader uses 3
  hand-built `CampaignSubmission` presets in `src/ui_helpers.py` rather
  than reading rows from `data/sample_campaigns.csv`. The CSV's rows are
  anchored to a fixed reference date (2026-08-07, see Decision 002/003
  context and `data/README.md`) for deterministic *testing*; a live demo
  loader needs launch dates that stay valid relative to whatever "today"
  actually is when someone runs the app, which the fixed CSV dates
  cannot guarantee. Building 3 presets directly avoids CSV parsing
  complexity in `app.py` entirely and keeps the demo data trivially
  testable (`tests/test_ui_helpers.py::TestExampleCampaigns`) against
  the real `score_campaign()` pipeline.
- The QA engine itself (`src/models.py`, `src/constants.py`,
  `src/validators.py`, `src/scoring.py`) was not modified — see Decision
  002/003 for the rules this sprint's UI renders but does not alter.

## Known Issues

*None identified in automated testing. Manual browser review may surface
UX issues not visible from code/automated checks — record any here once
found.*

## Blockers

*None.*

## Next Session Starting Point

Manually run `streamlit run app.py` and walk through the app in a
browser: submit a real campaign, load each of the 3 example campaigns,
and confirm the layout, styling, and result sections read clearly. Once
confirmed, update this document's Current Status to "Completed" and add
the Sprint Retrospective section (see Sprint 1's entry for the expected
format).

## Definition of Done

- [x] Streamlit form collects all `CampaignSubmission` fields
- [x] Submission calls the real `score_campaign()` — no duplicated
      validation/scoring logic in the UI
- [x] QA Score, Status, Critical Issues, and Warnings are clearly
      presented
- [x] Critical Issues and Warnings are never hidden in collapsed
      sections
- [x] Category breakdown is computed from `ValidationResult` objects,
      not invented
- [x] Errors are handled gracefully with no stack traces shown to the
      user
- [x] Existing 98 tests still pass; new pure helpers have focused tests
      (111 total)
- [ ] **A human has manually verified the app in a browser** — pending,
      blocks marking this sprint complete
