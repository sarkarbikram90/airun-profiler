.PHONY: install test test-cov lint format demo lab doctor build release-dry-run docs clean

install:
	pip install -e ".[dev,otel]"

test:
	pytest -v

test-cov:
	pytest -v --cov=airun --cov-report=term-missing

lint:
	ruff check src tests examples
	mypy src

format:
	ruff format src tests examples
	ruff check --fix src tests examples

demo:
	python -m airun demo

lab:
	python examples/lab/run_all.py

doctor:
	python -m airun doctor

build:
	python -m build

release-dry-run: build
	python -m airun doctor
	python -m airun demo
	python -m airun report latest

release:
	python scripts/release.py $(version)

docs:
	@echo "Documentation located in docs/ and validation/ directories."

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
