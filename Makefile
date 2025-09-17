PY=python
PIP=pip

.PHONY: help install dev qa lint fmt test run docker-build docker-run init

help:
	@echo "Targets: install dev qa lint fmt test run docker-build docker-run init"

install:
	$(PIP) install -U pip
	$(PIP) install -e .[dev]

init:
	$(PY) scripts/init_dirs.py
	$(PY) scripts/init_playwright.py
	$(PY) scripts/init_dbs.py

qa: lint test

lint:
	ruff check .

fmt:
	ruff format .

test:
	pytest

run:
	$(PY) bot.py

docker-build:
	docker build -t rag-notes:local .

docker-run:
	docker run --rm -it --env-file .env rag-notes:local
