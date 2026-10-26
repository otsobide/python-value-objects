.DEFAULT_GOAL := check
.PHONY: install test cov lint format typecheck check build clean publish

install:          ## create .venv with the dev group
	uv sync
test:
	uv run pytest
cov:              ## branch coverage of pyvalueobjects/; fails under 100 %
	uv run pytest --cov --cov-report=term-missing
lint:
	uv run ruff check .
	uv run ruff format --check .
format:
	uv run ruff check --fix .
	uv run ruff format .
typecheck:
	uv run mypy
check: lint typecheck cov
build:
	rm -rf dist && uv build
clean:
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .hypothesis
publish: build
	uv publish
