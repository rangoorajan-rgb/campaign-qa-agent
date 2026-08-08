# Current Sprint

## Sprint Number

4

## Sprint Name

Make Webhook Integration

## Sprint Goal

Add a Make webhook as a third, side-effect-only pipeline stage that
delivers the completed QA result (deterministic + Gemini) to a Make
scenario for downstream workflow automation, without touching the
deterministic engine or Gemini's behaviour.

## Current Status

Completed

## Tasks To Complete

*None — Sprint 4 is complete.*

## Completed Tasks

- **Live Make verification (human-performed, 2026-08-08):**
  `MAKE_WEBHOOK_URL` configured locally in `.env`; a Make Custom Webhook
  scenario was created and run in "Run once" mode; the Streamlit app was
  started and the "Clean Paid Search" example was submitted; deterministic
  QA returned 100/PASS, Gemini's qualitative review completed, and the
  UI showed the "Sent to Make" caption. Make's execution history recorded
  1 live operation with a payload containing `event` =
  `campaign.qa.completed`, `event_id`, `sent_at`, `campaign`, `qa_result`
  (including `category_breakdown`), and `ai_review` (`summary`,
  `concerns` array, `recommendation`). No API key or secret appeared in
  the payload. End-to-end delivery confirmed working against a real
  Make scenario, not just the fake-client test suite.

- Domain models — `src/models.py`: added `WebhookDeliveryStatus`
  (SENT/NOT_CONFIGURED/ERROR) and `WebhookDeliveryResult`. Named
  generically (not Make-specific) so a future Slack integration can
  reuse the same result type. Purely additive; no existing model changed
- Config — `config.py`: loads `MAKE_WEBHOOK_URL`,
  `MAKE_WEBHOOK_TIMEOUT_SECONDS` (default `5`), and
  `MAKE_WEBHOOK_MAX_ATTEMPTS` (default `2`) from the environment;
  `.env.example` documents all three
- Webhook module — `src/webhook.py` implemented:
  `send_to_make(qa_result, gemini_review_result, *, client=None, now=None)
  -> WebhookDeliveryResult`. Builds the `campaign.qa.completed` payload,
  posts it via `requests` with retry logic, and never raises — every
  outcome resolves to a valid `WebhookDeliveryResult`
- Event identity — one `event_id` (UUID4) and one `sent_at` (UTC ISO
  8601, injectable via `now`) are generated once per call, before the
  retry loop, and reused unchanged across every attempt belonging to
  that call
- Retry logic — up to `MAKE_WEBHOOK_MAX_ATTEMPTS` attempts (default 2),
  ~1s fixed delay between attempts. Retries on `ConnectionError`,
  `Timeout`, and HTTP 5xx; never retries HTTP 4xx (resolves to `ERROR`
  in one attempt)
- Logging — `logger.exception(...)` only for real caught exceptions
  (`ConnectionError`/`Timeout`/unexpected `Exception`);
  `logger.warning(...)` for retryable 5xx responses; `logger.error(...)`
  for terminal 4xx responses. Full `MAKE_WEBHOOK_URL` is never logged
- Tests — `tests/test_webhook.py`, 24 tests, all using an injected fake
  HTTP client (no real network calls, no `MAKE_WEBHOOK_URL` required to
  run the suite): successful delivery + exact payload shape (event name,
  campaign fields, full deterministic QA block, full Gemini `concerns`
  array, excluded-field absence), `NOT_CONFIGURED`, retry-then-succeed
  (connection error and 5xx), retry-exhausted, single-attempt 4xx,
  `event_id`/`sent_at` validity and stability across retries, injectable
  timestamp, configured timeout reaching the HTTP client, non-propagation
  of unexpected exceptions, and non-mutation of both `QAResult` and
  `GeminiReviewResult`. Retry-delay sleeps are patched out so the suite
  stays fast
- Streamlit integration — `app.py`: `send_to_make()` is called
  automatically inside the same `if submitted:` branch, after
  `gemini_review_result` is computed, wrapped in
  `st.spinner("Sending to Make...")`; both `qa_result` and
  `gemini_review_result` are already in `st.session_state` before the
  call, and the call itself is wrapped in a defensive `try/except`. New
  `render_webhook_status()` renders nothing for `NOT_CONFIGURED`, a small
  `st.caption` "Sent to Make" for `SENT`, and a small calm caption for
  `ERROR` — never a prominent box
- Full regression run — all 162 tests pass (138 pre-Sprint-4 + 24 new)
- Streamlit startup smoke test — `streamlit run app.py` launched
  headlessly and served HTTP 200 with no errors, then stopped (no real
  webhook call occurs without a configured `MAKE_WEBHOOK_URL`, so this
  is safe to run in this environment)
- Documentation — added Decision 005 to `DECISIONS.md`; updated this
  document; updated `README.md` to note Make integration is implemented

## Technical Notes

- New files: `tests/test_webhook.py`. `src/webhook.py` was implemented
  (was a docstring stub). `src/models.py` and `config.py` were extended,
  not rewritten. `app.py` was extended with webhook wiring on top of its
  Sprint 2/3 code, which is otherwise unchanged.
