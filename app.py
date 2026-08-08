"""Streamlit submission interface for the Campaign QA & Launch Governance Agent.

Marketer-facing UI on top of the deterministic QA engine
(src.validators, src.scoring). This module contains no validation or
scoring logic of its own — it only collects form input, constructs a
CampaignSubmission, calls score_campaign(), and renders the resulting
QAResult. Presentation-only helpers live in src/ui_helpers.py.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import streamlit as st

from config import APP_TITLE, LAYOUT, PAGE_ICON, SIDEBAR_STATE
from src.gemini_analyzer import analyze_campaign
from src.models import (
    CampaignSubmission,
    GeminiReviewResult,
    GeminiReviewStatus,
    QAResult,
    QAStatus,
    ValidationResult,
)
from src.scoring import score_campaign
from src.ui_helpers import (
    CATEGORY_LABELS,
    STATUS_META,
    category_breakdown,
    category_status_label,
    example_campaigns,
    format_points,
    group_by_category,
)

logger = logging.getLogger(__name__)

CAMPAIGN_TYPE_OPTIONS = [
    "Paid Search",
    "Paid Social",
    "Display",
    "Content Syndication",
    "Email",
    "Organic Social",
    "Webinar",
    "Partner Marketing",
    "Other",
]

CHANNEL_OPTIONS = [
    "Google Ads",
    "Microsoft Ads",
    "LinkedIn Ads",
    "Meta Ads",
    "Email",
    "Website",
    "Organic Social",
    "Programmatic Display",
    "Content Syndication",
    "Partner",
    "Webinar/Event",
    "Other",
]

_CUSTOM_CSS = """
<style>
.block-container {
    max-width: 1200px;
    padding-top: 1rem;
    padding-bottom: 2.5rem;
}

.app-header {
    margin-bottom: 0.85rem;
}
.app-header .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 0.25rem;
}
.app-header h1 {
    font-size: 1.45rem;
    font-weight: 700;
    margin: 0 0 0.3rem 0;
    color: #0f172a;
    line-height: 1.25;
}
.app-header p {
    color: #475569;
    font-size: 0.92rem;
    margin: 0;
    max-width: 68ch;
}

.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.6rem;
}

.metric-card {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    background: #ffffff;
    min-height: 5.5rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.metric-card .metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #64748b;
    margin-bottom: 0.35rem;
}
.metric-card .metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.01em;
}

