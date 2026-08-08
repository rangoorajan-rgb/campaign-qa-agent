# Engineering Decision Log

This log records significant engineering decisions made during the
development of this project, along with the context and alternatives
considered.

## Template

Copy the block below for each new decision.

---

### Decision ID

### Date

### Context

### Decision

### Alternatives Considered

### Reasoning

### Consequences

### Status

---

## Decision 001

### Decision ID

001

### Date

2026-08-07

### Context

Google's newer Gemini Python SDK is `google-genai`, while
`google-generativeai` is the older SDK.

### Decision

Use `google-genai` instead of `google-generativeai`.

### Alternatives Considered

- Continue using `google-generativeai`.

### Reasoning

Use the current supported SDK to avoid building future Gemini integration
against a legacy package.

### Consequences

Phase 4 implementation must use the `google-genai` client interface.

### Status

Accepted

---

## Decision 002

### Decision ID

002

### Date

2026-08-07

### Context

Sprint 1 (Rule-Based QA Engine) could not begin implementation until the
deterministic scoring model and validation ruleset were fully specified.
Prior sprint planning identified several open ambiguities: category
weighting, PASS/REVIEW/FAIL thresholds, the definition of a "critical
failure," paid vs. non-paid campaign handling, naming convention rules,
UTM rules, URL rules, CTA rules, and campaign owner requirements. These
have now been resolved and are locked below as the single source of truth
for the QA engine, scoring logic, and future consumers of QA results
(Streamlit UI, Google Sheets logging, Slack notifications).

### Decision

Adopt the following deterministic QA/scoring model for Sprint 1 and treat
it as authoritative until superseded by a new decision entry.

**Scoring model — total score = 100, by category:**

| Category                             | Points |
|---------------------------------------|-------:|
| Tracking & UTMs                       | 30     |
| Required campaign information (incl. CTA) | 20 |
| URL & destination integrity           | 20     |
| Naming & governance                   | 15     |
| Launch readiness                      | 15     |

CTA validation is scored within "Required campaign information," not as
its own category.

**Status thresholds and critical-failure override:**

- 90–100 with no critical failures → **PASS**
- 90–100 with one or more critical failures → **REVIEW**
- 70–89 → **REVIEW**
- 0–69 → **FAIL**

A numeric PASS-range score cannot itself produce a PASS status while any
critical failure exists. Critical failures block PASS but do not
automatically force FAIL — status is still ultimately governed by the
score band above.

**Campaign types:**

- *Paid* — Paid Search, Paid Social, Display, Content Syndication.
  Requires `utm_source`, `utm_medium`, `utm_campaign`, a destination/
  tracking URL containing those UTM parameters, and a budget greater than
  zero.
- *Non-paid* — Email, Organic Social, Webinar/Event, Other. UTMs are
  recommended, not critical. If supplied, they must still be validated
  using the same UTM rules as paid campaigns.

**Critical failures (all campaigns):**

- Missing campaign name
- Missing campaign type
- Missing channel
- Missing objective
- Missing target audience
- Missing landing-page URL
- Malformed landing-page URL
- Missing campaign owner
- Missing launch date
- Launch date in the past
- Missing CTA

**Additional critical failures (paid campaigns only):**

- Missing `utm_source`
- Missing `utm_medium`
- Missing `utm_campaign`
- Missing destination/tracking URL
- Destination URL missing required UTM parameters
- Budget missing or ≤ 0

**Warnings** (reduce the relevant category score; do not force FAIL):

- Landing-page URL uses HTTP rather than HTTPS
- Uppercase characters in campaign name
- Spaces in campaign name
- Malformed naming convention
- Uppercase UTM values
- Spaces in UTM values
- `utm_campaign` does not match normalised campaign name
- Launch date is fewer than 2 days away
- Unusually long CTA

**Campaign naming:**

Preferred conceptual structure: `market_audience_or_product_objective_period`
(e.g., `uk_enterprise_demo_q3_2026`). Sprint 1 does not attempt semantic
validation of individual components — only the following deterministic,
syntactic rules apply:

- Lowercase preferred
- Words separated by underscores
- No spaces
- Only letters, numbers, and underscores
- No leading underscore
- No trailing underscore
- No consecutive underscores

Normalisation must allow direct comparison between campaign name and
`utm_campaign` (e.g., `"UK Enterprise Demo Q3 2026"` normalises to
`"uk_enterprise_demo_q3_2026"`).

**UTM rules** (`utm_source`, `utm_medium`, `utm_campaign`):

