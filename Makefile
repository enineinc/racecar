# Root Makefile — self-verification for this framework's own docs and scripts.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so tooling resolves to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif
PYTHON := $(if $(VENV),$(VENV)/bin/python3,python3)

.PHONY: install install-deps expert expert-uninstall check-docs check-subsystem-docs check-brief test check clean distclean obsidian obsidian-data obsidian-docs help

install: install-deps
	./install

expert:
	$(PYTHON) scripts/expert_mode.py install

expert-uninstall:
	$(PYTHON) scripts/expert_mode.py uninstall

install-deps:
	$(PYTHON) -m pip install --group dev

check-docs:
	$(PYTHON) doc-coherence/scripts/check_docs.py

check-subsystem-docs:
	$(PYTHON) doc-coherence/scripts/check_subsystem_docs.py

check-brief:
	$(PYTHON) llm-summary/scripts/check_brief.py

test:
	$(PYTHON) -m pytest arch-coherence/tests doc-coherence/tests llm-summary/tests scripts/tests

check: check-docs check-subsystem-docs test check-brief

# Remove derived caches/build artifacts only. Never touches the virtualenv
# (that is the explicit, separate `distclean`) and prunes .git + the venv so
# nothing inside them is removed.
clean:
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type f -name '*.py[co]' -delete 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -path ./.git -prune -o -path './$(VENV)' -prune -o \
	  -type f -name '.DS_Store' -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache .import_linter_cache \
	  build dist .coverage coverage.xml htmlcov

distclean: clean
	rm -rf $(VENV)

# Obsidian sync — make this repo's outputs browsable in an Obsidian vault
# (iCloud/Dropbox-synced). Both MIRROR into $(OBSIDIAN_DEST)/<org>-<repo>/ — the
# vault matches the repo and holds nothing extra. `obsidian-data` mirrors
# $(DATA_DIR)/ → .../data/; `obsidian-docs` collects every all-uppercase *.md
# ([A-Z]+.md — README, standards docs, ...) anywhere in the repo, preserving
# tree structure, into .../docs/. `make obsidian` lists the modes; each no-ops
# when there's nothing to sync.
OBSIDIAN_DEST ?= $(HOME)/Obsidian
DATA_DIR      ?= .data
# Per-repo vault folder <org>-<repo>, derived from `git remote get-url origin`.
OBSIDIAN_SLUG  = $(shell git remote get-url origin 2>/dev/null | sed -E 's|\.git$$||; s|^.*[/:]([^/:]+)/([^/]+)$$|\1-\2|')

obsidian:
	@echo "Obsidian sync — mirror into $(OBSIDIAN_DEST)/<org>-<repo>/"
	@echo "  make obsidian-data   mirror $(DATA_DIR)/ → <org>-<repo>/data/"
	@echo "  make obsidian-docs   mirror all [A-Z]+.md (whole repo) → <org>-<repo>/docs/"

obsidian-data:
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
obsidian-docs:
	@files=$$(find . -path ./.git -prune -o -path './$(VENV)' -prune -o -type f -name '*.md' -print | grep -E '/[A-Z]+\.md$$' | sed 's|^\./||'); \
	 test -n "$$files" || { echo "no [A-Z]+.md files to sync — nothing to do"; exit 0; }; \
	 slug='$(OBSIDIAN_SLUG)'; \
	 test -d "$(OBSIDIAN_DEST)" || { echo "$(OBSIDIAN_DEST) not found (vault symlink missing?)"; exit 1; }; \
	 test -n "$$slug" || { echo "cannot derive <org>-<repo> from git remote 'origin'"; exit 1; }; \
	 dest="$(OBSIDIAN_DEST)/$$slug/docs"; \
	 rm -rf "$$dest"; mkdir -p "$$dest"; \
	 printf '%s\n' "$$files" | rsync -a --files-from=- . "$$dest/"

help:
	@echo "make install          - install python deps then bootstrap into Claude Code config"
	@echo "make install-deps     - install python deps from pyproject.toml dev group"
	@echo "make expert           - install the optional racecar-expert-mode overlay (skill symlink + CLAUDE.md pointer)"
	@echo "make expert-uninstall - remove the racecar-expert-mode overlay"
	@echo "make check-docs       - run the mechanical pre-pass on this repo's own docs"
	@echo "make check-subsystem-docs - verify every major subsystem in an import-linter layer owns README + CLAUDE"
	@echo "make check-brief      - validate the racecar-llm-summary brief bundle at docs/<repo>/<REPO>.md"
	@echo "make test         - run the test suites under each skill"
	@echo "make check        - run check-docs, check-subsystem-docs, test, and check-brief"
	@echo "make clean        - remove caches and build artifacts (never the venv)"
	@echo "make distclean    - clean + remove the virtualenv"
	@echo "make obsidian      - list the obsidian sync modes (obsidian-data / obsidian-docs)"
	@echo "make obsidian-data - mirror $(DATA_DIR)/ into the vault under <org>-<repo>/data/"
	@echo "make obsidian-docs - mirror all [A-Z]+.md (whole repo) into <org>-<repo>/docs/"
