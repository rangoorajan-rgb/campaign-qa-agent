# Test Plan

This document will define the testing strategy for the Campaign QA & Launch
Governance Agent. It is a template; test cases below describe planned
scenarios only — no tests have been implemented yet. The authoritative
rules these scenarios must exercise are defined in
[project_management/DECISIONS.md](../project_management/DECISIONS.md)
(Decision 002).

## Test Strategy

*To be defined.*

## Functional Tests

Planned scenarios for the rule-based QA engine (Sprint 1), to be
implemented as automated `pytest` tests in
[tests/test_validators.py](../tests/test_validators.py) and
[tests/test_scoring.py](../tests/test_scoring.py):

- A fully complete paid campaign scores 90–100 with no critical failures
  and resolves to PASS.
- A fully complete non-paid campaign without UTMs is not penalized with a
  critical failure and can still resolve to PASS.
- A paid campaign missing `utm_source`, `utm_medium`, or `utm_campaign`
  produces a critical failure and cannot resolve to PASS.
- A paid campaign with a destination URL missing required UTM parameters
  produces a critical failure.
- A paid campaign with budget missing or ≤ 0 produces a critical failure.
- A campaign missing any universally required field (name, type, channel,
  objective, target audience, landing-page URL, owner, launch date, CTA)
  produces the corresponding critical failure.
- A campaign with a malformed landing-page URL produces a critical
  failure.
- A campaign with a launch date in the past produces a critical failure.
- A campaign scoring 90–100 with at least one critical failure resolves
  to REVIEW, not PASS.
- A campaign scoring 70–89 resolves to REVIEW regardless of critical
  failures.
- A campaign scoring 0–69 resolves to FAIL.
- Warnings (HTTP landing page, uppercase/spaces in name or UTMs,
  malformed naming convention, `utm_campaign`/name mismatch, launch date
  under 2 days away, CTA over 60 characters) reduce the relevant category
  score without producing a critical failure.
- Campaign name normalisation correctly converts a human-entered name
  (e.g., `"UK Enterprise Demo Q3 2026"`) to its comparable form
  (`"uk_enterprise_demo_q3_2026"`) for `utm_campaign` matching.

## Integration Tests

*To be defined — deferred until Make, Google Sheets, and Slack
integrations exist (Phases 5–7).*

## User Acceptance Tests

*To be defined.*

## Edge Cases

- Score of exactly 90 with zero critical failures (boundary of PASS).
- Score of exactly 90 with one critical failure (must be REVIEW, not
  PASS).
- Score of exactly 89 and exactly 70 (REVIEW boundaries).
- Score of exactly 69 (FAIL boundary).
- CTA of exactly 60 characters (normal) vs. 61 characters (warning).
- CTA that is present but whitespace-only (must be treated as blank —
  critical failure).
- Launch date exactly 2 days away vs. 1 day away (warning boundary).
- Campaign name with consecutive underscores, a leading underscore, or a
  trailing underscore.
- Campaign name that is already lowercase and correctly formatted
  (no warnings triggered).
- Non-paid campaign that supplies UTM values with spaces or uppercase
  characters (must still be validated and produce warnings).
- Landing-page URL with a valid scheme but missing host/domain
  (malformed — critical failure).
- Landing-page URL using HTTP (warning, not critical).

## Regression Tests

*To be defined — will cover previously fixed defects once Sprint 1
implementation begins.*
