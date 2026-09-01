VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
IMAGE := fraud-service:slim
COMPOSE_URL := http://localhost:8080

.DEFAULT_GOAL := help
.PHONY: help install run-batch lint format test test-unit test-all cov serve image image-naive up down smoke clean

help:  ## List targets
	@grep -E '^[a-zA-Z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:  ## Editable install plus the dev toolchain
	$(PIP) install -e ".[dev]"

run-batch:  ## Score data/transactions_sample.csv into scored.csv
	$(PY) -m fraud_service.batch

lint:  ## ruff, no autofix
	$(VENV)/bin/ruff check src tests

format:  ## ruff with autofix
	$(VENV)/bin/ruff check --fix src tests

test-unit:  ## The fast unit selection
	$(PY) -m pytest -m unit

test:  ## Everything except the slow golden sweep
	$(PY) -m pytest -m "not slow"

test-all:  ## The whole suite, slow tests included
	$(PY) -m pytest

cov:  ## Branch coverage over domain/service/api
	$(PY) -m pytest -m "not slow" --cov=fraud_service.domain --cov=fraud_service.service \
		--cov=fraud_service.api --cov-report=term-missing

serve:  ## Run the API locally with reload
	$(VENV)/bin/fastapi dev src/fraud_service/api/app.py

image:  ## Build the multi-stage runtime image
	docker build -f Dockerfile -t $(IMAGE) .

image-naive:  ## Build the single-stage image kept for the size comparison
	docker build -f Dockerfile.naive -t fraud-service:naive .

up:  ## Start the compose stack and wait for healthy
	docker compose up -d --wait

down:  ## Stop the compose stack
	docker compose down

smoke:  ## Hit the running stack the way Lab 3 does
	curl -fsS $(COMPOSE_URL)/v1/ready && echo
	curl -fsS -X POST $(COMPOSE_URL)/v1/predict \
		-H 'content-type: application/json' -d @payloads/sample.json && echo

clean:  ## Remove test and coverage artefacts
	rm -rf .pytest_cache .coverage htmlcov
	find . -path ./.venv -prune -o -name __pycache__ -type d -print0 | xargs -0 rm -rf
