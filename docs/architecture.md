# Architecture

## Why This Project Exists

Marketing campaigns are frequently launched with preventable errors: broken
or missing UTM parameters, invalid URLs, inconsistent naming, and missing
required metadata. These issues are typically caught manually, if at all,
and often only after a campaign has gone live — by which point attribution
data may already be compromised.

The Campaign QA & Launch Governance Agent exists to move this validation
earlier in the process, replacing ad-hoc manual review with a consistent,
repeatable, and auditable QA step that runs before a campaign launches.

## High-Level Architecture

The system is planned around a small set of cooperating components rather
than a single monolithic application:

- **QA Engine** — Applies a defined set of governance rules to campaign
  data (naming conventions, required fields, UTM parameter structure, URL
  validity) and produces a structured result.
- **AI Analysis Layer** — Supplements rule-based checks with Gemini-powered
  analysis for issues that are difficult to express as static rules, such
  as naming consistency or contextual anomalies.
- **Application Layer** — A Streamlit interface through which campaigns are
  submitted for review and QA results are displayed.
- **Automation Layer** — Make (Integromat) workflows that connect the QA
  process to the tools marketing teams already use.
- **Logging Layer** — Google Sheets used as a persistent, shareable record
  of QA runs and outcomes.
- **Notification Layer** — Slack webhooks used to alert stakeholders of QA
  results and launch blockers.

These components are described here at a conceptual level. The QA Engine
(deterministic validation and scoring) is implemented; the AI Analysis,
Application, Automation, Logging, and Notification layers are not yet
built and will be introduced incrementally, as described in
[roadmap.md](roadmap.md).

### QA Engine Validation Model

At a conceptual level, the QA engine applies a fixed set of weighted
governance categories (tracking/UTMs, required campaign information,
URL/destination integrity, naming/governance, and launch readiness) to
produce a 0–100 score, alongside individually severity-tagged results per
rule (informational, warning, or critical). Campaign status (PASS,
REVIEW, or FAIL) is derived from the score together with a
critical-failure override, so that a high score alone cannot mask a
launch-blocking omission. Paid and non-paid campaigns are subject to
different tracking requirements, reflecting that not all channels carry
the same attribution needs.

The exact weights, thresholds, and rule definitions are governance
decisions, not architecture, and are recorded as the project's source of
truth in
[project_management/DECISIONS.md](../project_management/DECISIONS.md)
(Decision 002) rather than here.

## Future Workflow

The intended end-to-end workflow, once fully implemented, is expected to
look approximately as follows:

1. A campaign's metadata is submitted for review, either through the
   Streamlit interface or via an automated trigger.
2. The QA engine validates the campaign against governance rules.
3. Where applicable, the AI analysis layer reviews the campaign for issues
   not captured by static rules.
4. Results are logged to Google Sheets for record-keeping and audit.
5. A Slack notification is sent summarizing the outcome and flagging any
   blockers that require attention before launch.
6. Make automation connects this workflow to upstream and downstream
   marketing tools as needed.

This workflow will be refined as each phase of the roadmap is implemented.
