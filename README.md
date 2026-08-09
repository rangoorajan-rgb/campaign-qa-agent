# Campaign QA & Launch Governance Agent

## Overview

Marketing teams frequently launch campaigns with preventable errors —
broken UTM parameters, invalid tracking URLs, inconsistent naming, or
missing governance information — that go unnoticed until after launch,
by which point attribution and reporting are already compromised. The
Campaign QA & Launch Governance Agent is an internal Marketing
Operations tool that runs a structured, deterministic pre-launch quality
check across campaign setup, tracking, naming, and launch readiness,
producing a governance score and a clear PASS/REVIEW/FAIL outcome before
a campaign goes live. It is used by Marketing Operations Managers,
Campaign Managers, and Performance Marketing teams who need a fast,
consistent way to catch these issues before they reach production.

## Current Project Status

## Completed

- Repository setup
- Deterministic QA engine
- Streamlit dashboard
- Gemini AI qualitative review
- Make webhook automation
- Google Sheets audit logging (via Make.com)
- Slack notifications (via Make.com)
- Automated test suite

## Planned

*None currently in progress. See
[project_management/FUTURE_PRODUCT_ROADMAP.md](project_management/FUTURE_PRODUCT_ROADMAP.md)
for possible future product directions.*

## Screenshots

### Campaign Setup

(Add screenshot)

### Validation Results

(Add screenshot)

### PASS Example

(Add screenshot)

### FAIL Example

(Add screenshot)

## Demo Workflow

```
Campaign Setup
      ↓
Validate Campaign
      ↓
Governance Score
      ↓
Review Issues
      ↓
Launch Decision
```

1. **Campaign Setup** — Enter campaign details, tracking parameters,
   launch details, and messaging into the Streamlit form.
2. **Validate Campaign** — Submit the form to run the deterministic QA
   engine against the campaign.
3. **Governance Score** — Review the overall score, PASS/REVIEW/FAIL
   status, and a category-by-category breakdown.
4. **Review Issues** — Work through any critical issues and warnings,
   each with a specific recommendation.
5. **Launch Decision** — Once the campaign reaches a PASS status (or
   flagged issues have been resolved), proceed with launch.

## Business Problem

Marketing teams frequently launch campaigns with preventable issues, including:

- Broken or missing UTM parameters
- Invalid URLs
- Inconsistent campaign naming conventions
- Missing required campaign information
- Tracking mistakes that compromise attribution and reporting
- Poor overall launch governance

These issues are often caught late — after a campaign is already live —
resulting in lost data, incorrect reporting, and wasted ad spend.

## Objectives

- Provide a consistent, automated way to validate campaigns before launch
- Reduce tracking and attribution errors caused by manual QA
- Establish clear, enforceable campaign naming and tagging standards
- Create an auditable record of campaign QA checks over time
- Integrate QA checks into existing marketing operations workflows

## Architecture

The application is composed of the following components:

- A **rule-based QA engine** that validates campaign data against defined
  governance rules (naming conventions, required fields, UTM structure,
  URL validity) and produces a deterministic 0–100 score and PASS/REVIEW/
  FAIL status — **implemented** (`src/validators.py`, `src/scoring.py`)
- A **Streamlit application** providing a user interface for submitting
  and reviewing campaign QA results — **implemented** (`app.py`,
  `src/ui_helpers.py`)
- **Gemini AI-assisted analysis** for more nuanced review beyond static
  rules (e.g., naming consistency, contextual anomalies) — **implemented**
  (`src/gemini_analyzer.py`), runs automatically after the deterministic
  QA engine as an advisory-only qualitative review
- **Automation via Make (Integromat)** to connect the QA process to
  existing marketing tools and workflows — **implemented**
  (`src/webhook.py`), delivers the completed QA result to a Make scenario
  as a side effect after QA and Gemini both complete; verified end-to-end
  against a live Make scenario
- **Google Sheets logging** to maintain a persistent, shareable audit trail
  of QA results — **implemented via Make.com** (a "Google Sheets — Add a
  Row" module in the same Make scenario the webhook triggers, not
  repository Python code); each row records campaign name, campaign
  type, channel, score, status, critical-failure count, warning count,
  campaign owner, AI status, AI summary, and recommendation
- **Slack notifications** to alert stakeholders of QA results and launch
  blockers — **implemented via Make.com** as the final operational step,
  triggered immediately after the Google Sheets row is written; posts to
  the `#campaign-qa` channel with campaign name, campaign owner, channel,
  QA score, QA status, critical-failure count, warning count, AI
  summary, and AI recommendation. Verified end-to-end (Streamlit → QA
  Engine → Gemini → Make Webhook → Google Sheets → Slack)

Google Sheets logging and Slack notifications are both configured
entirely within the external Make scenario, not in this repository's
Python code — `src/webhook.py` only publishes the `campaign.qa.completed`
event; everything downstream of that is Make automation.

See [docs/architecture.md](docs/architecture.md) for further detail and
[docs/roadmap.md](docs/roadmap.md) for the phased build plan.

## Technology Stack

| Area              | Technology                  |
|-------------------|------------------------------|
| Language          | Python 3.11+                 |
| Application UI    | Streamlit                    |
| AI analysis       | Google Gemini API             |
| Automation        | Make (Integromat) webhooks    |
| Data logging      | Google Sheets                 |
| Notifications     | Slack webhooks                 |
| Testing           | pytest                        |
| Packaging         | pyproject.toml (PEP 621)      |

Technology choices reflect current planning and may evolve as the project
develops.

## Development Phases

This project is being built incrementally. See
[docs/roadmap.md](docs/roadmap.md) for the full phased roadmap, summarized
below:

1. Repository bootstrap
2. Rule-based QA engine
3. Streamlit application
4. Gemini AI analysis
5. Make automation
6. Google Sheets logging
7. Slack notifications
8. Testing
9. Documentation
10. GitHub release

## Installation

Follow these steps to set up a local development environment, run the
automated test suite, and launch the Streamlit dashboard.

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd campaign-qa-agent
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template and fill in your own credentials:

   ```bash
   cp .env.example .env
   ```

5. Run the test suite:

   ```bash
   pytest
   ```

6. Run the application:

   ```bash
   python -m streamlit run app.py
   ```

## Future Roadmap

The originally planned integration phases (Streamlit, Gemini, Make,
Google Sheets, Slack — see [docs/roadmap.md](docs/roadmap.md)) are all
complete. No further implementation is currently planned; longer-term
product direction beyond this MVP is captured separately in
[project_management/FUTURE_PRODUCT_ROADMAP.md](project_management/FUTURE_PRODUCT_ROADMAP.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.
