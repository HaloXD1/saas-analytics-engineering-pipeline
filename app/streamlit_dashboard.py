from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from saas_analytics.bootstrap import ensure_demo_outputs

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "exports"


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(EXPORTS / name)


def money(value: float) -> str:
    return f"${value:,.0f}"


st.set_page_config(page_title="SaaS Analytics Dashboard", layout="wide")
generated = ensure_demo_outputs()
if generated:
    st.toast("Demo data prepared")

st.title("SaaS Analytics Dashboard")
st.caption("DuckDB analytics engineering pipeline for revenue, churn, usage, customer health, and data quality.")

overview = load_csv("executive_overview.csv").iloc[0]
mrr = load_csv("mart_mrr.csv")
churn = load_csv("mart_churn.csv")
adoption = load_csv("mart_feature_adoption.csv")
health = load_csv("mart_customer_health.csv")
quality = load_csv("data_quality_summary.csv")

tab_exec, tab_revenue, tab_churn, tab_usage, tab_health, tab_quality = st.tabs(
    ["Executive", "Revenue", "Churn", "Product Usage", "Customer Health", "Data Quality"]
)

with tab_exec:
    cols = st.columns(5)
    cols[0].metric("ARR Proxy", money(overview["annual_recurring_revenue"]))
    cols[1].metric("Active Customers", f"{int(overview['active_customers']):,}")
    cols[2].metric("Trial Customers", f"{int(overview['trial_customers']):,}")
    cols[3].metric("Active Users", f"{int(overview['active_users']):,}")
    cols[4].metric("Avg Health", f"{overview['average_health_score']:.1f}")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.line(mrr, x="invoice_month", y="mrr", markers=True), use_container_width=True)
    with right:
        st.plotly_chart(px.bar(adoption, x="feature", y="active_users", color="feature"), use_container_width=True)

with tab_revenue:
    st.subheader("Monthly Recurring Revenue")
    st.plotly_chart(px.bar(mrr, x="invoice_month", y="mrr", labels={"mrr": "MRR"}), use_container_width=True)
    st.dataframe(mrr, use_container_width=True, hide_index=True)

with tab_churn:
    st.subheader("Churned Customers and MRR")
    if churn.empty:
        st.info("No churn in current generated dataset.")
    else:
        st.plotly_chart(px.bar(churn, x="churn_month", y="churned_customers"), use_container_width=True)
        st.dataframe(churn, use_container_width=True, hide_index=True)

with tab_usage:
    st.subheader("Feature Adoption")
    st.plotly_chart(px.bar(adoption, x="feature", y="events", color="feature"), use_container_width=True)
    st.dataframe(adoption, use_container_width=True, hide_index=True)

with tab_health:
    st.subheader("Customer Health")
    segment = st.multiselect("Segment", sorted(health["segment"].unique()), default=sorted(health["segment"].unique()))
    view = health[health["segment"].isin(segment)]
    st.plotly_chart(
        px.scatter(view, x="revenue", y="product_events", color="segment", size="health_score"),
        use_container_width=True,
    )
    st.dataframe(view.head(25), use_container_width=True, hide_index=True)

with tab_quality:
    st.subheader("Data Quality")
    st.metric("Average Quality Score", f"{quality['quality_score'].mean() * 100:.1f}%")
    st.plotly_chart(px.bar(quality, x="table_name", y="quality_score", color="table_name"), use_container_width=True)
    st.dataframe(quality, use_container_width=True, hide_index=True)
