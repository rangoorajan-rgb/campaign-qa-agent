# Master Project Plan

## Project Overview

Campaign QA & Launch Governance Agent — an internal Marketing Operations
tool that validates marketing campaigns before launch.

## Business Problem

Marketing teams frequently launch campaigns with preventable errors such as
missing or malformed UTMs, invalid destination URLs, inconsistent naming
conventions, incomplete campaign information, missing ownership, poor
launch readiness, and other tracking/governance issues. The purpose of the
application is to provide Marketing Operations with a structured pre-launch
QA process. The system will combine deterministic validation rules with
later AI-assisted qualitative analysis.

## Vision

Create a practical internal Marketing Operations governance tool that
reduces preventable campaign launch errors and creates a repeatable QA
process.

## Objectives

- Standardise campaign QA before launch.
- Catch tracking and configuration problems early.
- Reduce manual QA effort.
- Create consistent campaign governance.
- Produce an auditable record of campaign checks.
- Demonstrate realistic Marketing Operations, automation, AI and software
  engineering skills.

## Success Criteria

The finished prototype should be able to:

- Accept campaign information through a usable interface.
- Apply deterministic validation rules.
- Produce a 0–100 QA score.
- Assign PASS, REVIEW or FAIL status.
- Prevent PASS when critical failures exist.
- Explain failed checks and recommended fixes.
- Perform qualitative AI review using Gemini.
- Send completed results to Make.
- Log campaign QA results in Google Sheets.
- Send useful Slack notifications.
- Handle invalid input and API/integration failures gracefully.
- Include automated tests and documented manual test scenarios.

## Target Users

- Marketing Operations Managers
- Marketing Operations Executives
- Demand Generation Managers
- Performance Marketing Managers
- Campaign Managers
- Digital Marketing Managers

## Stakeholders

*To be defined.*

## Scope

Included in this portfolio version:

- Campaign submission
- Deterministic validation
- Scoring
- Streamlit UI
- Gemini qualitative analysis
- Make webhook
- Google Sheets audit log
- Slack notifications
- Testing
- Documentation

## Out of Scope

Out of scope for this portfolio version:

- Direct publishing to ad platforms
- Modifying live campaigns
- Real CRM integration
- Enterprise authentication / SSO
- Database infrastructure
- Automated media buying
- Production hosting at enterprise scale

## Functional Requirements

At a high level, the system is expected to:

- Accept campaign submission data (name, URLs, UTM parameters, ownership,
  launch details, and related metadata) through a Streamlit form.
- Run deterministic validation rules against the submitted campaign,
  covering required fields, URL validity, UTM structure, naming
  conventions, launch readiness, and CTA presence.
- Distinguish validation logic for paid vs. non-paid campaigns where
  applicable.
- Calculate a weighted QA score (0–100) from validation results.
- Assign a final status of PASS, REVIEW, or FAIL, with critical failures
  always preventing a PASS regardless of overall score.
- Present explanations of failed or flagged checks, with recommended
  fixes.
- Submit the final result to Gemini for a supplementary qualitative
  review.
- Send the completed result to a Make.com webhook.
- Log the QA outcome to a Google Sheets audit log.
- Send a Slack notification summarizing the result.
- Handle invalid input and integration/API failures without crashing the
  application.

These requirements describe planned functionality only; none is
implemented at this stage.

The concrete deterministic scoring model (category weights, PASS/REVIEW/
FAIL thresholds, critical-failure override, and the full validation
ruleset for naming, UTMs, URLs, CTAs, and campaign ownership) is locked
and documented in
[project_management/DECISIONS.md](DECISIONS.md) (Decision 002), which is
the source of truth for this logic — not duplicated here.

## Non-functional Requirements

- **Maintainability** — code should be organized into clear, single-
  purpose modules that are easy to extend as rules evolve.
- **Modularity** — the QA engine, scoring, AI analysis, and integrations
  should be independently testable and loosely coupled.
- **Security of API keys** — credentials (Gemini, Make, Slack) must never
  be committed to the repository and must be loaded from environment
  variables.
- **Explainability** — QA results must clearly state which checks failed
  or passed and why.
- **Reliability** — the QA engine's deterministic checks must produce
  consistent, repeatable results for the same input.
- **Graceful error handling** — invalid input and integration failures
  (Gemini, Make, Slack, Google Sheets) should be handled without crashing
  the application.
- **Usability** — the Streamlit interface should be understandable to
  non-technical Marketing Operations users.
- **Testability** — core logic (validation, scoring) should be testable
  independently of the Streamlit UI and external integrations.

## Architecture Overview

See [docs/architecture.md](../docs/architecture.md).

Planned future architecture:

```
Streamlit form
    ↓
Python rule-based QA engine
    ↓
QA scoring
    ↓
Gemini qualitative review
    ↓
Final PASS / REVIEW / FAIL result
    ↓
Make.com webhook
    ↓
Google Sheets audit log
    ↓
Slack notifications
```

## Technology Stack

- Python
- Streamlit
- google-genai
- Make.com
- Google Sheets
- Slack
- pytest
- Git / GitHub

## Development Phases

1. Repository bootstrap
2. Rule-based QA engine
3. Streamlit application
4. Gemini AI analysis
5. Make integration
6. Google Sheets logging
7. Slack notifications
8. Testing
9. Documentation/polish
10. GitHub release

See [docs/roadmap.md](../docs/roadmap.md) for full phase descriptions.

## Product Backlog

Tracked per-sprint in [CURRENT_SPRINT.md](CURRENT_SPRINT.md) as the
project progresses.

## Risks

- **AI inconsistency** — Gemini's qualitative review may produce varying
  output for similar inputs across runs.
- **API limits** — Gemini, Make, and Slack integrations are subject to
  rate limits and quota constraints.
- **False positives/negatives** — deterministic rules may incorrectly
  flag valid campaigns or miss genuinely invalid ones.
- **Hard-coded governance assumptions** — naming conventions and required
  fields are based on assumed conventions that may not generalize to all
  organizations.
- **Integration failures** — Make, Google Sheets, or Slack integrations
  may fail or become unavailable, and must not block core QA
  functionality.
- **Data privacy** — campaign data submitted for QA may contain
  business-sensitive information that must be handled appropriately,
  particularly when sent to external AI or automation services.
- **Dependency changes** — external SDKs (e.g., `google-genai`) and
  third-party services may change their APIs in ways that break
  integrations.

## Future Improvements

*To be defined.*

## Lessons Learned

*To be defined.*
