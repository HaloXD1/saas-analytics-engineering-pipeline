from __future__ import annotations

from contextlib import closing
from pathlib import Path

import duckdb
import pandas as pd

from saas_analytics.config import ensure_parent, project_path

PRIMARY_KEYS = {
    "dim_customers": "customer_id",
    "dim_plans": "plan",
    "fact_subscriptions": "subscription_id",
    "fact_invoices": "invoice_id",
    "fact_product_events": "event_id",
    "fact_support_tickets": "ticket_id",
}


def clean_tables(raw_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    customers = raw_tables["customers"].drop_duplicates("customer_id").copy()
    subscriptions = raw_tables["subscriptions"].copy()
    invoices = raw_tables["invoices"].copy()
    events = raw_tables["product_events"].copy()
    tickets = raw_tables["support_tickets"].copy()

    valid_customers = set(customers["customer_id"])
    subscriptions["mrr"] = pd.to_numeric(subscriptions["mrr"], errors="coerce")
    subscriptions = subscriptions[
        subscriptions["customer_id"].isin(valid_customers)
        & subscriptions["mrr"].gt(0)
        & ~subscriptions["subscription_id"].duplicated()
    ].copy()
    invoices["amount"] = pd.to_numeric(invoices["amount"], errors="coerce")
    invoices = invoices[invoices["customer_id"].isin(valid_customers) & invoices["amount"].gt(0)].copy()
    events = events[events["customer_id"].isin(valid_customers) & ~events["event_id"].duplicated()].copy()
    tickets = tickets[tickets["customer_id"].isin(valid_customers) & ~tickets["ticket_id"].duplicated()].copy()

    return {
        "dim_customers": customers,
        "dim_plans": pd.DataFrame(
            [
                {"plan": "Starter", "monthly_price": 49, "tier": 1},
                {"plan": "Growth", "monthly_price": 149, "tier": 2},
                {"plan": "Scale", "monthly_price": 399, "tier": 3},
            ]
        ),
        "fact_subscriptions": subscriptions,
        "fact_invoices": invoices,
        "fact_product_events": events,
        "fact_support_tickets": tickets,
    }


def load_warehouse(database_path: Path, tables: dict[str, pd.DataFrame], mode: str) -> dict[str, int]:
    if mode not in {"full", "incremental"}:
        raise ValueError("mode must be 'full' or 'incremental'")
    ensure_parent(database_path)
    loaded_counts = {}
    with closing(duckdb.connect(str(database_path))) as connection:
        if mode == "full":
            _drop_project_tables(connection)
        for table_name, frame in tables.items():
            frame_to_load = frame if mode == "full" else _new_rows(connection, table_name, frame)
            connection.register("incoming_frame", frame_to_load)
            connection.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_frame WHERE 1=0")
            connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_frame")
            connection.unregister("incoming_frame")
            loaded_counts[table_name] = len(frame_to_load)
        _write_parquet_layers(connection)
    return loaded_counts


def build_marts(database_path: Path) -> dict[str, pd.DataFrame]:
    with closing(duckdb.connect(str(database_path))) as connection:
        _create_mart_tables(connection)
        return {
            "executive_overview": connection.sql("SELECT * FROM executive_overview").df(),
            "mart_mrr": connection.sql("SELECT * FROM mart_mrr ORDER BY invoice_month").df(),
            "mart_churn": connection.sql("SELECT * FROM mart_churn ORDER BY churn_month").df(),
            "mart_feature_adoption": connection.sql("SELECT * FROM mart_feature_adoption ORDER BY active_users DESC").df(),
            "mart_customer_health": connection.sql("SELECT * FROM mart_customer_health ORDER BY health_score DESC").df(),
        }


def export_marts(database_path: Path, export_paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    marts = build_marts(database_path)
    for name, frame in marts.items():
        ensure_parent(export_paths[name])
        frame.to_csv(export_paths[name], index=False)
    return marts


def _new_rows(connection: duckdb.DuckDBPyConnection, table_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    key = PRIMARY_KEYS[table_name]
    if not _table_exists(connection, table_name):
        return frame
    existing_keys = set(connection.sql(f"SELECT {key} FROM {table_name}").df()[key].astype(str))
    return frame[~frame[key].astype(str).isin(existing_keys)]


def _drop_project_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table in [
        "executive_overview",
        "mart_mrr",
        "mart_churn",
        "mart_feature_adoption",
        "mart_customer_health",
        *PRIMARY_KEYS,
    ]:
        connection.execute(f"DROP TABLE IF EXISTS {table}")


def _create_mart_tables(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE mart_mrr AS
        SELECT
            invoice_month,
            ROUND(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END), 2) AS mrr,
            COUNT(DISTINCT customer_id) AS paying_customers,
            ROUND(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) / NULLIF(COUNT(DISTINCT customer_id), 0), 2) AS arpa
        FROM fact_invoices
        GROUP BY invoice_month
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE mart_churn AS
        SELECT
            DATE_TRUNC('month', CAST(end_date AS DATE))::DATE AS churn_month,
            COUNT(*) AS churned_customers,
            ROUND(SUM(mrr), 2) AS churned_mrr
        FROM fact_subscriptions
        WHERE status = 'cancelled' AND end_date IS NOT NULL AND end_date != ''
        GROUP BY churn_month
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE mart_feature_adoption AS
        SELECT
            feature,
            COUNT(*) AS events,
            COUNT(DISTINCT user_id) AS active_users,
            COUNT(DISTINCT customer_id) AS active_customers
        FROM fact_product_events
        GROUP BY feature
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE mart_customer_health AS
        SELECT
            c.customer_id,
            c.customer_name,
            c.segment,
            COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) AS revenue,
            COUNT(DISTINCT e.event_id) AS product_events,
            COUNT(DISTINCT t.ticket_id) AS support_tickets,
            ROUND(
                LEAST(100, COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) / 100
                + COUNT(DISTINCT e.event_id) * 0.4
                - COUNT(DISTINCT t.ticket_id) * 2),
                2
            ) AS health_score
        FROM dim_customers c
        LEFT JOIN fact_invoices i ON c.customer_id = i.customer_id
        LEFT JOIN fact_product_events e ON c.customer_id = e.customer_id
        LEFT JOIN fact_support_tickets t ON c.customer_id = t.customer_id
        GROUP BY c.customer_id, c.customer_name, c.segment
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE executive_overview AS
        SELECT
            ROUND((SELECT SUM(mrr) FROM mart_mrr), 2) AS annual_recurring_revenue,
            (SELECT COUNT(DISTINCT customer_id) FROM fact_subscriptions WHERE status = 'active') AS active_customers,
            (SELECT COUNT(*) FROM fact_subscriptions WHERE status = 'trial') AS trial_customers,
            (SELECT COALESCE(SUM(churned_customers), 0) FROM mart_churn) AS churned_customers,
            (SELECT COUNT(DISTINCT user_id) FROM fact_product_events) AS active_users,
            ROUND((SELECT AVG(health_score) FROM mart_customer_health), 2) AS average_health_score
        """
    )


def _write_parquet_layers(connection: duckdb.DuckDBPyConnection) -> None:
    parquet_dir = project_path("data/warehouse/parquet")
    parquet_dir.mkdir(parents=True, exist_ok=True)
    for table in PRIMARY_KEYS:
        if _table_exists(connection, table):
            connection.execute(f"COPY {table} TO '{parquet_dir / f'{table}.parquet'}' (FORMAT PARQUET)")


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    return bool(
        connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0]
    )
