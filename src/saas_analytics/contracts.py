from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ISSUE_COLUMNS = ["table_name", "issue_type", "row_reference", "column_name", "issue_detail"]


def load_contracts(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def read_raw_tables(settings: dict[str, Any]) -> dict[str, pd.DataFrame]:
    from saas_analytics.config import project_path

    tables = {}
    for name, path in settings["raw_files"].items():
        file_path = project_path(path)
        if file_path.suffix == ".jsonl":
            tables[name] = pd.read_json(file_path, lines=True)
        else:
            tables[name] = pd.read_csv(file_path)
    return tables


def validate_contracts(raw_tables: dict[str, pd.DataFrame], contracts: dict[str, Any]) -> pd.DataFrame:
    issues = []
    for table_name, frame in raw_tables.items():
        contract = contracts.get(table_name, {})
        _check_required_columns(table_name, frame, contract)
        issues.extend(_pattern_issues(table_name, frame, contract))
        issues.extend(_duplicate_issues(table_name, frame, contract))
        issues.extend(_date_issues(table_name, frame, contract))
        issues.extend(_numeric_issues(table_name, frame, contract))
        issues.extend(_allowed_value_issues(table_name, frame, contract))
        issues.extend(_foreign_key_issues(table_name, frame, contract, raw_tables))
    return pd.DataFrame(issues, columns=ISSUE_COLUMNS)


def _check_required_columns(table_name: str, frame: pd.DataFrame, contract: dict[str, Any]) -> None:
    missing = sorted(set(contract.get("required_columns", [])) - set(frame.columns))
    if missing:
        raise ValueError(f"{table_name} missing required columns: {', '.join(missing)}")


def _pattern_issues(table_name: str, frame: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, str]]:
    key = contract.get("unique_key")
    pattern = contract.get("id_pattern")
    if not key or not pattern:
        return []
    invalid = ~frame[key].astype(str).str.match(pattern, na=False)
    return _issue_rows(frame[invalid], table_name, "invalid_id_format", key, f"Expected {pattern}", key)


def _duplicate_issues(table_name: str, frame: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, str]]:
    key = contract.get("unique_key")
    if not key:
        return []
    duplicate = frame[key].astype(str).duplicated(keep="first")
    return _issue_rows(frame[duplicate], table_name, "duplicate_key", key, "Duplicate key", key)


def _date_issues(table_name: str, frame: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    for column, rules in contract.get("date_columns", {}).items():
        parsed = pd.to_datetime(frame[column], errors="coerce")
        issues.extend(
            _issue_rows(
                frame[parsed.isna()],
                table_name,
                "invalid_date",
                column,
                "Date cannot be parsed",
                contract.get("unique_key"),
            )
        )
        if rules.get("min"):
            below = parsed.notna() & (parsed < pd.Timestamp(rules["min"]))
            issues.extend(
                _issue_rows(
                    frame[below],
                    table_name,
                    "date_below_min",
                    column,
                    f"Before {rules['min']}",
                    contract.get("unique_key"),
                )
            )
        if rules.get("max"):
            above = parsed.notna() & (parsed > pd.Timestamp(rules["max"]))
            issues.extend(
                _issue_rows(
                    frame[above],
                    table_name,
                    "date_above_max",
                    column,
                    f"After {rules['max']}",
                    contract.get("unique_key"),
                )
            )
    return issues


def _numeric_issues(table_name: str, frame: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    for column, rules in contract.get("numeric_ranges", {}).items():
        values = pd.to_numeric(frame[column], errors="coerce")
        issues.extend(
            _issue_rows(
                frame[values.isna()], table_name, "invalid_numeric", column, "Not numeric", contract.get("unique_key")
            )
        )
        if "min" in rules:
            minimum = float(rules["min"])
            below = values <= minimum if rules.get("inclusive_min") is False else values < minimum
            issues.extend(
                _issue_rows(
                    frame[values.notna() & below],
                    table_name,
                    "numeric_below_min",
                    column,
                    f"Minimum {minimum}",
                    contract.get("unique_key"),
                )
            )
    return issues


def _allowed_value_issues(table_name: str, frame: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    for column, allowed_values in contract.get("allowed_values", {}).items():
        allowed = {str(value).lower() for value in allowed_values}
        invalid = ~frame[column].astype(str).str.lower().isin(allowed)
        issues.extend(
            _issue_rows(
                frame[invalid],
                table_name,
                "invalid_allowed_value",
                column,
                "Unexpected value",
                contract.get("unique_key"),
            )
        )
    return issues


def _foreign_key_issues(
    table_name: str,
    frame: pd.DataFrame,
    contract: dict[str, Any],
    raw_tables: dict[str, pd.DataFrame],
) -> list[dict[str, str]]:
    issues = []
    for column, rule in contract.get("foreign_keys", {}).items():
        parent = raw_tables[rule["table"]]
        parent_keys = set(parent[rule["column"]].astype(str))
        missing = ~frame[column].astype(str).isin(parent_keys)
        issues.extend(
            _issue_rows(
                frame[missing],
                table_name,
                "missing_foreign_key",
                column,
                f"Missing {rule['table']}.{rule['column']}",
                contract.get("unique_key"),
            )
        )
    return issues


def _issue_rows(
    frame: pd.DataFrame,
    table_name: str,
    issue_type: str,
    column_name: str,
    detail: str,
    reference_column: str | None,
) -> list[dict[str, str]]:
    if frame.empty:
        return []
    references = (
        frame[reference_column].astype(str)
        if reference_column and reference_column in frame.columns
        else frame.index.astype(str)
    )
    return [
        {
            "table_name": table_name,
            "issue_type": issue_type,
            "row_reference": reference,
            "column_name": column_name,
            "issue_detail": detail,
        }
        for reference in references
    ]
