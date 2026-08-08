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

In progress — implementation complete and the full automated suite
passes; live verification against a real Make scenario (with a real
`MAKE_WEBHOOK_URL` configured) by a human is still required before this
sprint can be marked done.

## Tasks To Complete

- Manual live verification — configure a real Make scenario and
  `MAKE_WEBHOOK_URL`, submit a campaign, and confirm Make actually
  receives the `campaign.qa.completed` payload with the expected shape
  (see Next Session Starting Point for the exact steps)

## Completed Tasks

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
  document; updated `README.md` to note Make integration is in progress

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
- No `.env` file exists in this development environment, so
  `MAKE_WEBHOOK_URL` is unset locally — the Streamlit smoke test exercises
  the `NOT_CONFIGURED` path only (silent, no UI output), until a real
  webhook URL is supplied.

## Known Issues

*None identified in automated testing. The `SENT`/retry paths have only
been exercised against a fake client in tests — delivery to a real Make
scenario has not yet been verified. Record any issues found during live
testing here.*

## Blockers

*None.*

## Next Session Starting Point

1. Create a Make scenario with a "Custom webhook" trigger module; copy
   its webhook URL.
2. Add `MAKE_WEBHOOK_URL=<that URL>` to a local `.env` file (copy from
   `.env.example` if no `.env` exists yet).
3. Run `python -m streamlit run app.py`, submit a real campaign, and
   confirm: a "Sending to Make..." spinner appears, a "Sent to Make"
   caption appears afterward, and the Make scenario's execution history
   shows a received `campaign.qa.completed` payload matching the shape
   documented in Decision 005.
4. Optionally test the failure path (e.g. temporarily point
   `MAKE_WEBHOOK_URL` at an invalid host) and confirm the calm "Could not
   deliver to Make — QA result above is unaffected." caption appears,
   with the QA result and AI review sections completely unaffected.
5. Once verified, update this document's Current Status to "Completed"
   and add a Sprint Retrospective (see Sprint 1's entry for the expected
   format).

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
- [ ] **A human has manually verified delivery against a real Make
      scenario** — pending, blocks marking this sprint complete
