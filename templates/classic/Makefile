# templates/classic/Makefile — copy to project root (no rename needed).
#
# Canonical Makefile for racecar Python projects. `make help` lists every
# target. `make check` is the canonical verification gate.
#
# Tools are invoked as `$(PYTHON) -m <tool>` / `$(BIN)/<tool>` (never bare
# names), so no target requires an *activated* venv — `make check` works from a
# cold shell, sidestepping the GNU Make 3.81 (macOS) PATH-export bug where
# `export PATH :=` is ignored for non-shell execvp lookups.
#
# Requires pip >= 25.1 for `pip install --group <name>` (PEP 735).

# Auto-detect venv (order: .venv, venv, ../venv). Override with `make VENV=...`.
VENV   := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif
PYTHON := $(if $(VENV),$(VENV)/bin/python,python3)
PIP    := $(PYTHON) -m pip
BIN    := $(if $(VENV),$(VENV)/bin,$(HOME)/.local/bin)

# Project shape — see arch-coherence/PACKAGING.md §"Scope". Pick exactly one
# and set the matching variables:
#
#   shape: src
#     SRC=src                    PKG=src/<pkg>         DJAPP=
#     LIB_PYPROJECT=pyproject.toml
#     DJAPP_PYPROJECT=
#
#   shape: pypkg
#     SRC=pypkg/src              PKG=pypkg/src/<pkg>   DJAPP=
#     LIB_PYPROJECT=pypkg/src/pyproject.toml
#     DJAPP_PYPROJECT=
#
#   shape: pypkg+djapp
#     SRC=pypkg/src              PKG=pypkg/src/<pkg>   DJAPP=djapp
#     LIB_PYPROJECT=pypkg/src/pyproject.toml
#     DJAPP_PYPROJECT=djapp/pyproject.toml
#
#   shape: djapp
#     SRC=djapp                  PKG=djapp/<app>       DJAPP=djapp
#     LIB_PYPROJECT=pyproject.toml
#     DJAPP_PYPROJECT=

# Source root to format/lint/type-check.
SRC ?= src
# Package path to audit for architectural coherence (full path or dotted name).
PKG ?= $(SRC)
# Django app directory; empty when not a Django project.
DJAPP ?=
# Path to the library pyproject (used for tool --config and lockfile gen).
LIB_PYPROJECT   ?= pyproject.toml
# Path to the djapp pyproject (only Shape pypkg+djapp). Empty otherwise.
DJAPP_PYPROJECT ?=
# Library install directory (where pip -e installs from).
LIB_DIR    := $(if $(filter pyproject.toml,$(LIB_PYPROJECT)),.,$(patsubst %/pyproject.toml,%,$(LIB_PYPROJECT)))

# Extra pytest args, e.g. make test PYTEST_ARGS="-k foo -q"
PYTEST_ARGS ?=

.DEFAULT_GOAL := help
.PHONY: help venv install install-dev check check-full fix fmt fmt-check lint \
        test coverage typecheck arch audit docs clean distclean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

$(VENV):
	python3 -m venv .venv

venv: ## Create .venv if missing (always at .venv/)
	@test -n "$(VENV)" || $(MAKE) .venv VENV=.venv

install: venv ## Bootstrap: editable library install (resolves deps from pyproject)
	$(PIP) install --upgrade 'pip>=25.1'
	$(PIP) install -e $(LIB_DIR)
	@if [ -n "$(DJAPP_PYPROJECT)" ]; then \
	  $(PIP) install --group $(DJAPP_PYPROJECT):runtime; \
	fi

install-dev: install ## install + PEP 735 dev group (requires pip >= 25.1)
	$(PIP) install --group $(LIB_PYPROJECT):dev

check: fmt-check lint test ## Fast gate (~30s; pre-commit cadence)

check-full: ## Full gate (parallel; pre-push / CI cadence) — adds typecheck + arch + docs
	@$(MAKE) -j fmt-check lint test typecheck arch docs

audit: ## pip-audit dependency vulnerability scan (standalone; run weekly / on-demand)
	$(PYTHON) -m pip_audit

fix: fmt ## Auto-fix formatting (isort + black)

fmt: ## Format in place (isort orders imports, then black formats)
	$(PYTHON) -m isort --settings-file $(LIB_PYPROJECT) $(SRC) $(DJAPP)
	$(PYTHON) -m black --config $(LIB_PYPROJECT) $(SRC) $(DJAPP)

fmt-check: ## Check formatting only — no writes
	$(PYTHON) -m isort --check-only --settings-file $(LIB_PYPROJECT) $(SRC) $(DJAPP)
	$(PYTHON) -m black --check --config $(LIB_PYPROJECT) $(SRC) $(DJAPP)

lint: ## pylint (summary view: count by message code) + no-upward-imports
	@set -o pipefail; \
	  $(PYTHON) -m pylint --rcfile $(LIB_PYPROJECT) $(SRC) $(DJAPP) 2>&1 \
	  | grep -oE '\([a-z-]+\)$$' | sort | uniq -c | sort -rn
	@$(BIN)/pre-commit run no-upward-imports-in-business-modules --all-files

test: ## pytest; scope via PYTEST_ARGS=... (exit 5 = no tests = ok)
	@$(PYTHON) -m pytest -c $(LIB_PYPROJECT) $(PYTEST_ARGS); status=$$?; \
	  if [ $$status -eq 5 ]; then echo "(no tests collected)"; exit 0; fi; \
	  exit $$status

coverage: ## pytest with branch coverage; HTML report at htmlcov/index.html
	$(PYTHON) -m pytest -c $(LIB_PYPROJECT) \
	  --cov=$(PKG) --cov-branch \
	  --cov-report=term-missing --cov-report=html

typecheck: ## mypy
	$(PYTHON) -m mypy --config-file $(LIB_PYPROJECT) $(SRC)

arch: ## lint-imports + §1 upward + §3 CLI tree + packaging canon (+ Django string-relations)
	$(BIN)/lint-imports --config $(LIB_PYPROJECT)
	$(PYTHON) scripts/check_upward_imports.py $$(find $(PKG) -name '*.py')
	@if [ -n "$$(find $(PKG) -name '__main__.py' -print -quit 2>/dev/null)" ]; then \
	  $(PYTHON) scripts/check_cli_commands.py $(PKG); \
	else \
	  echo "arch: skipping check_cli_commands ($(PKG) has no __main__.py — no CLI surface)"; \
	fi
	$(PYTHON) scripts/check_packaging.py
	@if [ -n "$(DJAPP)" ] && [ -f $(DJAPP)/manage.py ]; then \
	  $(PYTHON) scripts/check_string_relations.py; \
	else \
	  echo "arch: skipping check_string_relations (DJAPP unset or no manage.py)"; \
	fi

docs: ## doc-coherence pre-pass (links / §N / vocab) + TODO + CLAUDE shape + placement
	$(PYTHON) scripts/check_docs.py
	$(PYTHON) scripts/check_todo_format.py
	$(PYTHON) scripts/check_claude_shape.py
	$(PYTHON) scripts/check_file_placement.py

clean: ## Remove caches, *.pyc, .DS_Store, build artifacts (never the venv)
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type f -name '*.py[co]' -delete 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type f -name '.DS_Store' -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .import_linter_cache \
	  build dist *.egg-info .coverage coverage.xml htmlcov

distclean: clean ## clean + remove the virtualenv
	rm -rf $(VENV)
