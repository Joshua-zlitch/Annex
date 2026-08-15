.PHONY: install dev test lint format docker-build docker-up

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

docker-build:
	docker build -t annex-api .

docker-up:
	docker compose up