- Required for paid campaigns; not required for non-paid campaigns
- No spaces
- Lowercase recommended
- `utm_campaign` should match the normalised campaign name
- For paid campaigns, the destination URL must contain `utm_source`,
  `utm_medium`, and `utm_campaign`
- If UTMs are supplied on a non-paid campaign, they are validated using
  the same rules

**URL rules:**

- Landing page must have an `http` or `https` scheme and a valid
  host/domain
- HTTPS is preferred; HTTP produces a warning, not a critical failure
- A malformed URL is a critical failure
- Sprint 1 performs syntactic validation only — no network requests are
  made to test resolution or HTTP status

**CTA rules:**

- Must contain non-whitespace text; blank CTA is a critical failure
- 1–60 characters is normal
- Over 60 characters produces a warning
- Subjective CTA quality analysis is out of scope for Sprint 1 and is
  deferred to the future Gemini qualitative review phase

**Campaign owner:**

- `campaign_owner` is a required string; blank owner is a critical
  failure
- An email address is not required in Sprint 1

**Validation output design:**

Every individual validation result must eventually be capable of
representing: category, rule identifier, status, severity, human-readable
message, recommendation, points available, and points earned.

- Status values: `PASS`, `WARNING`, `FAIL`
- Severity values (minimum): `INFO`, `WARNING`, `CRITICAL`

This structure is designed so the Streamlit UI, Google Sheets logging,
and Slack notifications (later phases) can all consume the same
structured QA result without transformation.

### Alternatives Considered

- Equal weighting across all five categories instead of weighting toward
  tracking/UTM integrity and required information.
- A purely binary pass/fail per rule with no numeric scoring.
- Treating every critical failure as an automatic FAIL rather than a
  PASS-blocking, REVIEW-producing condition.
- Requiring UTMs uniformly across all campaign types regardless of paid
  vs. non-paid status.

### Reasoning

Weighting Tracking & UTMs and Required Campaign Information most heavily
reflects that attribution integrity and basic campaign completeness are
the highest-value things this tool protects against, while still awarding
partial credit for otherwise-launchable campaigns with minor issues.
Separating "critical failure" from the numeric score prevents a
high-scoring campaign from passing while missing a launch-blocking
element (e.g., no campaign owner), without being as punitive as an
automatic FAIL for a single non-fatal omission. Distinguishing paid vs.
non-paid campaigns avoids penalizing organic/email campaigns for lacking
paid-media tracking infrastructure they don't need.

### Consequences

This model becomes the source of truth for the implementation of
`src/constants.py`, `src/validators.py`, and `src/scoring.py` in Sprint 1
(Rule-Based QA Engine) and Phase 2 more broadly. Any future change to
category weights, thresholds, the critical-failure list, or field rules
must be recorded as a new decision entry rather than changed silently in
code. Test cases in [docs/TEST_PLAN.md](../docs/TEST_PLAN.md) must be
written to reflect this specification.

### Status

Accepted

---

## Decision 003

### Decision ID

003

### Date

2026-08-07

### Context

Decision 002 locked category weights (e.g. Tracking & UTMs = 30) but not
per-rule point allocations within each category. Implementing
`src/validators.py` required a concrete points table, plus a rule for what
happens when a check does not apply to a given campaign (e.g. a UTM field
that is optional for a non-paid campaign, or a format check for a field
that was never supplied) — since the task requires that a non-paid
campaign must still be able to reach a perfect score, and that paid-only
checks must never push a category's theoretical maximum above its locked
weight.

### Decision

**Design principle — every rule always fires.** Every validator rule
emits a `ValidationResult` for every campaign it runs against. When a rule
does not apply (UTM presence for a non-paid campaign; a format check for a
field that was never supplied; naming checks when the name itself is
blank; destination-URL checks for a non-paid campaign that didn't supply
one), the rule is reported at full `points_earned` rather than being
omitted. This guarantees the sum of `points_available` per category is
always exactly that category's weight, for every campaign — paid or
non-paid, complete or incomplete — so the category weights from Decision
002 hold as fixed constants rather than varying by submission.

**Amendment (2026-08-07): NOT_APPLICABLE is a distinct status from PASS.**
The original version of this decision reported every "doesn't apply" case
as `ValidationStatus.PASS`. That preserved the scoring math but produced
misleading semantic output — e.g. a non-paid Organic Social campaign would
show as having "passed" `paid_budget` and the paid UTM-required rules,
which were never applicable to it in the first place. `ValidationStatus`
now includes `NOT_APPLICABLE`, and the rules below separate two distinct
"nothing wrong here" outcomes that must not be conflated:

