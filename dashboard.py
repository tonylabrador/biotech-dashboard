"""
Company Pipeline & Trials Review Dashboard
Data: Company_Pipeline_Summary.csv, Enriched_Clinical_Trials.csv
Created by Tony Jiang
"""

import pathlib
import pandas as pd
import streamlit as st

# ── Page config & custom CSS ───────────────────────────────────

st.set_page_config(
    page_title="Pipeline Review | Tony Jiang",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Maximize main content area */
    .block-container { padding-top: 0.75rem; padding-bottom: 0.5rem; padding-left: 1.5rem; padding-right: 1.5rem; max-width: 100%; }
    header[data-testid="stHeader"] { background: linear-gradient(90deg, #1e3a5f 0%, #2d5a87 100%); }
    .stDataFrame { font-size: 0.9rem; }
    /* Compact metrics */
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
    /* Footer */
    .footer { text-align: right; font-size: 0.8rem; color: #6b7280; margin-top: 1rem; padding-top: 0.5rem; border-top: 1px solid #e5e7eb; }
    /* Section headers */
    .section-title { font-size: 1.05rem; font-weight: 600; color: #1e3a5f; margin-bottom: 0.25rem; }
    .company-detail-header { background: #f0f4f8; padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 4px solid #2d5a87; }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = pathlib.Path(__file__).parent
SUMMARY_CSV = DATA_DIR / "Company_Pipeline_Summary.csv"
TRIALS_CSV = DATA_DIR / "Enriched_Clinical_Trials.csv"


@st.cache_data(show_spinner="Loading company summary…")
def load_summary() -> pd.DataFrame:
    if not SUMMARY_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(SUMMARY_CSV)
    for col in ["Market Cap", "EV", "Total Debt", "Total Cash", "Price", "52W Low", "52W High", "Wall Street Ratings",
                "Pipeline_Count", "Total_Active_Trials", "Shares Outstanding", "Institutional Shares", "Insider %"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner="Loading trials…")
def load_trials() -> pd.DataFrame:
    if not TRIALS_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(TRIALS_CSV)
    for col in ["EnrollmentCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── Load data ─────────────────────────────────────────────────────

df_summary = load_summary()
df_trials_all = load_trials()

if df_summary.empty:
    st.error(f"**{SUMMARY_CSV.name}** not found. Run the pipeline first.")
    st.stop()

# ── Sidebar: filters ──────────────────────────────────────────────

st.sidebar.markdown("### Filters")
st.sidebar.markdown("---")

# Market Cap (B)
mcap_b = df_summary["Market Cap"].dropna() / 1e9
mcap_min_b = float(mcap_b.min()) if len(mcap_b) else 0.0
mcap_max_b = float(mcap_b.max()) if len(mcap_b) else 1.0
st.sidebar.markdown("**Market Cap (B USD)**")
mcap_lo = st.sidebar.number_input("Min", min_value=0.0, max_value=mcap_max_b * 1.2, value=mcap_min_b, step=0.1, format="%.2f", key="mcap_lo")
mcap_hi = st.sidebar.number_input("Max", min_value=0.0, max_value=mcap_max_b * 2, value=mcap_max_b, step=0.5, format="%.2f", key="mcap_hi")

# Therapeutic Area
tas = sorted(df_summary["Therapeutic_Area_Filter"].dropna().unique().tolist())
ta_selected = st.sidebar.multiselect("Therapeutic Area", options=tas, default=[], key="ta_filter")

# Phase
_phase_order = {"PHASE4": 4, "PHASE3": 3, "PHASE2": 2, "PHASE1": 1, "EARLY_PHASE1": 0, "N/A": -1, "No Trials": -2}
phases_raw = df_summary["Highest_Phase"].dropna().unique().tolist()
phases = sorted(phases_raw, key=lambda x: (_phase_order.get(x, -1), str(x)))
phase_selected = st.sidebar.multiselect("Phase of Development", options=phases, default=[], key="phase_filter")

# Has Marketed Drug
marketed_options = ["All", "Yes", "No"]
marketed_choice = st.sidebar.radio("Has Marketed Drug", options=marketed_options, index=0, key="marketed")

st.sidebar.markdown("---")
clear_btn = st.sidebar.button("Clear filters", width="stretch")
st.sidebar.markdown("---")
st.sidebar.caption("Dashboard by **Tony Jiang**")

if clear_btn:
    st.session_state["mcap_lo"] = mcap_min_b
    st.session_state["mcap_hi"] = mcap_max_b
    st.session_state["ta_filter"] = []
    st.session_state["phase_filter"] = []
    st.session_state["marketed"] = "All"
    st.rerun()

# ── Apply filters to summary ─────────────────────────────────────

filtered = df_summary.copy()
filtered = filtered[
    (filtered["Market Cap"].fillna(0) >= mcap_lo * 1e9) &
    (filtered["Market Cap"].fillna(0) <= mcap_hi * 1e9)
]
if ta_selected:
    filtered = filtered[filtered["Therapeutic_Area_Filter"].isin(ta_selected)]
if phase_selected:
    filtered = filtered[filtered["Highest_Phase"].isin(phase_selected)]
if marketed_choice == "Yes":
    filtered = filtered[filtered["Has_Marketed_Drug"] == "Yes"]
elif marketed_choice == "No":
    filtered = filtered[filtered["Has_Marketed_Drug"] == "No"]

# Unique companies for selector (from filtered rows)
companies = filtered[["Symbol", "Name"]].drop_duplicates().sort_values("Name")
company_list = companies.apply(lambda r: f"{r['Symbol']} — {r['Name']}", axis=1).tolist()

# ── Header: title + creator ───────────────────────────────────────

st.markdown(
    "<p style='font-size:1.6rem; font-weight:700; color:#1e3a5f; margin-bottom:0;'>Company Pipeline & Trials Review</p>"
    "<p style='font-size:0.85rem; color:#6b7280; margin-top:0.1rem;'>Filter by Market Cap, Therapeutic Area, Phase, Marketed Drug · Select a company to view trials</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Top bar: KPI + company selector ───────────────────────────────

col_k1, col_k2, col_k3, col_sel = st.columns([1, 1, 1, 2])
with col_k1:
    st.metric("Companies (rows)", f"{len(filtered)}")
with col_k2:
    uniq = filtered["Symbol"].nunique()
    st.metric("Unique companies", f"{uniq}")
with col_k3:
    avg_mcap = filtered["Market Cap"].mean() / 1e9
    st.metric("Avg Market Cap", f"${avg_mcap:.2f}B" if pd.notna(avg_mcap) else "—")
with col_sel:
    company_choice = st.selectbox(
        "View trials for company",
        options=["— Select company —"] + company_list,
        index=0,
        key="company_select",
    )

# ── Display table (formatted) ─────────────────────────────────────

display = filtered.copy()
display["Market Cap (B)"] = (display["Market Cap"] / 1e9).round(2)
display["EV (B)"] = (display["EV"] / 1e9).round(2)
display["Total Cash (M)"] = (display["Total Cash"] / 1e6).round(0)
display["Total Debt (M)"] = (display["Total Debt"] / 1e6).round(0)

cols_show = [
    "Symbol", "Name", "Therapeutic_Area_Filter", "Highest_Phase", "Has_Marketed_Drug",
    "Market Cap (B)", "Pipeline_Count", "Total_Active_Trials", "Country", "Industry",
]
cols_show = [c for c in cols_show if c in display.columns]
display = display[cols_show]

st.markdown("<p class='section-title'>Company list (filtered) — sort by clicking column headers</p>", unsafe_allow_html=True)
st.dataframe(
    display.reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
    height=520,
    column_config={
        "Market Cap (B)": st.column_config.NumberColumn("Mkt Cap ($B)", format="%.2f"),
        "EV (B)": st.column_config.NumberColumn("EV ($B)", format="%.2f"),
        "Total Cash (M)": st.column_config.NumberColumn("Cash ($M)", format="%.0f"),
        "Total Debt (M)": st.column_config.NumberColumn("Debt ($M)", format="%.0f"),
    },
)

# ── Company detail: trials ───────────────────────────────────────

if company_choice and company_choice != "— Select company —":
    symbol = company_choice.split(" — ")[0]
    company_name = company_choice.split(" — ", 1)[1] if " — " in company_choice else ""

    st.markdown("---")
    st.markdown(
        f"<div class='company-detail-header'><strong>{symbol}</strong> — {company_name} · All trials</div>",
        unsafe_allow_html=True,
    )

    trials = df_trials_all[df_trials_all["Symbol"] == symbol] if not df_trials_all.empty else pd.DataFrame()
    if trials.empty:
        st.info("No trials found for this company in Enriched_Clinical_Trials.csv.")
    else:
        # Show key trial columns + CTG link
        trial_cols = ["NCTId", "Phases", "Status", "Conditions", "Interventions", "EnrollmentCount", "StartDate", "PrimaryCompletionDate", "BriefSummary", "OfficialTitle"]
        trial_cols = [c for c in trial_cols if c in trials.columns]
        trials_display = trials[trial_cols].copy()
        trials_display["NCT_Link"] = trials_display["NCTId"].apply(
            lambda x: f"https://clinicaltrials.gov/study/{x}" if pd.notna(x) and str(x).startswith("NCT") else ""
        )
        st.markdown(f"**{len(trials)}** trial(s)")
        st.dataframe(
            trials_display,
            use_container_width=True,
            hide_index=True,
            height=min(450, 100 + len(trials) * 40),
            column_config={
                "NCTId": st.column_config.TextColumn("NCT ID", width="small"),
                "NCT_Link": st.column_config.LinkColumn("CTG", display_text="Open", width="small"),
                "EnrollmentCount": st.column_config.NumberColumn("Enrollment", format="%d"),
                "BriefSummary": st.column_config.TextColumn("Summary", width="large"),
                "OfficialTitle": st.column_config.TextColumn("Title", width="large"),
            },
        )

# ── Footer ───────────────────────────────────────────────────────

st.markdown("<div class='footer'>Dashboard by Tony Jiang</div>", unsafe_allow_html=True)