- **Not touched:** `src/validators.py`, `src/scoring.py`,
  `src/constants.py`, `src/gemini_analyzer.py`, `CATEGORY_WEIGHTS`,
  `RULE_POINTS`, and every Sprint 1/2/3 test file — per this sprint's
  explicit constraint.
- See [DECISIONS.md](DECISIONS.md), Decision 005, for the full webhook
  contract: event identity semantics (stable `event_id`/`sent_at` across
  retries), the payload allowlist and what's deliberately excluded, the
  precise ~11-second worst-case latency (5s timeout + 1s retry delay +
  5s timeout — documented accurately, not rounded down), and the
  exception-vs-HTTP-status logging distinction.
- A local `.env` with a real `MAKE_WEBHOOK_URL` was configured for live
  verification (2026-08-08). The automated smoke test earlier in this
  sprint ran before that, against the `NOT_CONFIGURED` path only — both
  states have now been exercised, one by the automated suite/smoke test
  and one by human live verification.

## Known Issues

*None. Live verification against a real Make scenario succeeded with no
issues found — see the live-verification entry under Completed Tasks.*

## Blockers

*None.*

## Next Session Starting Point

Sprint 4 is complete. Sprint 5 has not yet been scoped — per the
roadmap, Google Sheets audit logging and Slack notifications remain the
next planned integrations, but which comes first, and its exact goal and
task list, is a planning decision for the next session, not assumed
here.

## Definition of Done

- [x] Webhook runs automatically after QA and Gemini already exist, in
      a single user submission
- [x] Deterministic QA remains authoritative; webhook failure cannot
      change score, status, or Gemini's result
- [x] `event_id` and `sent_at` are stable across retries within one
      logical delivery
- [x] Retries apply only to connection errors, timeouts, and HTTP 5xx;
      HTTP 4xx is never retried
- [x] `MAKE_WEBHOOK_TIMEOUT_SECONDS`/`MAKE_WEBHOOK_MAX_ATTEMPTS` are
      configurable via environment variable, not hard-coded
- [x] No secrets, raw prompt text, stack traces, `budget`, or
      `campaign_message` appear in the payload
- [x] No test makes a real network request; all 162 tests pass
- [x] `src/validators.py`, `src/scoring.py`, `src/constants.py`, and
      `src/gemini_analyzer.py` are unmodified
- [x] **A human has manually verified delivery against a real Make
      scenario** — confirmed 2026-08-08; 1 live operation received with
      the expected payload shape and no secrets present

## Sprint Retrospective

### What Was Achieved

Sprint 4 added Make webhook delivery as a third, side-effect-only stage
after the deterministic QA engine and Gemini's qualitative review, with
the same failure-isolation guarantees already established for Gemini in
Decision 004: the webhook cannot change a score, a status, or hide
either upstream result, and every outcome (sent, unconfigured, or
error-after-retries) resolves to a typed `WebhookDeliveryResult` rather
than an exception. The payload contract (`campaign.qa.completed`, a
stable `event_id`/`sent_at` reused across retries, an explicit
field allowlist excluding `budget`/`campaign_message`/secrets/raw
prompt text) was locked in Decision 005 before implementation, then
verified end-to-end against a real Make scenario — not just the 24-test
fake-client suite.

### Lessons Learned

- Generating `event_id`/`sent_at` once per logical call (not per HTTP
  attempt) was worth locking in as an explicit architectural decision
  before writing any retry code — it would have been an easy, subtle
  mistake to generate a fresh ID per attempt, which would have silently
  broken the exact idempotency/audit-tracing property the field exists
  to provide.
- Distinguishing `logger.exception(...)` (real caught exceptions) from
  `logger.warning`/`logger.error` (HTTP status-code failures that are
  not exceptions) was a small but genuine correctness issue worth
  getting right — fabricating a traceback for a normal HTTP 4xx/5xx
  response would have made logs actively misleading during real
  incident debugging.
- Live verification caught nothing the fake-client test suite had
  missed, which is itself a useful signal: the dependency-injection
  pattern used consistently since Gemini (Decision 004) — a fake client
  matching the real client's exact call shape — continues to be a
  reliable substitute for the real integration, not just a convenient
  test double.

### Preparation for Sprint 5

The QA pipeline through Sprint 4 is: `CampaignSubmission` →
`validate_campaign()`/`score_campaign()` (deterministic, authoritative)
→ `analyze_campaign()` (Gemini, advisory) → `send_to_make()` (webhook,
side effect). Any future Google Sheets or Slack integration can follow
the exact same shape established twice now (Decisions 004 and 005):
read already-computed results without mutating them, never raise, return
a typed result object, and isolate failures behind at least the same
two independent layers (session-state-before-call, plus a defensive
`try/except` in `app.py`). `WebhookDeliveryResult`/`WebhookDeliveryStatus`
were deliberately named generically rather than Make-specific, so a
future Slack notification can likely reuse them as-is rather than
introducing a near-duplicate type.
