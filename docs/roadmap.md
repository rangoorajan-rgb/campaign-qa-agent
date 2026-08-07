# Roadmap

This roadmap describes the planned, phased build-out of the Campaign QA &
Launch Governance Agent. Phases are intended to be completed sequentially,
with each phase building on a working result from the previous one.

## Phase 1 – Repository Bootstrap

Establish a clean, professional repository structure: project scaffolding,
documentation, licensing, environment configuration, and packaging setup.
No application logic is implemented in this phase.

## Phase 2 – Rule-Based QA Engine

Implement the core validation logic: checks for UTM parameter correctness,
URL validity, campaign naming conventions, and required-field presence.

## Phase 3 – Streamlit Application

Build a Streamlit interface for submitting campaigns and viewing QA
results produced by the rule-based engine.

## Phase 4 – Gemini AI Analysis

Integrate Gemini to supplement rule-based checks with AI-assisted analysis
for issues that are difficult to capture with static rules.

## Phase 5 – Make Automation

Connect the QA workflow to external marketing tools using Make
(Integromat), enabling campaigns to be submitted for QA automatically.

## Phase 6 – Google Sheets Logging

Persist QA run results to Google Sheets to provide a shareable, auditable
history of campaign QA outcomes.

## Phase 7 – Slack Notifications

Send Slack notifications summarizing QA results and flagging launch
blockers to relevant stakeholders.

## Phase 8 – Testing

Build out a test suite covering the QA engine, scoring logic, and other
core components to ensure correctness and prevent regressions.

## Phase 9 – Documentation

Expand project documentation to reflect the fully implemented system,
including usage guides and configuration references.

## Phase 10 – GitHub Release

Prepare and publish a tagged release of the completed application.
