.PHONY: setup generate run incremental validate marts health test coverage lint format-check smoke dashboard docker-dashboard docker-pipeline

setup:
	python3 -m pip install -e ".[dev]"

generate:
	saas-analytics generate-data

run:
	saas-analytics run-pipeline --mode full

incremental:
	saas-analytics run-pipeline --mode incremental

validate:
	saas-analytics validate-contracts

marts:
	saas-analytics export-marts

health:
	saas-analytics health-check

test:
	pytest

coverage:
	pytest --cov=src/saas_analytics --cov-report=term-missing

lint:
	ruff check .

format-check:
	ruff format --check .

smoke:
	saas-analytics generate-data
	saas-analytics run-pipeline --mode full
	saas-analytics run-pipeline --mode incremental
	saas-analytics export-marts
	saas-analytics validate-contracts
	saas-analytics health-check

dashboard:
	streamlit run app/streamlit_dashboard.py

docker-dashboard:
	docker compose up dashboard

docker-pipeline:
	docker compose run --rm pipeline saas-analytics run-pipeline --mode full
