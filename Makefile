# Makefile for PyAgenity packaging and publishing

.PHONY: build publish testpublish clean test test-cov

build:
	uv pip install build
	python -m build

publish: build
	uv pip install twine
	twine upload dist/*

testpublish: build
	uv pip install twine
	twine upload --repository testpypi dist/*

clean:
	rm -rf dist build *.egg-info

test:
	uv run pytest -v

.PHONY: docs-serve docs-build
docs-serve:
	@echo "Serving docs at http://127.0.0.1:8000"
	mkdocs serve -a 127.0.0.1:8000

docs-build:
	mkdocs build --strict

test-cov:
	uv run pytest --cov=pyagenity --cov-report=html --cov-report=term-missing --cov-report=xml -v
