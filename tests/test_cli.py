import os
import subprocess
import sys

from saas_analytics.cli import main
from saas_analytics.generate_data import generate_all


def test_cli_smoke(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["saas-analytics", "generate-data"])
    main()
    assert "Generated raw files" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["saas-analytics", "run-pipeline", "--mode", "full"])
    main()
    assert "DuckDB warehouse" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["saas-analytics", "export-marts"])
    main()
    assert "Exported marts" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["saas-analytics", "validate-contracts"])
    main()
    assert "Contract issues found" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["saas-analytics", "health-check"])
    main()
    assert "Health checks passed" in capsys.readouterr().out


def test_module_cli_subprocess():
    generate_all()
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-m", "saas_analytics.cli", "validate-contracts"],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )
    assert "Contract issues found" in result.stdout
