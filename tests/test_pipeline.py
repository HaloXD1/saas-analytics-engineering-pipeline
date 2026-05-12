import duckdb
import pandas as pd

from saas_analytics.bootstrap import ensure_demo_outputs
from saas_analytics.config import load_settings, project_path
from saas_analytics.contracts import load_contracts, read_raw_tables, validate_contracts
from saas_analytics.generate_data import generate_all
from saas_analytics.health import assert_outputs, required_exports, verify_outputs
from saas_analytics.run import run_pipeline


def test_data_generation_and_contract_validation():
    outputs = generate_all()
    assert outputs["product_events"].exists()
    settings = load_settings()
    issues = validate_contracts(read_raw_tables(settings), load_contracts(project_path(settings["contracts"]["path"])))
    assert {"duplicate_key", "missing_foreign_key", "numeric_below_min"}.issubset(set(issues["issue_type"]))


def test_pipeline_builds_duckdb_marts_and_exports():
    generate_all()
    outputs = run_pipeline(mode="full")
    assert outputs["database"].exists()
    for path in required_exports().values():
        assert path.exists()
    assert verify_outputs() == []

    with duckdb.connect(str(outputs["database"])) as connection:
        tables = set(connection.sql("SHOW TABLES").df()["name"])
    assert {"mart_mrr", "mart_churn", "mart_feature_adoption", "mart_customer_health"}.issubset(tables)


def test_incremental_pipeline_is_idempotent():
    generate_all()
    outputs = run_pipeline(mode="full")
    with duckdb.connect(str(outputs["database"])) as connection:
        before = connection.sql("SELECT COUNT(*) FROM fact_invoices").fetchone()[0]
    run_pipeline(mode="incremental")
    with duckdb.connect(str(outputs["database"])) as connection:
        after = connection.sql("SELECT COUNT(*) FROM fact_invoices").fetchone()[0]
    assert after == before


def test_mrr_export_matches_duckdb():
    generate_all()
    outputs = run_pipeline(mode="full")
    mrr = pd.read_csv(required_exports()["mart_mrr"])["mrr"].sum()
    with duckdb.connect(str(outputs["database"])) as connection:
        warehouse_mrr = connection.sql("SELECT SUM(mrr) FROM mart_mrr").fetchone()[0]
    assert round(mrr, 2) == round(warehouse_mrr, 2)


def test_dashboard_bootstrap_recreates_missing_exports():
    generate_all()
    run_pipeline(mode="full")
    for path in required_exports().values():
        path.unlink(missing_ok=True)
    assert ensure_demo_outputs() is True
    assert_outputs()
