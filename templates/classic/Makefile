# templates/classic/Makefile — copy to project root (no rename needed).
# Classic variant using black + isort + pylint.
# `make check` is the canonical verification entry point.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so black, isort, pylint, mypy, pytest, lint-imports,
# pre-commit resolve to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif

# Package path or dotted name to audit for architectural coherence.
# Override with:  make arch PKG=my_package
PKG ?= src

.PHONY: check fix fmt fmt-check lint test typecheck arch docs clean help

check: fmt-check lint test typecheck arch docs

fix: fmt

fmt:
	black src
	isort src

fmt-check:
	black --check src
	isort --check-only src

lint:
	pylint src
	pre-commit run no-upward-imports-in-business-modules --all-files

test:
	pytest

typecheck:
	mypy src

arch:
	lint-imports
	python scripts/check_upward_imports.py $$(find $(PKG) -name '*.py')
	python scripts/check_cli_commands.py $(PKG)
	@if [ -f manage.py ]; then python scripts/check_string_relations.py; else echo "arch: skipping check_string_relations (no manage.py — not a Django project)"; fi

docs:
	python scripts/check_docs.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +

help:
	@echo "make check     - run all verification (fmt-check + lint + test + typecheck + arch + docs)"
	@echo "make fix       - auto-fix formatting (black + isort)"
	@echo "make fmt       - format code in place"
	@echo "make fmt-check - check formatting without modifying"
	@echo "make lint      - pylint + custom arch-coherence/PYTHON.md §1 check"
	@echo "make test      - pytest"
	@echo "make typecheck - mypy"
	@echo "make arch      - full arch audit: lint-imports + §1 upward imports + §3 CLI tree + (Django only) string-relations. Scope: PKG=$(PKG) (override: make arch PKG=<path>)"
	@echo "make docs      - doc-coherence mechanical pre-pass (link / §N / vocabulary drift)"
	@echo "make clean     - remove cache dirs"