- **`NOT_APPLICABLE`** — the rule genuinely does not apply to this
  campaign because of its *type* (paid vs. non-paid). Used for:
  `paid_budget`, `utm_source_required`, `utm_medium_required`,
  `utm_campaign_required`, `destination_url_required`,
  `destination_url_utms`, and `utm_campaign_alignment` — each *only* on a
  non-paid campaign, and *only* for the "required"/"applicability" half of
  the rule. For the `_required` UTM/destination-URL rules and
  `paid_budget`, this applies unconditionally on a non-paid campaign, even
  if a value happens to be supplied — supplying an optional field doesn't
  retroactively make the requirement apply.
- **`PASS` (with a "not evaluated" message)** — the rule *does* apply to
  this campaign, but there is nothing to evaluate because a prerequisite
  universal field is missing (e.g. campaign name is blank, so the five
  naming-format rules have nothing to check). That missing prerequisite is
  separately reported as its own CRITICAL failure elsewhere; this is not a
  loophole, just this rule declining to double-report it. Per Decision
  002/003, `NOT_APPLICABLE` must never be substituted here — an applicable
  paid rule with missing data must still `FAIL`, and a downstream check on
  a missing *universally required* field stays `PASS`, never
  `NOT_APPLICABLE`.

Format/alignment checks are more granular still: they track the *value*,
not the campaign type. A UTM format check (e.g. `utm_source_format`) is
`NOT_APPLICABLE` only when nothing was supplied *and* it wasn't required
(non-paid + absent). If a non-paid campaign supplies an optional UTM
value, `..._required` is still `NOT_APPLICABLE` (the requirement never
applied) but `..._format` evaluates that value normally (`PASS`/
`WARNING`) — once given, formatting still matters. Example: a non-paid
campaign with `utm_source="FACEBOOK"` produces
`utm_source_required = NOT_APPLICABLE` and
`utm_source_format = WARNING`. The same non-paid campaign with no
`utm_source` at all produces `utm_source_required = NOT_APPLICABLE` and
`utm_source_format = NOT_APPLICABLE`.

Both `NOT_APPLICABLE` and the "not evaluated" `PASS` case award full
`points_earned` equal to `points_available` — this amendment changes
*semantic reporting only* (the status shown to a human or downstream
system), not the scoring mathematics. This is deliberate: it separates
"how many points does this campaign score" (scoring.py's concern, still a
flat sum over `points_earned`) from "what actually happened on this
check, in plain terms" (audit/UI concern). `QAResult.passed_checks` now
excludes `NOT_APPLICABLE` results (only true `PASS` counts as "passed");
a new `QAResult.not_applicable_checks` property surfaces them separately.

**Per-rule point allocations** (`src/constants.py::RULE_POINTS`):

| Category (weight)                  | Rule ID                                  | Points |
|--------------------------------------|-------------------------------------------|-------:|
| Required information (20)            | required_campaign_name                    | 2 |
|                                       | required_campaign_type                    | 2 |
|                                       | required_channel                          | 2 |
|                                       | required_objective                        | 2 |
|                                       | required_target_audience                  | 2 |
|                                       | required_landing_page_url                 | 2 |
|                                       | required_campaign_owner                   | 2 |
|                                       | required_launch_date                      | 2 |
|                                       | required_cta                              | 2 |
|                                       | cta_length                                | 2 |
| URL & destination integrity (20)     | landing_url_format                        | 6 |
|                                       | landing_url_https                         | 4 |
|                                       | destination_url_required                  | 4 |
|                                       | destination_url_format                    | 4 |
|                                       | destination_url_https                     | 2 |
| Tracking & UTMs (30)                 | utm_source_required                       | 6 |
|                                       | utm_medium_required                       | 6 |
|                                       | utm_campaign_required                     | 6 |
|                                       | utm_source_format                         | 2 |
|                                       | utm_medium_format                         | 2 |
|                                       | utm_campaign_format                       | 2 |
|                                       | utm_campaign_alignment                    | 2 |
|                                       | destination_url_utms                      | 4 |
| Naming & governance (15)             | campaign_name_lowercase                   | 3 |
|                                       | campaign_name_no_spaces                   | 3 |
|                                       | campaign_name_characters                  | 3 |
|                                       | campaign_name_underscore_placement        | 3 |
|                                       | campaign_name_consecutive_underscores     | 3 |
| Launch readiness (15)                | launch_date_timing                        | 10 |
|                                       | paid_budget                               | 5 |

Each category's column sums exactly to its Decision 002 weight; the grand
total is 100.

