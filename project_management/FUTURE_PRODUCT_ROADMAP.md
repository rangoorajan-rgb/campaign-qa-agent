# Future Product Roadmap

This document exists so that whoever returns to this repository later —
possibly a future version of the same team, possibly someone else
entirely — can pick it back up without having to reconstruct intent from
code alone. It draws a hard line between what this project **is today**
(a working portfolio MVP) and what it **could become** (a full Campaign
Governance Platform), so neither gets mistaken for the other.

Nothing in this document is a commitment or a current task. It is a
preserved product vision, written at a stopping point, for a future
resumption of work.

---

## 1. Current MVP (Implemented)

The following capabilities genuinely exist in this repository today and
are covered by the automated test suite:

- **Deterministic campaign QA engine** (`src/validators.py`) — rule-based
  validation of required fields, URL/destination integrity, UTM
  structure, naming conventions, and launch readiness, for both paid and
  non-paid campaign types.
- **Weighted governance scoring** (`src/scoring.py`, `src/constants.py`)
  — a fixed, documented points allocation (`CATEGORY_WEIGHTS`,
  `RULE_POINTS`) that always sums to 100, producing a 0–100 governance
  score from the validation results.
- **PASS / REVIEW / FAIL decision** (`src/scoring.py`) — deterministic
  status derived from the score plus a critical-failure override, so a
  high score alone can never mask a launch-blocking omission.
- **Streamlit campaign submission interface** (`app.py`,
  `src/ui_helpers.py`) — a form-based UI for submitting a campaign and
  viewing its QA result, category breakdown, and flagged issues.
- **Gemini qualitative campaign review** (`src/gemini_analyzer.py`) — an
  advisory-only, second-stage AI review that runs after the deterministic
  result exists; it never produces a score or a verdict, and a Gemini
  failure never affects the deterministic result.
- **Make webhook event publishing** (`src/webhook.py`) — a
  `campaign.qa.completed` event delivered to a configured Make scenario
  as a side effect after QA and Gemini both complete, with retry logic
  and complete failure isolation from the governance result. Verified
  end-to-end against a live Make scenario.
- **Google Sheets audit logging via Make.com** — implemented and
  manually verified end-to-end; this integration currently lives in the
  external Make scenario rather than in repository application code. The
  live workflow is Streamlit Campaign QA → deterministic QA → Gemini
  qualitative review → Make custom webhook → Google Sheets "Add a Row" →
  Campaign QA Audit Log. Verification confirmed the webhook received
  `campaign.qa.completed`, the Add a Row module's field mapping executed
  successfully, and a real row was written containing campaign name,
  campaign type, channel, score, status, critical-failure count, warning
  count, campaign owner, AI status, AI summary, and recommendation.
- **Slack notifications via Make.com** — implemented and manually
  verified end-to-end; like Google Sheets logging, this integration
  lives in the external Make scenario rather than in repository
  application code. It is the final step of the same Make scenario,
  triggered immediately after the Google Sheets row is written
  successfully. The live workflow is Streamlit Campaign QA →
  deterministic QA → Gemini qualitative review → Make custom webhook →
  Google Sheets "Add a Row" → Slack notification. Verification confirmed
  a message posted to the `#campaign-qa` channel (observed in the
  TaskFlowAI workspace) containing campaign name, campaign owner,
  channel, QA score, QA status, critical-failure count, warning count,
  AI summary, and AI recommendation, with no regression to Google Sheets
  logging or any earlier pipeline stage.
- **Automated pytest suite** — 162 passing tests across models,
  validators, scoring, the sample dataset, Gemini (fake-client), and the
  webhook (fake-client), none of which make real network calls.
- **Documented architecture and decision records** —
  `docs/architecture.md`, `project_management/MASTER_PROJECT_PLAN.md`,
  and `project_management/DECISIONS.md` (Decisions 001–005), which
  record not just what was built but why, and what alternatives were
  rejected.

### A note on where this MVP actually lives

Not all of the current MVP is Python application code. Google Sheets
audit logging and Slack notifications are both implemented entirely as
configuration inside the same external Make.com scenario (webhook
trigger → "Add a Row" module → Slack message module) — there is no
Google Sheets or Slack integration in `src/`, and no related dependency
in `requirements.txt`. That is expected: `src/webhook.py` only publishes
`campaign.qa.completed`; what Make does with that event afterward,
including chaining Slack after the Sheets write, is external
infrastructure, not repository code.

