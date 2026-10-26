.DEFAULT_GOAL := check
.PHONY: install test cov check build clean publish

install:          ## create .venv with the dev group
	uv sync
test:
	uv run pytest
cov:              ## branch coverage of pyvalueobjects/
	uv run pytest --cov --cov-report=term-missing
check: cov
build:
	rm -rf dist && uv build
clean:
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .hypothesis
publish: build
	uv publish
