# Data

This directory holds sample data used for local development and testing of
the QA engine.

## sample_campaigns.csv

35 representative marketing campaigns spanning the channel types this tool
is designed to govern: Paid Search (Google Ads, Microsoft Ads), Paid Social
(Meta Ads, LinkedIn Ads), Display, Content Syndication, Email, Organic
Social, Webinar, and Partner Marketing.

Columns map directly to `src.models.CampaignSubmission` fields, in the
same order:

`campaign_name, campaign_type, channel, objective, target_audience,
landing_page_url, destination_url, utm_source, utm_medium, utm_campaign,
cta, campaign_owner, launch_date, budget, campaign_message`

Empty cells represent a missing/optional value (`None` for optional
fields, an empty string for required fields — both are treated as blank
by the validators).

One additional column, `quality_tier`, is **not** a `CampaignSubmission`
field — it is dataset metadata used by
[tests/test_integration.py](../tests/test_integration.py) to group rows by
intended outcome:

- **`excellent`** (8 rows) — fully compliant; expected to score 100 and
  PASS.
- **`pass_ready`** (5 rows) — expected to PASS (score ≥ 90, no critical
  failures), with one minor, non-critical issue each (e.g. an HTTP landing
  page or a long CTA).
- **`warning`** (10 rows) — expected to REVIEW via warning-driven score
  deductions alone (score 70–89), with zero critical failures. Covers
  naming-convention violations, HTTP landing pages, uppercase/spaced UTM
  values, `utm_campaign`/name misalignment, and near-term launch dates.
- **`critical`** (12 rows) — each has at least one critical failure (so
  status can never be PASS regardless of score). Ten score high enough
  (≥ 90) to demonstrate the critical-failure override into REVIEW; two are
  deliberately broken across many rules simultaneously to demonstrate
  FAIL (score < 70).

All dates are anchored to a fixed reference date of **2026-08-07** (the
date this dataset was authored) so that "launch date today" / "launch
date yesterday" scenarios remain meaningful. Tests that use this dataset
must pass `reference_date=date(2026, 8, 7)` explicitly to
`validate_campaign()`/`score_campaign()` rather than relying on
`date.today()`, or the launch-readiness rows will silently drift out of
their intended scenario as real time passes.

The dataset exercises every validator rule at least once: required-field
presence, landing/destination URL format and HTTPS preference, paid UTM
requirements, UTM casing/spacing/alignment, destination-URL UTM
query-parameter coverage, every naming-convention check, launch-date
timing (past/today/tomorrow/2+ days), and paid budget presence/positivity.
