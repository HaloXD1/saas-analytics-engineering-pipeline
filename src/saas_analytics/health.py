from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from saas_analytics.config import load_settings, project_path


def required_exports() -> dict[str, Path]:
    settings = load_settings()
    return {name: project_path(path) for name, path in settings["exports"].items()}


def missing_exports() -> list[Path]:
    return [path for path in required_exports().values() if not path.exists()]


def verify_outputs() -> list[str]:
    settings = load_settings()
    failures = [f"Missing export: {path}" for path in missing_exports()]
    quality_path = project_path(settings["exports"]["data_quality_summary"])
    if quality_path.exists():
        quality = pd.read_csv(quality_path)
        threshold = settings["quality"]["minimum_quality_score"]
        low_quality = quality[quality["quality_score"] < threshold]
        failures.extend(f"{row.table_name} quality below threshold" for row in low_quality.itertuples(index=False))
    failures.extend(_mrr_consistency_failures(settings))
    return failures


def assert_outputs() -> None:
    failures = verify_outputs()
    if failures:
        raise RuntimeError("Health checks failed:\n- " + "\n- ".join(failures))


def _mrr_consistency_failures(settings: dict) -> list[str]:
    database_path = project_path(settings["paths"]["warehouse"])
    mrr_path = project_path(settings["exports"]["mart_mrr"])
    if not database_path.exists() or not mrr_path.exists():
        return []
    exported = pd.read_csv(mrr_path)["mrr"].sum()
    with duckdb.connect(str(database_path)) as connection:
        database_total = connection.sql("SELECT SUM(mrr) FROM mart_mrr").fetchone()[0]
    if round(float(exported), 2) != round(float(database_total), 2):
        return ["Exported MRR does not match DuckDB mart_mrr"]
    return []
