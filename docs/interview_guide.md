# Interview Guide

## Pitch

I built a SaaS analytics engineering pipeline that ingests customers, subscriptions, invoices, product events, and support tickets. It validates raw data with YAML contracts, builds cleaned DuckDB warehouse tables, creates SQL KPI marts, exports dashboard datasets, and visualizes revenue, churn, product adoption, customer health, and data quality in Streamlit.

## Good Talking Points

- DuckDB gives SQL analytics without needing a cloud warehouse.
- Data contracts make assumptions explicit.
- Incremental loading prevents duplicate warehouse rows.
- KPI marts separate business logic from dashboard code.
- The dashboard bootstraps demo data for public deployment.
