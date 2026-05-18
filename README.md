# SaaS Analytics Engineering Pipeline

[![Tests](https://github.com/AhmedYasserShalaby/saas-analytics-engineering-pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/AhmedYasserShalaby/saas-analytics-engineering-pipeline/actions/workflows/tests.yml)

SaaS analytics engineering portfolio project that turns customer, billing, subscription, support, and product-event data into DuckDB/Parquet layers, trusted KPI marts, and a Streamlit dashboard.

## Live Demo

Streamlit Cloud URL: https://ahmed-saas-analytics-pipeline.streamlit.app/

The dashboard bootstraps demo data automatically if generated exports are missing.

![SaaS dashboard demo](dashboard/demo/saas_dashboard_demo.gif)

![SaaS Analytics Dashboard](dashboard/screenshots/saas_dashboard.png)

## Architecture

```mermaid
flowchart LR
    A[Raw CSV and JSONL sources] --> B[YAML data contracts]
    B --> C[Python cleaning pipeline]
    C --> D[DuckDB warehouse]
    D --> E[Parquet layer exports]
    D --> F[Gold KPI marts]
    F --> G[Streamlit dashboard]
    B --> H[Data quality report]
```

## Metrics

- Monthly recurring revenue
- Active customers
- Trial customers
- Churned customers
- Active users
- Feature adoption
- Customer health score
- Data quality score

## Warehouse Model

```mermaid
erDiagram
    dim_customers ||--o{ fact_subscriptions : has
    dim_customers ||--o{ fact_invoices : billed
    dim_customers ||--o{ fact_product_events : uses
    dim_customers ||--o{ fact_support_tickets : opens
    dim_plans ||--o{ fact_subscriptions : prices
    fact_invoices ||--o{ mart_mrr : aggregates
    fact_subscriptions ||--o{ mart_churn : aggregates
    fact_product_events ||--o{ mart_feature_adoption : aggregates
    dim_customers ||--o{ mart_customer_health : scores
```

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
saas-analytics generate-data
saas-analytics run-pipeline --mode full
streamlit run app/streamlit_dashboard.py
```

## Docker

```bash
docker compose up dashboard
docker compose run --rm pipeline saas-analytics run-pipeline --mode full
```

## Testing

```bash
ruff check .
ruff format --check .
pytest --cov=src/saas_analytics --cov-report=term-missing
```

## Docs

- [Architecture](docs/architecture.md)
- [Data model](docs/data_model.md)
- [KPI definitions](docs/kpi_definitions.md)
- [Data contracts](docs/data_contracts.md)

## Project Summary

- Built a SaaS analytics engineering pipeline that ingests customer, billing, subscription, support, and product-event data into DuckDB/Parquet layers and exports trusted KPI marts.
- Modeled MRR, churn, trial conversion, product adoption, and customer health metrics with SQL transformations, data contracts, incremental loading, and automated quality checks.
- Delivered a Streamlit executive dashboard with CI tests, Docker support, documentation, and reproducible local/demo setup.
