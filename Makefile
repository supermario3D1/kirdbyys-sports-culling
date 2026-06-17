.PHONY: install models run test lint clean

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

install-dev:
	. .venv/bin/activate && pip install -r requirements.txt && pip install rawpy reportlab pytest

models:
	. .venv/bin/activate && python scripts/setup_models.py

run:
	. .venv/bin/activate && python -m kirdbyys

test:
	. .venv/bin/activate && python -m pytest tests/ -v

lint:
	. .venv/bin/activate && ruff check kirdbyys/ tests/

clean:
	rm -rf .venv kirdbyys/__pycache__ kirdbyys/**/__pycache__ .pytest_cache kirdbyys/cache kirdbyys/temp kirdbyys/exports kirdbyys/data/*.db
