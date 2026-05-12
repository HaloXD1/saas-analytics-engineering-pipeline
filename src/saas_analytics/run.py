from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from saas_analytics.config import ensure_parent, load_settings, project_path
from saas_analytics.contracts import load_contracts, read_raw_tables, validate_contracts
from saas_analytics.markdown import dataframe_to_markdown
from saas_analytics.warehouse import clean_tables, export_marts, load_warehouse


def run_pipeline(mode: str = "full") -> dict[str, Path]:
    started_at = datetime.now(timezone.utc)
    settings = load_settings()
    raw_tables = read_raw_tables(settings)
    contracts = load_contracts(project_path(settings["contracts"]["path"]))
    issues = validate_contracts(raw_tables, contracts)
    clean = clean_tables(raw_tables)
    database_path = project_path(settings["paths"]["warehouse"])
    export_paths = _export_paths(settings)
    loaded_counts = load_warehouse(database_path, clean, mode)
    export_marts(database_path, export_paths)
    _write_quality_outputs(raw_tables, clean, issues, export_paths, settings)
    _write_run_summary(started_at, mode, raw_tables, clean, loaded_counts, export_paths, settings)
    return {"database": database_path, "exports": project_path(settings["paths"]["exports"])}


def export_existing_marts() -> dict[str, pd.DataFrame]:
    settings = load_settings()
    return export_marts(project_path(settings["paths"]["warehouse"]), _export_paths(settings))


def _export_paths(settings: dict) -> dict[str, Path]:
    return {name: project_path(path) for name, path in settings["exports"].items()}


def _write_quality_outputs(
    raw_tables: dict[str, pd.DataFrame],
    clean: dict[str, pd.DataFrame],
    issues: pd.DataFrame,
    export_paths: dict[str, Path],
    settings: dict,
) -> None:
    raw_counts = {
        "customers": len(raw_tables["customers"]),
        "subscriptions": len(raw_tables["subscriptions"]),
        "invoices": len(raw_tables["invoices"]),
        "product_events": len(raw_tables["product_events"]),
        "support_tickets": len(raw_tables["support_tickets"]),
    }
    clean_counts = {
        "customers": len(clean["dim_customers"]),
        "subscriptions": len(clean["fact_subscriptions"]),
        "invoices": len(clean["fact_invoices"]),
        "product_events": len(clean["fact_product_events"]),
        "support_tickets": len(clean["fact_support_tickets"]),
    }
    rows = []
    for table, raw_count in raw_counts.items():
        issue_count = int((issues["table_name"] == table).sum()) if not issues.empty else 0
        clean_count = clean_counts[table]
        issue_rate = issue_count / raw_count if raw_count else 0
        rows.append(
            {
                "table_name": table,
                "raw_rows": raw_count,
                "clean_rows": clean_count,
                "rejected_rows": raw_count - clean_count,
                "validation_issues": issue_count,
                "quality_score": round(max(0, 1 - issue_rate), 4),
            }
        )
    summary = pd.DataFrame(rows)
    ensure_parent(export_paths["data_quality_issues"])
    issues.to_csv(export_paths["data_quality_issues"], index=False)
    summary.to_csv(export_paths["data_quality_summary"], index=False)
    report = [
        "# Data Quality Report",
        "",
        dataframe_to_markdown(summary),
        "",
        "## Issue Breakdown",
        "",
        dataframe_to_markdown(
            issues.groupby(["table_name", "issue_type"]).size().reset_index(name="issue_count")
            if not issues.empty
            else pd.DataFrame()
        ),
        "",
    ]
    project_path(settings["paths"]["docs"]).mkdir(parents=True, exist_ok=True)
    project_path("docs/data_quality_report.md").write_text("\n".join(report), encoding="utf-8")


def _write_run_summary(
    started_at: datetime,
    mode: str,
    raw_tables: dict[str, pd.DataFrame],
    clean: dict[str, pd.DataFrame],
    loaded_counts: dict[str, int],
    export_paths: dict[str, Path],
    settings: dict,
) -> None:
    finished_at = datetime.now(timezone.utc)
    summary = pd.DataFrame(
        [
            {
                "run_id": started_at.strftime("%Y%m%dT%H%M%S%fZ"),
                "mode": mode,
                "started_at_utc": started_at.isoformat(),
                "finished_at_utc": finished_at.isoformat(),
                "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
                "rows_read": sum(len(frame) for frame in raw_tables.values()),
                "rows_cleaned": sum(len(frame) for frame in clean.values()),
                "loaded_rows": sum(loaded_counts.values()),
            }
        ]
    )
    ensure_parent(export_paths["pipeline_run_summary"])
    summary.to_csv(export_paths["pipeline_run_summary"], index=False)
    lines = ["# Pipeline Run Summary", "", dataframe_to_markdown(summary), ""]
    project_path("docs/run_summary.md").write_text("\n".join(lines), encoding="utf-8")
