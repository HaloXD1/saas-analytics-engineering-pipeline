from pathlib import Path

import yaml


def test_docker_compose_has_dashboard_and_pipeline_services():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"dashboard", "pipeline"}.issubset(services)
    assert "streamlit run app/streamlit_dashboard.py" in services["dashboard"]["command"]
    assert services["pipeline"]["command"] == "saas-analytics run-pipeline --mode full"