**Rule/category assignment for presence checks:** `landing_page_url` and
`launch_date` presence checks live in `validate_required_fields` (category
`REQUIRED_INFORMATION`), matching the function they're implemented in.
Their *format*/*timing* checks (assuming the field is present) live in
`validate_landing_page_url` and `validate_launch_readiness` respectively,
under `URL_INTEGRITY` and `LAUNCH_READINESS`. `destination_url_utms` (UTM
query-parameter coverage) is scored under `TRACKING_UTMS`, not
`URL_INTEGRITY`, since it validates tracking-parameter presence rather
than URL syntax.

**CTA is split into two rules**, both under `REQUIRED_INFORMATION`:
`required_cta` (presence, in `validate_required_fields`) and `cta_length`
(the 1–60/`>60` length check, in `validate_cta`). `validate_cta` does not
re-check blank/presence — it auto-passes at full points when the CTA is
blank, since `required_cta` already reports that as a critical failure.

**Naming rules are granular** (5 separate rule IDs — lowercase, spaces,
allowed characters, underscore placement, consecutive underscores) rather
than one combined `campaign_name_format` rule, so the future UI can
explain each violation individually.

### Alternatives Considered

- A single combined rule per concern (e.g. one `campaign_name_format` rule
  covering all naming violations at once) instead of granular per-issue
  rules.
- Omitting a `ValidationResult` entirely when a rule doesn't apply,
  instead of emitting an automatic PASS — rejected because it would make
  a category's available points vary by submission, breaking the
  "non-paid campaigns must be able to reach 100" requirement.
- Scoring `destination_url_utms` under `URL_INTEGRITY` instead of
  `TRACKING_UTMS`.
- *(Amendment)* Keeping the original all-`PASS` reporting and instead
  encoding applicability only in the message text — rejected because a
  string is not machine-checkable; a future audit log, dashboard, or
  Slack notification would have no reliable way to distinguish "genuinely
  passed" from "not applicable" without status-based branching.
- *(Amendment)* Making `NOT_APPLICABLE` swallow the "missing universal
  field, nothing to evaluate downstream" case too (e.g. naming checks
  when campaign name is blank) — rejected per the existing Decision 002
  instruction that an applicable field's absence must still surface as a
  `FAIL`, not be reframed as inapplicable.

### Reasoning

The "always fire, auto-pass when not applicable" rule is the only design
that keeps `points_available` per category constant across all campaign
types and field-completeness states without introducing conditional
category weights, which Decision 002 explicitly locked. Splitting CTA
into a presence rule and a length rule keeps `validate_required_fields`
doing presence-only checks (as specified) while giving the CTA validator
sole ownership of the length/warning logic, avoiding duplicate critical
failures for the same blank CTA. Granular naming rule IDs trade a slightly
larger rule count for clearer, individually explainable UI messaging.

*(Amendment)* Reporting scoring mathematics (full points either way) and
semantic meaning (`PASS` vs. `NOT_APPLICABLE`) as two separate concerns
avoids a false choice between "correct denominator" and "honest QA
report" — both are achievable simultaneously once status and points are
decoupled.

### Consequences

`src/scoring.py` can sum `points_earned` directly across all returned
`ValidationResult`s without any category-aware branching or "not
applicable" handling — every campaign's results always total 100 points
available, and this holds regardless of whether a given result's status is
`PASS` or `NOT_APPLICABLE`. Any future change to a rule's point value must
keep each category's column summing to its Decision 002 weight, and should
be recorded as a new decision entry.

*(Amendment)* `critical_failures` (severity `CRITICAL` and status `FAIL`)
is unaffected by this amendment — `NOT_APPLICABLE` results are always
severity `INFO` and can never appear there. Any future Streamlit UI,
Google Sheets audit log, or Slack notification must render `PASS`,
`NOT_APPLICABLE`, `WARNING`, and `FAIL` as visibly distinct outcomes
rather than collapsing `NOT_APPLICABLE` into `PASS` for display
convenience — that collapse is exactly the misleading behaviour this
amendment removes from the data model.

### Status

Accepted

---

## Decision 004

### Decision ID

004

### Date

2026-08-08

### Context

Sprint 3 adds Gemini as a second-stage reviewer that runs after the
deterministic QA engine (Sprint 1/2, Decisions 002/003). This is the
first point where an external, non-deterministic AI service enters a
pipeline that has, until now, been fully deterministic, fully offline,
and fully unit-testable without network access. The integration needed
explicit boundaries before implementation to guarantee it could never
compromise the properties Decisions 002/003 established.

### Decision

**Gemini is advisory only; deterministic QA remains authoritative.**
`src/gemini_analyzer.py::analyze_campaign(campaign, qa_result, *,
client=None)` is a pure consumer of an already-computed `QAResult` — it
never re-validates, never re-scores, never produces a numeric score, and
never produces a PASS/REVIEW/FAIL-shaped value. Its return type,
`GeminiReviewResult`, has no field that could be mistaken for a
governance verdict. The prompt sent to Gemini explicitly states the
deterministic result is context only and explicitly instructs Gemini not
to produce a score or a PASS/REVIEW/FAIL verdict.

**Gemini failures never affect the deterministic result.**
`analyze_campaign()` is contracted to never raise — a client-call
failure, a network error, or a malformed/unparseable structured response
all resolve to `GeminiReviewResult(status=ERROR, error_message=<safe
message>)`, never an exception. In `app.py`, the deterministic
`QAResult` is written to `st.session_state` *before* `analyze_campaign()`
is ever called, and the call itself is additionally wrapped in a
defensive `try/except` even though the contract says it won't raise.
Two independent layers must both fail for a Gemini problem to reach the
user as anything other than the calm "AI review is temporarily
unavailable" message.

**Structured output, not prose parsing.** The Gemini call uses
`google-genai`'s `response_mime_type="application/json"` +
`response_schema` (an explicit JSON-schema dict in
`gemini_analyzer.py::_RESPONSE_SCHEMA`, not the SDK's automatic
Python-type-to-schema conversion) so the expected response shape is
visible in one place and the parsing logic
(`gemini_analyzer.py::_parse_review`) is a small, independently testable
function rather than a prompt-engineering guess at prose extraction.

**`gemini-2.5-flash` is the configurable default model**, loaded as
`config.GEMINI_MODEL` (env var `GEMINI_MODEL`, defaulting to
`gemini-2.5-flash` if unset) and read from `config` at call time rather
than being a literal anywhere else in the codebase — changing models
requires no code change.

**Trigger: automatic, immediately after `score_campaign()` succeeds** —
not a separate "Run AI Review" button. The user submits the campaign
once; the flow is Campaign Form → Deterministic QA → QA Score/Status →
Gemini review → combined results, shown via a `st.spinner("Running AI
review...")` while the call is in flight. Because the call only happens
inside the same `if submitted:` branch that already computes `qa_result`
(see `app.py::main()`), a Streamlit rerun that isn't a new form
submission (e.g. expanding an unrelated expander) never re-triggers a
Gemini call — this was achieved by placement alone, with no caching
layer.

**No new domain concepts were introduced beyond what Decisions 002/003
already define.** `GeminiConcernSeverity` (LOW/MEDIUM/HIGH) is
deliberately a separate enum from `ValidationSeverity`
(INFO/WARNING/CRITICAL) so a qualitative AI judgment can never be
visually or semantically conflated with a deterministic rule outcome —
the UI does not reuse `STATUS_META`'s PASS/REVIEW/FAIL colour styling
anywhere in the AI review section.

### Alternatives Considered

- Letting Gemini also emit a score or verdict as a "second opinion" to
  compare against the deterministic one — rejected: the task scope
  requires the deterministic engine to remain the sole authority, and
  two competing scores would confuse, not help, a marketer.
- Relying on prose output and extracting structured data with regex —
  rejected in favour of the SDK's native structured-output support,
  which is both more reliable and directly requested by the approved
  architecture.
- A manual "Run AI Review" button instead of automatic triggering —
  considered for cost/latency control, but the approved architecture
  specifies a single-submission flow; noted here in case usage patterns
  later warrant revisiting it.
- A dedicated caching layer keyed by campaign content hash — rejected as
  unnecessary: placing the Gemini call inside the same
  submission-triggered branch as the deterministic score already
  prevents redundant calls on unrelated reruns, per Sprint 3's "do not
  build complex caching infrastructure" instruction.

### Reasoning

Every boundary above exists to protect the same invariant: a marketer
must always be able to trust the deterministic score and status exactly
as much after this integration as before it. Making Gemini's types,
prompt, and failure modes structurally incapable of producing a
verdict-shaped output — rather than just instructing it not to and
trusting compliance — means the guarantee holds even if Gemini
occasionally misbehaves or the prompt is refined later.

### Consequences

Any future consumer of `GeminiReviewResult` (a future Slack notification
or Google Sheets log, for instance) inherits the same non-authoritative
framing for free — there is no score or verdict field to accidentally
surface as if it were one. If a future sprint wants Gemini's qualitative
input to actually influence launch decisions (not just inform them),
that would be a new, explicit decision, not an incremental change to
this one. Test coverage for `analyze_campaign()` uses an injected fake
client exclusively (`tests/test_gemini_analyzer.py`); no test in the
suite makes a real network call or requires `GEMINI_API_KEY` to be set.

### Status

Accepted

---
