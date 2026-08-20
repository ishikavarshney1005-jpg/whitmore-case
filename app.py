"""
Whitmore Structured Credit Opportunities Fund II — LAIM Sleeve Dashboard
==========================================================================
Case Study: FinValley 10.0 (Caldwell & Crane Partners)

Reads pre-computed, verified outputs from the Part A calculation notebook
(data/*.csv) and presents them as an interactive, institutional-grade dashboard.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Page config & professional styling
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Whitmore Fund II — LAIM Sleeve Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Main background & font styling */
    .main { background-color: #f4f6f9; }
    
    /* Metric Card Styling */
    .stMetric {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #586069;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f2328;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 6px 6px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
        border: 1px solid #e1e4e8;
        color: #24292e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0366d6 !important;
        color: white !important;
    }

    /* Subheaders and text */
    h3 {
        color: #1f2328;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 600;
        letter-spacing: -0.01em;
    }
    
    /* Custom Badge helpers */
    .badge-red { background-color: #ffeef0; color: #b3261e; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
    .badge-green { background-color: #e6ffed; color: #146c2e; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = Path(__file__).parent


# --------------------------------------------------------------------------
# Data loading (cached)
# --------------------------------------------------------------------------
@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / f"{name}.csv")
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    return df


@st.cache_data
def load_scalars() -> dict:
    with open(DATA_DIR / "scalars.json") as f:
        return json.load(f)


loan_book = load_csv("df_loan_book_master")
cash_ledger = load_csv("df_cash_ledger")
revolver = load_csv("df_revolver_util")
lease_full = load_csv("leased")
sleeve_lease_cost = load_csv("df_sleeve_lease_cost")
cds_book = load_csv("cds_book")
fx_summary = load_csv("fx_summary")
options_summary = load_csv("options_summary")
hedge_summary = load_csv("hedge_effectiveness_summary")
kpi_summary = load_csv("kpi_summary")
concentration_name = load_csv("concentration")
concentration_cp = load_csv("concentration_cp")
core_pnl = load_csv("core_pnl_components")
oneoff_pnl = load_csv("oneoff_pnl_components")
assumptions = load_csv("assumptions_log")
scalars = load_scalars()

# Mappings
ASSET_CLASS_MAP = {
    "Net loan book interest/PIK income": "Loan Book",
    "Greystone + Ironbridge financing cost": "Financing",
    "IRS Q3 realized settlement (cash, kept)": "IRS Hedge",
    "IRS Q4 accrued (unrealized MTM change)": "IRS Hedge",
    "Content-library lease cost (this sleeve)": "Leased Assets",
    "Management (GP) fee": "Financing",
    "Options recognized P&L": "Options",
    "GBP forward realized P&L (as executed)": "FX Hedge",
    "JPY forward realized P&L": "FX Hedge",
}
core_pnl["Asset_Class"] = core_pnl["Component"].map(ASSET_CLASS_MAP).fillna("Other")

CASH_CATEGORY_ASSET_CLASS = {
    "LOAN_INT_IN": "Loan Book", "LOAN_FEE_IN": "Loan Book", "LOAN_INT_ACCR": "Loan Book",
    "SWAP_NET": "IRS Hedge", "SWAP_SETTLE": "IRS Hedge",
    "SWAP_PREM_OUT": "CDS", "SWAP_PREM_IN": "CDS",
    "DEBT_INT_OUT": "Financing", "DEBT_FEE_OUT": "Financing",
    "LEASE_OUT": "Leased Assets", "ROYALTY_IN": "Leased Assets",
    "FX_ROLL": "FX Hedge",
    "OPT_PREM_IN": "Options", "OPT_EX_OUT": "Options",
    "LP_CAPITAL_IN": "LP Capital", "LP_CAPITAL_OUT": "LP Capital",
    "LP_DIST_OUT": "LP Capital",
    "GP_FEE_OUT": "Financing", "ADMIN_OUT": "Financing",
    "MISC_IN": "Other",
}
cash_ledger["Asset_Class"] = cash_ledger["Category_Raw"].map(CASH_CATEGORY_ASSET_CLASS).fillna("Other")
cash_ledger["Value_Date"] = pd.to_datetime(cash_ledger["Value_Date"])

ALL_ASSET_CLASSES = sorted(
    set(core_pnl["Asset_Class"]) | set(cash_ledger["Asset_Class"])
)

# --------------------------------------------------------------------------
# Sidebar — global filters
# --------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/investment-portfolio.png", width=60)
st.sidebar.title("Portfolio Filters")
st.sidebar.markdown("Refines **Overview** and **Cash vs. Recognized** tabs.")

selected_classes = st.sidebar.multiselect(
    "Asset class",
    options=ALL_ASSET_CLASSES,
    default=ALL_ASSET_CLASSES,
)

min_d, max_d = cash_ledger["Value_Date"].min(), cash_ledger["Value_Date"].max()
date_range = st.sidebar.date_input(
    "Cash ledger period",
    value=(min_d.date(), max_d.date()),
    min_value=min_d.date(),
    max_value=max_d.date(),
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
else:
    start_d, end_d = min_d.date(), max_d.date()

st.sidebar.markdown("---")
st.sidebar.info(
    "**Fund Context:** Whitmore Structured Credit Opportunities Fund II, L.P. "
    "Data pipeline verified against Step 0–9 computation outputs."
)

# --------------------------------------------------------------------------
# Header + top-line KPIs
# --------------------------------------------------------------------------
st.title("Whitmore Fund II — LAIM Sleeve Dashboard")
st.markdown("##### Q4 2025 Performance Review & Strategic Risk Monitoring")
st.write("")

kpi_dict = dict(zip(kpi_summary["KPI"], kpi_summary["Value"]))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Net yield, pre-leverage", kpi_dict.get("Net yield before leverage (annualized)", "—"))
c2.metric("Net yield, post-leverage", kpi_dict.get("Net yield after leverage (annualized)", "—"))
c3.metric("Cost-to-income ratio", kpi_dict.get("Cost-to-income ratio", "—"))
c4.metric("Debt-service coverage", kpi_dict.get("Debt-service coverage ratio", "—"))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Net accrual gap (Q4)", "-$4.38M", "-1.14% of NAV", delta_color="inverse")
c6.metric("Largest single-name breach", "Lumivue", "20.8% vs 12.5% limit", delta_color="inverse")
c7.metric("Top counterparty exposure", "Greystone Fin.", "$3.84M net")
c8.metric("Hedges operational", "1 of 3", "2 misaligned structures", delta_color="off")

st.markdown("---")

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab_overview, tab_loans, tab_hedges, tab_options, tab_conc, tab_lease, tab_cash, tab_assump = st.tabs(
    [
        "📈 Overview",
        "📑 Loan Book",
        "🛡️ Financing & Hedges",
        "📊 Options",
        "⚠️ Concentration",
        "🏢 Leased Assets",
        "💵 Cash vs. Recognized",
        "🔍 Assumptions Log",
    ]
)

# ---- OVERVIEW ----
with tab_overview:
    st.subheader("Q4 2025 Recognized P&L by Component")
    filtered_core = core_pnl[core_pnl["Asset_Class"].isin(selected_classes)]
    
    fig = px.bar(
        filtered_core,
        x="Component",
        y="Amount_USD",
        color="Amount_USD",
        color_continuous_scale=["#d93838", "#f0f2f5", "#107c41"],
        color_continuous_midpoint=0,
        text=filtered_core["Amount_USD"].map(lambda v: f"${v:,.0f}"),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        template="plotly_white",
        yaxis_title="USD",
        xaxis_tickangle=-25,
        height=450,
        margin=dict(t=20, b=100, l=40, r=20),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    total_core = filtered_core["Amount_USD"].sum()
    st.success(f"**Total core recognized P&L (filtered):** ${total_core:,.0f} (Excludes Orion one-off restructuring items).")

    st.subheader("One-off / Event-Driven Items (Q4 2025)")
    st.dataframe(oneoff_pnl, use_container_width=True, hide_index=True)
    st.caption("Orion Studios credit event: Realized auction settlement gain vs. Mezzanine RSA exchange markdown.")

# ---- LOAN BOOK ----
with tab_loans:
    st.subheader("Master Loan Book Registry")
    st.caption(f"Total positions: {len(loan_book)} | Total outstanding: ${loan_book['Outstanding_USD'].sum():,.0f} USD")

    obligors = sorted(loan_book["Obligor_Name"].unique())
    servicers = sorted(loan_book["Servicer"].dropna().unique())
    coupon_types = sorted(loan_book["Coupon_Type"].dropna().unique())

    fcol1, fcol2, fcol3 = st.columns(3)
    sel_obligor = fcol1.multiselect("Obligor", obligors, default=obligors)
    sel_servicer = fcol2.multiselect("Servicer", servicers, default=servicers)
    sel_coupon = fcol3.multiselect("Coupon type", coupon_types, default=coupon_types)

    filt = loan_book[
        loan_book["Obligor_Name"].isin(sel_obligor)
        & loan_book["Servicer"].isin(sel_servicer)
        & loan_book["Coupon_Type"].isin(sel_coupon)
    ]

    lcol1, lcol2 = st.columns([2, 1])
    with lcol1:
        by_obligor = filt.groupby("Obligor_Name")["Outstanding_USD"].sum().sort_values(ascending=True)
        fig3 = px.bar(by_obligor, orientation="h", template="plotly_white")
        fig3.update_layout(height=340, margin=dict(t=10, b=10), showlegend=False, yaxis_title="")
        st.plotly_chart(fig3, use_container_width=True)
    with lcol2:
        fig4 = px.pie(filt, names="Coupon_Type", values="Outstanding_USD", hole=0.4, template="plotly_white")
        fig4.update_layout(height=340, margin=dict(t=10, b=10))
        st.plotly_chart(fig4, use_container_width=True)

    st.dataframe(
        filt[["Loan_Key", "Obligor_Name", "CCY", "Tranche", "Outstanding_USD",
              "Coupon_Type", "Fixed_Rate_Pct", "Coupon_Spread_bps", "Servicer", "Reporting_Basis"]],
        use_container_width=True, hide_index=True,
    )

# ---- FINANCING & HEDGES ----
with tab_hedges:
    st.subheader("Fund Financing & Facility Utilization")
    facilities = sorted(revolver["Obligor"].unique())
    sel_fac = st.multiselect("Revolver obligor", facilities, default=facilities)
    rev_filt = revolver[revolver["Obligor"].isin(sel_fac)].copy()
    rev_filt["Report_Date"] = pd.to_datetime(rev_filt["Report_Date"])
    
    fig5 = px.line(rev_filt.sort_values("Report_Date"), x="Report_Date", y="Drawn_USD", color="Obligor", markers=True, template="plotly_white")
    fig5.update_layout(height=320, margin=dict(t=10, b=10), yaxis_title="Drawn Balance (USD)")
    st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")
    st.subheader("Hedge Effectiveness Summary")
    
    def _color_assessment(val: str) -> str:
        v = str(val).lower()
        if "wrong" in v or "backwards" in v:
            return "background-color: #ffeef0; color: #b3261e;"
        if "oversized" in v or "undersized" in v:
            return "background-color: #fff8c4; color: #b08800;"
        return "background-color: #e6ffed; color: #146c2e;"

    try:
        styled_hedge = hedge_summary.style.map(_color_assessment, subset=["Assessment"])
    except AttributeError:
        styled_hedge = hedge_summary.style.applymap(_color_assessment, subset=["Assessment"])
    
    st.dataframe(styled_hedge, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Credit Default Swaps (CDS) Book")
    st.dataframe(cds_book, use_container_width=True, hide_index=True)

# ---- OPTIONS ----
with tab_options:
    st.subheader("Options Recognized P&L Breakdown")
    st.dataframe(options_summary, use_container_width=True, hide_index=True)
    fig7 = px.bar(options_summary, x="Component", y="Amount_USD", color="Recognized", template="plotly_white", color_discrete_map={True: "#107c41", False: "#586069"})
    fig7.update_layout(height=350, margin=dict(t=10, b=30))
    st.plotly_chart(fig7, use_container_width=True)

# ---- CONCENTRATION ----
with tab_conc:
    st.subheader("Single-Name Concentration vs. 12.5% Covenant Limit")
    st.dataframe(
        concentration_name.style.apply(
            lambda row: ["background-color: #ffeef0; color: #b3261e;" if row["Breach"] else "" for _ in row],
            axis=1,
        ),
        use_container_width=True, hide_index=True,
    )
    
    fig8 = px.bar(
        concentration_name, x="Reference_Entity", y="Exposure_USD",
        color="Breach", color_discrete_map={True: "#b3261e", False: "#107c41"},
        template="plotly_white"
    )
    fig8.add_hline(y=concentration_name["Limit_USD"].iloc[0], line_dash="dash", annotation_text="12.5% NAV Limit", line_color="#24292e")
    fig8.update_layout(height=380, margin=dict(t=10, b=30))
    st.plotly_chart(fig8, use_container_width=True)

    st.markdown("---")
    st.subheader("Counterparty Exposure Summary")
    st.dataframe(concentration_cp, use_container_width=True, hide_index=True)

# ---- LEASED ASSETS ----
with tab_lease:
    st.subheader("Leased Assets Registry")
    cat_options = sorted(lease_full["Asset_Category"].unique())
    sel_cat = st.multiselect("Asset category", cat_options, default=cat_options)
    lease_filt = lease_full[lease_full["Asset_Category"].isin(sel_cat)]
    st.dataframe(lease_filt, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Content-Library Lease Costs (Sleeve Allocation)")
    st.dataframe(sleeve_lease_cost, use_container_width=True, hide_index=True)
    st.metric("Total Q4 Content-Library Cost Allocated", "$1,279,205")

# ---- CASH VS RECOGNIZED ----
with tab_cash:
    st.subheader("Cash Ledger Movements")
    cash_filt = cash_ledger[
        cash_ledger["Asset_Class"].isin(selected_classes)
        & (cash_ledger["Value_Date"].dt.date >= start_d)
        & (cash_ledger["Value_Date"].dt.date <= end_d)
    ]

    cc1, cc2 = st.columns(2)
    cc1.metric("Total Cash In (Filtered)", f"${cash_filt.loc[cash_filt['Amount_USD']>0,'Amount_USD'].sum():,.0f}")
    cc2.metric("Total Cash Out (Filtered)", f"${cash_filt.loc[cash_filt['Amount_USD']<0,'Amount_USD'].sum():,.0f}")

    cash_daily = cash_filt.groupby("Value_Date")["Amount_USD"].sum().cumsum().reset_index()
    fig10 = px.line(cash_daily, x="Value_Date", y="Amount_USD", markers=True, template="plotly_white")
    fig10.update_layout(height=320, margin=dict(t=10, b=10), yaxis_title="Cumulative Net Cash (USD)")
    st.plotly_chart(fig10, use_container_width=True)

    st.dataframe(cash_filt.sort_values("Value_Date"), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Recognition-Timing Accrual Gap (Q4)")
    g1, g2, g3 = st.columns(3)
    g1.metric("Income Recognized, Cash Pending", f"${scalars['total_income_no_cash']:,.0f}")
    g2.metric("Expense Recognized, Cash Pending", f"-${scalars['total_expense_no_cash']:,.0f}")
    g3.metric("Net Accrual Gap", f"${scalars['net_accrual_gap_q4']:,.0f}", "-1.14% NAV", delta_color="inverse")

# ---- ASSUMPTIONS LOG ----
with tab_assump:
    st.subheader("Audit Trail: Assumptions & Judgment Calls")
    step_options = sorted(assumptions["Step"].unique())
    sel_steps = st.multiselect("Filter step", step_options, default=step_options)
    area_options = sorted(assumptions["Area"].unique())
    sel_areas = st.multiselect("Filter area", area_options, default=area_options)

    assump_filt = assumptions[assumptions["Step"].isin(sel_steps) & assumptions["Area"].isin(sel_areas)]
    st.dataframe(assump_filt, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #586069; font-size: 0.8rem;'>"
    "Whitmore Fund II LAIM Sleeve Dashboard · Built for FinValley 10.0"
    "</div>",
    unsafe_allow_html=True,
)