.status-pass { border-color: #86efac !important; background: #f0fdf4 !important; }
.status-pass .metric-value { color: #15803d !important; }
.status-review { border-color: #fcd34d !important; background: #fffbeb !important; }
.status-review .metric-value { color: #b45309 !important; }
.status-fail { border-color: #fca5a5 !important; background: #fef2f2 !important; }
.status-fail .metric-value { color: #b91c1c !important; }

.recommendation {
    margin: 0.75rem 0 1.1rem 0;
    padding: 0.7rem 1rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    font-size: 0.92rem;
    background: #f8fafc;
    color: #0f172a;
}

.category-row {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem 0.6rem;
    background: #ffffff;
    text-align: center;
    min-height: 6rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.category-row .category-label {
    font-size: 0.72rem;
    color: #64748b;
    margin-bottom: 0.3rem;
    line-height: 1.25;
}
.category-row .category-points {
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
}
.category-row .category-status {
    margin-top: 0.4rem;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.category-row.cat-status-pass { border-color: #86efac; }
.category-row.cat-status-pass .category-status { color: #15803d; }
.category-row.cat-status-review { border-color: #fcd34d; }
.category-row.cat-status-review .category-status { color: #b45309; }
.category-row.cat-status-fail { border-color: #fca5a5; }
.category-row.cat-status-fail .category-status { color: #b91c1c; }

.sidebar-heading {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #0f172a;
    margin: 0.1rem 0 0.5rem 0;
}
</style>
"""

_STATE_KEYS = (
    "campaign_name",
    "campaign_type",
    "channel",
    "objective",
    "target_audience",
    "campaign_owner",
    "cta",
    "campaign_message",
    "landing_page_url",
    "destination_url",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "launch_date",
    "budget",
)


def _apply_example(name: str) -> None:
    """Populate widget session state from a curated example campaign.

    Must run before the form widgets below are instantiated in the same
    script pass — Streamlit widgets read their initial value from
    session_state[key] if already present, so setting it here is enough;
    no explicit rerun is required.
    """
    campaign = example_campaigns()[name]
    st.session_state["campaign_name"] = campaign.campaign_name
    st.session_state["campaign_type"] = campaign.campaign_type
    st.session_state["channel"] = (
        campaign.channel if campaign.channel in CHANNEL_OPTIONS else "Other"
    )
    st.session_state["objective"] = campaign.objective
    st.session_state["target_audience"] = campaign.target_audience
    st.session_state["campaign_owner"] = campaign.campaign_owner
    st.session_state["cta"] = campaign.cta
    st.session_state["campaign_message"] = campaign.campaign_message or ""
    st.session_state["landing_page_url"] = campaign.landing_page_url
    st.session_state["destination_url"] = campaign.destination_url or ""
    st.session_state["utm_source"] = campaign.utm_source or ""
    st.session_state["utm_medium"] = campaign.utm_medium or ""
    st.session_state["utm_campaign"] = campaign.utm_campaign or ""
    st.session_state["launch_date"] = campaign.launch_date
    st.session_state["budget"] = campaign.budget or 0.0
    st.session_state.pop("qa_result", None)


def _build_campaign_from_state() -> CampaignSubmission:
    """Construct a CampaignSubmission from raw widget input.

    Values are passed through exactly as entered — no trimming, casing,
    or formatting fixes — so the QA engine can catch formatting problems
    (spacing, casing, etc.) itself rather than having the UI silently
    correct them first.
    """
    state = st.session_state
    return CampaignSubmission(
        campaign_name=state.get("campaign_name", ""),
        campaign_type=state.get("campaign_type", CAMPAIGN_TYPE_OPTIONS[0]),
        channel=state.get("channel", CHANNEL_OPTIONS[0]),
        objective=state.get("objective", ""),
        target_audience=state.get("target_audience", ""),
        landing_page_url=state.get("landing_page_url", ""),
        cta=state.get("cta", ""),
        campaign_owner=state.get("campaign_owner", ""),
        launch_date=state.get("launch_date"),
        destination_url=state.get("destination_url") or None,
        utm_source=state.get("utm_source") or None,
        utm_medium=state.get("utm_medium") or None,
        utm_campaign=state.get("utm_campaign") or None,
        budget=state.get("budget") or None,
        campaign_message=state.get("campaign_message") or None,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="app-header">
            <div class="eyebrow">Marketing Operations QA</div>
            <h1>Campaign QA &amp; Launch Governance</h1>
            <p>Validate campaign governance, tracking quality and launch
            readiness before publishing.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-heading">Example Campaigns</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Load a preset to see how the QA engine scores different "
            "campaign profiles."
        )
        options = ["— Select —", *example_campaigns().keys()]
        choice = st.selectbox(
            "Load a sample campaign", options, label_visibility="collapsed"
        )
        if st.button(
            "Load Example Campaign",
            use_container_width=True,
            disabled=choice == "— Select —",
        ):
            _apply_example(choice)

        st.divider()

        st.markdown(
            '<div class="sidebar-heading">How Scoring Works</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"- **{STATUS_META[QAStatus.PASS]['label']}** — score 90–100, "
            "no critical failures\n"
            f"- **{STATUS_META[QAStatus.REVIEW]['label']}** — score 70–89, "
            "or 90–100 with a critical failure\n"
            f"- **{STATUS_META[QAStatus.FAIL]['label']}** — score 0–69"
        )
        st.caption(
            "A critical failure always prevents PASS, regardless of score."
        )

        st.divider()

        st.markdown(
            '<div class="sidebar-heading">Governance Categories</div>',
            unsafe_allow_html=True,
        )
        st.markdown("\n".join(f"- {label}" for label in CATEGORY_LABELS.values()))


def _section_title(text: str) -> None:
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def render_form() -> bool:
    """Render the campaign submission form. Returns True if submitted."""
    with st.form("campaign_qa_form", clear_on_submit=False):
        with st.container(border=True):
            _section_title("1. Campaign Setup")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input(
                    "Campaign Name",
                    key="campaign_name",
                    placeholder="uk_enterprise_demo_q3_2026",
                )
                st.selectbox(
                    "Campaign Type", CAMPAIGN_TYPE_OPTIONS, key="campaign_type"
                )
                st.selectbox("Channel", CHANNEL_OPTIONS, key="channel")
                st.text_input(
                    "Campaign Owner", key="campaign_owner", placeholder="Jane Doe"
                )
            with col2:
                st.text_input(
                    "Objective", key="objective", placeholder="Demo Signups"
                )
                st.text_input(
                    "Target Audience",
                    key="target_audience",
                    placeholder="UK Enterprise",
                )
                st.text_input("CTA", key="cta", placeholder="Book a Demo")

        with st.container(border=True):
            _section_title("2. Tracking")
            col3, col4 = st.columns(2)
            with col3:
                st.text_input(
                    "Landing Page URL",
                    key="landing_page_url",
                    placeholder="https://example.com/demo",
                )
            with col4:
                st.text_input(
                    "Tracking URL",
                    key="destination_url",
                    placeholder="https://example.com/demo?utm_source=...",
                    help=(
                        "Required for paid campaign types; must contain "
                        "utm_source, utm_medium, and utm_campaign."
                    ),
                )
            col5, col6, col7 = st.columns(3)
            with col5:
                st.text_input(
                    "UTM Source",
                    key="utm_source",
                    placeholder="google, linkedin, meta",
                )
            with col6:
                st.text_input(
                    "UTM Medium",
                    key="utm_medium",
                    placeholder="cpc, paid_social, email",
                )
            with col7:
                st.text_input(
                    "UTM Campaign",
                    key="utm_campaign",
                    placeholder="uk_enterprise_demo_q3_2026",
                )

        with st.container(border=True):
            _section_title("3. Launch")
            col8, col9 = st.columns(2)
            with col8:
                st.date_input(
                    "Launch Date",
                    key="launch_date",
                    value=date.today() + timedelta(days=7),
                )
            with col9:
                st.number_input(
                    "Campaign Budget (£)",
                    key="budget",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    format="%.2f",
                    help=(
                        "Required (must be greater than zero) for paid "
                        "campaign types. Leave at 0 for non-paid campaigns."
                    ),
                )

        with st.container(border=True):
            _section_title("4. Message")
            st.text_area(
                "Campaign Message / Proposition",
                key="campaign_message",
                placeholder="Optional supporting copy or proposition for this campaign.",
                height=100,
            )

        st.write("")
        return st.form_submit_button("Validate Campaign", type="primary")


def _metric_card(col, label: str, value: str, tone: str = "") -> None:
    col.markdown(
        f'<div class="metric-card {tone}">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_result_group(
    title: str, results: list[ValidationResult], *, box_fn=None
) -> None:
    if not results:
        return

    if box_fn is not None:
        st.markdown(f"**{title} ({len(results)})**")
        for result in results:
            lines = [result.message]
            if result.recommendation:
                lines.append(f"**Recommendation:** {result.recommendation}")
            lines.append(
                f"_{CATEGORY_LABELS[result.category]} · "
                f"{format_points(result.points_earned, result.points_available)} pts_"
            )
            box_fn("\n\n".join(lines))
    else:
        with st.expander(f"{title} ({len(results)})"):
            for result in results:
                st.markdown(
                    f"**{result.message}** — {CATEGORY_LABELS[result.category]} "
                    f"({format_points(result.points_earned, result.points_available)} pts)"
                )


def render_results(qa_result: QAResult) -> None:
    _section_title("5. Results")
    meta = STATUS_META[qa_result.status]

    # --- Summary -----------------------------------------------------
    cols = st.columns(4)
    _metric_card(cols[0], "Overall Score", f"{qa_result.score:g} / 100")
    _metric_card(cols[1], "Status", meta["label"], tone=meta["css_class"])
    _metric_card(
        cols[2],
        "Critical Issues",
        str(len(qa_result.critical_failures)),
        tone="status-fail" if qa_result.critical_failures else "",
    )
    _metric_card(
        cols[3],
        "Warnings",
        str(len(qa_result.warnings)),
        tone="status-review" if qa_result.warnings else "",
    )

    st.progress(
        qa_result.score / 100,
        text=f"Overall Score — {qa_result.score:g} / 100",
    )

    st.markdown(
        f'<div class="recommendation {meta["css_class"]}">{meta["recommendation"]}</div>',
        unsafe_allow_html=True,
    )

    # --- Category breakdown -------------------------------------------
    _section_title("Category Breakdown")
    breakdown = category_breakdown(qa_result.validation_results)
    grouped = group_by_category(qa_result.validation_results)
    cat_cols = st.columns(len(CATEGORY_LABELS))
    for col, (category, label) in zip(cat_cols, CATEGORY_LABELS.items()):
        earned, available = breakdown[category]
        status_label, status_class = category_status_label(grouped[category])
        col.markdown(
            f'<div class="category-row {status_class}">'
            f'<div class="category-label">{label}</div>'
            f'<div class="category-points">{format_points(earned, available)}</div>'
            f'<div class="category-status">{status_label}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # --- Critical Issues -> Warnings -> Passed Checks -> Not Applicable
    _render_result_group(
        "Critical Issues", qa_result.critical_failures, box_fn=st.error
    )
    _render_result_group("Warnings", qa_result.warnings, box_fn=st.warning)
    _render_result_group("Passed Checks", qa_result.passed_checks)
    _render_result_group("Not Applicable", qa_result.not_applicable_checks)


def render_ai_review(review_result: GeminiReviewResult) -> None:
    """Render Gemini's supplementary qualitative review.

    Purely additive to render_results(): never reads or displays a score
    or a PASS/REVIEW/FAIL-shaped value, and never reuses the deterministic
    status colour styling — this section must always read as advisory,
    not as a second verdict.
    """
    _section_title("6. AI Review")
    st.caption(
        "Qualitative AI review — supplementary and does not affect the "
        "governance score or status above."
    )

    if review_result.status == GeminiReviewStatus.NOT_CONFIGURED:
        st.info(
            "AI review is not configured. Add a Gemini API key to enable "
            "qualitative review."
        )
        return

    if review_result.status == GeminiReviewStatus.ERROR:
        st.warning(
            "AI review is temporarily unavailable. The deterministic QA "
            "result above is unaffected."
        )
        return

    review = review_result.review
    if review is None:  # defensive; OK status always carries a review
        return

    st.markdown("**AI Summary**")
    st.write(review.summary)

    if review.concerns:
        st.markdown("**Concerns**")
        for concern in review.concerns:
            with st.container(border=True):
                st.markdown(
                    f"**{concern.title}**  \n*Severity: {concern.severity.value}*"
                )
                st.write(concern.explanation)

    if review.strengths:
        with st.expander(f"Strengths ({len(review.strengths)})"):
            for strength in review.strengths:
                st.markdown(f"- {strength}")

    st.markdown("**Recommendation**")
    st.write(review.recommendation)


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=PAGE_ICON,
        layout=LAYOUT,
        initial_sidebar_state=SIDEBAR_STATE,
    )
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    render_sidebar()
    render_header()

    submitted = render_form()

    if submitted:
        try:
            campaign = _build_campaign_from_state()
            qa_result = score_campaign(campaign)
        except Exception:
            logger.exception("Campaign QA run failed")
            st.error(
                "Something went wrong while running this QA check. Please "
                "review your inputs and try again."
            )
        else:
            # Deterministic result is stored first, before Gemini is ever
            # called, so it is guaranteed to be available and displayed
            # regardless of what happens with the AI review below.
            st.session_state["qa_result"] = qa_result

            try:
                with st.spinner("Running AI review..."):
                    gemini_review_result = analyze_campaign(campaign, qa_result)
            except Exception:
                # analyze_campaign() is contracted to never raise; this is
                # defense-in-depth only, so a bug there still can't take
                # down the deterministic result above.
                logger.exception("Unexpected failure while running AI review")
                gemini_review_result = GeminiReviewResult(
                    status=GeminiReviewStatus.ERROR,
                    error_message="AI review is temporarily unavailable.",
                )
            st.session_state["gemini_review_result"] = gemini_review_result

    if "qa_result" in st.session_state:
        render_results(st.session_state["qa_result"])

    if "gemini_review_result" in st.session_state:
        render_ai_review(st.session_state["gemini_review_result"])


if __name__ == "__main__":
    main()
