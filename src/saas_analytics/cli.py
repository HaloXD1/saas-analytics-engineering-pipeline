from __future__ import annotations

import argparse

from saas_analytics.config import load_settings, project_path
from saas_analytics.contracts import load_contracts, read_raw_tables, validate_contracts
from saas_analytics.generate_data import generate_all
from saas_analytics.health import assert_outputs
from saas_analytics.run import export_existing_marts, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="SaaS analytics engineering pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("generate-data", help="Generate synthetic SaaS source data")
    run_parser = subparsers.add_parser("run-pipeline", help="Run warehouse pipeline and marts")
    run_parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    subparsers.add_parser("validate-contracts", help="Validate raw files against YAML contracts")
    subparsers.add_parser("export-marts", help="Rebuild and export marts from DuckDB")
    subparsers.add_parser("health-check", help="Run export and KPI integrity checks")
    args = parser.parse_args()

    if args.command == "generate-data":
        outputs = generate_all()
        print("Generated raw files:")
        for name, path in outputs.items():
            print(f"- {name}: {path}")
    elif args.command == "run-pipeline":
        outputs = run_pipeline(mode=args.mode)
        print(f"DuckDB warehouse: {outputs['database']}")
        print(f"Dashboard exports: {outputs['exports']}")
    elif args.command == "validate-contracts":
        settings = load_settings()
        issues = validate_contracts(
            read_raw_tables(settings), load_contracts(project_path(settings["contracts"]["path"]))
        )
        print(f"Contract issues found: {len(issues)}")
        if not issues.empty:
            print(
                issues.groupby(["table_name", "issue_type"])
                .size()
                .reset_index(name="issue_count")
                .to_string(index=False)
            )
    elif args.command == "export-marts":
        marts = export_existing_marts()
        print("Exported marts:")
        for name in marts:
            print(f"- {name}")
    elif args.command == "health-check":
        assert_outputs()
        print("Health checks passed.")


if __name__ == "__main__":
    main()
