# Campaign QA & Launch Governance Agent

## Overview

The Campaign QA & Launch Governance Agent is an internal Marketing Operations
tool designed to validate marketing campaigns before launch. It checks
campaign metadata and tracking configuration against a set of governance
rules, helping teams catch preventable errors before they reach production.

This project is currently in early development. The deterministic
rule-based QA engine — campaign validation and scoring — is implemented
and covered by an automated test suite. A Streamlit submission interface
is under active development (Sprint 2) on top of that engine; it has not
yet been manually verified in a browser, so it should not be considered
complete. Gemini qualitative analysis and the Make/Google Sheets/Slack
integrations described below are still planned and not yet built.

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

## Planned Architecture

The application is planned to evolve through the following components:

- A **rule-based QA engine** that validates campaign data against defined
  governance rules (naming conventions, required fields, UTM structure,
  URL validity) and produces a deterministic 0–100 score and PASS/REVIEW/
  FAIL status — **implemented** (`src/validators.py`, `src/scoring.py`)
- A **Streamlit application** providing a user interface for submitting and
  reviewing campaign QA results — **under active development** (`app.py`,
  `src/ui_helpers.py`); not yet manually verified, so not yet considered
  complete
- **Gemini AI-assisted analysis** for more nuanced review beyond static
  rules (e.g., naming consistency, contextual anomalies) — planned, not
  yet built
- **Automation via Make (Integromat)** to connect the QA process to
  existing marketing tools and workflows — planned, not yet built
- **Google Sheets logging** to maintain a persistent, shareable audit trail
  of QA results — planned, not yet built
- **Slack notifications** to alert stakeholders of QA results and launch
  blockers — planned, not yet built

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

This project will be built incrementally. See [docs/roadmap.md](docs/roadmap.md)
for the full phased roadmap, summarized below:

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

> A Streamlit UI exists and is under active Sprint 2 development, but it
> has not yet been manually verified in a browser — treat it as
> unfinished. These steps prepare a local environment for development and
> let you run the deterministic QA engine's test suite.

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

## Future Roadmap

Planned future work includes the Streamlit interface, Gemini-powered
analysis, and integrations with Make, Google Sheets, and Slack. Full
details are tracked in [docs/roadmap.md](docs/roadmap.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.
