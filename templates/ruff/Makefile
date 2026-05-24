# templates/ruff/Makefile — copy to project root (no rename needed).
# Ruff variant using ruff + black.
# `make help` lists every target. `make check` is the canonical verification gate.
#
# Tools are invoked as `$(PYTHON) -m <tool>` / `$(BIN)/<tool>` (never bare
# names), so no target requires an *activated* venv — `make check` works from a
# cold shell, sidestepping the GNU Make 3.81 (macOS) PATH-export bug where
# `export PATH :=` is ignored for non-shell execvp lookups.

# Auto-detect venv (order: .venv, venv, ../venv). Override with `make VENV=...`.
VENV   := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif
PYTHON := $(if $(VENV),$(VENV)/bin/python,python3)
PIP    := $(PYTHON) -m pip
BIN    := $(if $(VENV),$(VENV)/bin,$(HOME)/.local/bin)

# Source root to format/lint/type-check. Override: make SRC=pypkg/src
SRC ?= src
# Package path or dotted name to audit for architectural coherence.
PKG ?= $(SRC)
# Extra pytest args, e.g. make test PYTEST_ARGS="-k foo -q"
PYTEST_ARGS ?=

.DEFAULT_GOAL := help
.PHONY: help install install-dev check fix fmt fmt-check lint test typecheck \
        arch docs clean distclean obsidian obsidian-data obsidian-docs

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

# install-dev assumes your project-side pyproject defines a `[dev]` optional
# extra (the template pyproject leaves [project]/extras project-side).
install: ## Install runtime deps (editable)
	$(PIP) install -e .

install-dev: ## Install runtime + dev + test deps (needs project [dev] extra)
	$(PIP) install -e ".[dev]"

check: fmt-check lint test typecheck arch docs ## Canonical gate (CI runs this)

fix: fmt ## Auto-fix formatting (ruff --fix + black)

fmt: ## Format in place (ruff --fix then black)
	$(PYTHON) -m ruff check --fix $(SRC)
	$(PYTHON) -m black $(SRC)

fmt-check: ## Check formatting only — no writes (ruff + black --check)
	$(PYTHON) -m ruff check $(SRC)
	$(PYTHON) -m black --check $(SRC)

lint: ## no-upward-imports pre-commit hook (ruff lint runs in fmt-check)
	$(BIN)/pre-commit run no-upward-imports-in-business-modules --all-files

test: ## pytest; scope via PYTEST_ARGS=... (exit 5 = no tests = ok)
	@$(PYTHON) -m pytest $(PYTEST_ARGS); status=$$?; \
	  if [ $$status -eq 5 ]; then echo "(no tests collected)"; exit 0; fi; \
	  exit $$status

typecheck: ## mypy
	$(PYTHON) -m mypy $(SRC)

arch: ## lint-imports + §1 upward + §3 CLI tree (+ Django string-relations)
	$(BIN)/lint-imports
	$(PYTHON) scripts/check_upward_imports.py $$(find $(PKG) -name '*.py')
	$(PYTHON) scripts/check_cli_commands.py $(PKG)
	@if [ -f manage.py ]; then $(PYTHON) scripts/check_string_relations.py; \
	  else echo "arch: skipping check_string_relations (no manage.py — not a Django project)"; fi

docs: ## doc-coherence mechanical pre-pass (link / §N / vocabulary drift)
	$(PYTHON) scripts/check_docs.py

clean: ## Remove caches, *.pyc, .DS_Store, build artifacts (never the venv)
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type f -name '*.py[co]' -delete 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type f -name '.DS_Store' -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache .import_linter_cache \
	  build dist *.egg-info .coverage coverage.xml htmlcov

distclean: clean ## clean + remove the virtualenv
	rm -rf $(VENV)

# Obsidian sync — two modes, so a repo's outputs are browsable on a phone /
# other devices (the vault is iCloud- or Dropbox-synced). Both MIRROR into a
# per-repo folder $(OBSIDIAN_DEST)/<org>-<repo>/ — the vault matches the repo
# and holds nothing extra. `obsidian-data` mirrors $(DATA_DIR)/ → .../data/;
# `obsidian-docs` collects every all-uppercase *.md ([A-Z]+.md — README,
# standards docs, ...) anywhere in the repo, preserving tree structure, into
# .../docs/. `make obsidian` lists the modes; each no-ops when there's nothing
# to sync.
OBSIDIAN_DEST ?= $(HOME)/Obsidian
DATA_DIR      ?= .data
# Per-repo vault folder <org>-<repo>, derived from `git remote get-url origin`.
# Override if your vault layout differs: make obsidian-docs OBSIDIAN_SLUG=foo
OBSIDIAN_SLUG  = $(shell git remote get-url origin 2>/dev/null | sed -E 's|\.git$$||; s|^.*[/:]([^/:]+)/([^/]+)$$|\1-\2|')

obsidian: ## list the obsidian sync modes (obsidian-data / obsidian-docs)
	@echo "Obsidian sync — mirror into $(OBSIDIAN_DEST)/<org>-<repo>/"
	@echo "  make obsidian-data   mirror $(DATA_DIR)/ → <org>-<repo>/data/"
	@echo "  make obsidian-docs   mirror all [A-Z]+.md (whole repo) → <org>-<repo>/docs/"

obsidian-data: ## mirror $(DATA_DIR)/ into <org>-<repo>/data/ in the vault
	@test -d "$(DATA_DIR)" || { echo "no $(DATA_DIR)/ to sync — nothing to do"; exit 0; }; \
	 slug='$(OBSIDIAN_SLUG)'; \
	 test -d "$(OBSIDIAN_DEST)" || { echo "$(OBSIDIAN_DEST) not found (vault symlink missing?)"; exit 1; }; \
	 test -n "$$slug" || { echo "cannot derive <org>-<repo> from git remote 'origin'"; exit 1; }; \
	 mkdir -p "$(OBSIDIAN_DEST)/$$slug/data"; \
	 rsync -a --delete --prune-empty-dirs "$(DATA_DIR)/" "$(OBSIDIAN_DEST)/$$slug/data/"

# Mirror by construction: wipe the docs subtree, then copy exactly the selected
# files. rsync --delete cannot prune with --files-from, so a fresh copy is the
# reliable mirror. dest is the dedicated <org>-<repo>/docs subtree, guarded by
# the non-empty-slug + vault-exists checks before the rm.
obsidian-docs: ## mirror all [A-Z]+.md (whole repo, tree preserved) into <org>-<repo>/docs/
	@files=$$(find . -path ./.git -prune -o -path './$(VENV)' -prune -o -type f -name '*.md' -print | grep -E '/[A-Z]+\.md$$' | sed 's|^\./||'); \
	 test -n "$$files" || { echo "no [A-Z]+.md files to sync — nothing to do"; exit 0; }; \
	 slug='$(OBSIDIAN_SLUG)'; \
	 test -d "$(OBSIDIAN_DEST)" || { echo "$(OBSIDIAN_DEST) not found (vault symlink missing?)"; exit 1; }; \
	 test -n "$$slug" || { echo "cannot derive <org>-<repo> from git remote 'origin'"; exit 1; }; \
	 dest="$(OBSIDIAN_DEST)/$$slug/docs"; \
	 rm -rf "$$dest"; mkdir -p "$$dest"; \
	 printf '%s\n' "$$files" | rsync -a --files-from=- . "$$dest/"