This means **inspecting `src/` alone is not sufficient to know the full
current MVP.** Some capabilities are implemented and verified, but
configured entirely outside this codebase. `docs/roadmap.md` (Phases 6
and 7) still describes Google Sheets logging and Slack notifications as
planned *repository* integrations and has not been updated to reflect
that the same outcomes already exist via Make — that document describes
the originally planned build sequence, not the current
external-automation state, and the two have diverged here.

---

## 2. Product Vision

The long-term vision for this project is a **Campaign Governance
Platform**: a system that helps Marketing Operations teams govern
campaign launches across the full lifecycle — submission, QA, review,
approval, audit, and operational reporting — not just a one-shot QA
check. The current MVP implements the first slice of that lifecycle
(submission through QA and advisory review) end-to-end and well; the
phases below describe how the rest of the lifecycle could be built out,
if and when there's a reason to.

---

## 3. Future Phases

### Phase 2 — Operational Workflow

Extends the QA result from something a marketer reads once into
something the organisation acts on.

Potential capabilities:

- Microsoft Teams notifications
- Configurable notification rules
- PASS / REVIEW / FAIL routing
- Campaign-owner alerts
- Approval requests
- Approval / rejection decisions
- Escalation workflows
- Improvements to the existing Google Sheets audit log, such as:
  - Richer audit history
  - Additional logged fields
  - A durable database replacement for the spreadsheet
  - Workflow branching based on logged events

### Phase 3 — Productisation

Turns a single-user tool into a multi-user product.

Potential capabilities:

- Persistent database instead of relying only on Google Sheets
- Campaign history
- Campaign detail pages
- Configurable governance rules
- Organisation-specific naming conventions
- Reusable campaign templates
- User accounts
- Teams
- Roles / permissions
- Reviewer / approver roles
- Campaign ownership
- Workflow state management

### Phase 4 — Marketing Technology Integrations

Potential integrations:

- HubSpot
- Salesforce
- Marketo
- Google Ads
- Meta Ads
- LinkedIn Campaign Manager
- Jira
- Asana
- Monday.com
- Notion

These integrations would let campaign metadata be pulled from or pushed
into the operational systems Marketing Operations teams already use,
rather than relying entirely on manual entry into this tool's form —
turning it from a standalone checkpoint into a connected step in an
existing workflow.

### Phase 5 — Governance Intelligence

Potential capabilities:

- Historical governance trends
- Recurring failure analysis
- Most common campaign QA issues
- Failure patterns by channel
- Failure patterns by campaign type
- Team / owner trends
- AI-assisted remediation suggestions
- Policy adherence insights
- Governance health metrics

This phase is deliberately **not** a generic marketing analytics
platform. Every capability here is about campaign governance and
operational quality — what's failing, why, how often, and for whom —
not campaign performance, spend efficiency, or attribution, which are
different problems this product does not aim to solve.

### Phase 6 — Production Readiness

Potential capabilities:

- Hosted production deployment
- Authentication
- Authorization
- Database migrations
- Secrets management
- API rate limiting
- Retry queues
- Background jobs
- Structured application logging
- Error monitoring
- Observability
- Security review
- Privacy review
- Configurable data retention
- Backup / recovery
- CI/CD
- Production tests

---

## 4. Product Development Principles

These rules apply to every future phase above, regardless of which one
is picked up first:

- Deterministic governance remains authoritative.
- AI remains advisory unless explicitly redesigned through a future
  architecture decision.
- External integration failure must not corrupt governance results.
- New capabilities should solve a real operational problem.
- Avoid adding features simply because they are technically possible.
- Each future phase should have its own architecture/design review
  before implementation.
- Portfolio MVP and production product are different maturity levels.
- Security, privacy, and maintainability requirements increase
  substantially once the system becomes multi-user or production-facing.

---

## 5. Non-Goals for the Current MVP

The following are explicitly **not required** for the current portfolio
version. Their absence is a scope boundary, not unfinished work:

- Authentication
- Multi-user support
- Production database
- Billing
- Enterprise permissions
- Full analytics suite
- Direct ad-platform publishing
- Approval engine
- Production-scale infrastructure

---

## 6. Return-to-Project Checklist

When development on this project resumes:

1. Re-read `MASTER_PROJECT_PLAN.md`
2. Re-read `DECISIONS.md`
3. Review current architecture and dependencies
4. Verify all tests still pass
5. Review this `FUTURE_PRODUCT_ROADMAP.md`
6. Select only **one** next product phase/capability
7. Write architecture before implementation
8. Update `CURRENT_SPRINT.md`
9. Implement, test, manually verify, document, and commit
