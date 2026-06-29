# Root Makefile — self-verification for this framework's own docs and scripts.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so tooling resolves to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif
PYTHON := $(if $(VENV),$(VENV)/bin/python3,python3)

.PHONY: install install-deps install-dev expert expert-uninstall doctor check-docs check-subsystem-docs check-changelog check-brief lint test check demo init sync-scripts sync-remote-test clean distclean obsidian obsidian-data obsidian-docs help

install: install-deps
	./install

expert:
	$(PYTHON) scripts/expert_mode.py install

expert-uninstall:
	$(PYTHON) scripts/expert_mode.py uninstall

install-deps:
	$(PYTHON) -m pip install -q --group dev

install-dev: install-deps
	$(PYTHON) -m pip install -q --group django

# Verify the load mechanism layer by layer (files, wiring, hook execution,
# transcript). Exit 1 on any deterministic failure. FIX=--fix repairs wiring
# and creates missing symlinks (never clobbers).
doctor:
	$(PYTHON) scripts/doctor.py $(FIX)

check-docs:
	$(PYTHON) doc-coherence/scripts/check_docs.py

check-subsystem-docs:
	$(PYTHON) doc-coherence/scripts/check_subsystem_docs.py

check-changelog:
	$(PYTHON) scripts/check_changelog.py

check-brief:
	$(PYTHON) llm-summary/scripts/check_brief.py

# Lint racecar's own delivered scripts to zero pylint findings. Scope: the
# production check + sync/install scripts under scripts/ and each lens's
# scripts/ dir — the code racecar ships and runs. Test files are excluded:
# their sys.path sibling imports and protected-access on the modules under test
# are inherent to test scaffolding, not defects. Caps that are genuinely too
# tight are raised (with rationale) in [tool.pylint] in pyproject.toml, never
# disabled. The rcfile carries the cap and message-control config.
LINT_SCRIPTS := $(shell find scripts doc-coherence/scripts llm-summary/scripts arch-coherence/scripts -name '*.py' -not -path '*/tests/*')
lint:
	$(PYTHON) -m pylint --rcfile pyproject.toml $(LINT_SCRIPTS)

test:
	$(PYTHON) -m pytest arch-coherence/tests doc-coherence/tests llm-summary/tests scripts/tests

check: check-docs check-subsystem-docs check-changelog lint test check-brief

# One-command "see the value" demo. Runs the arch-coherence upward-import check
# against examples/ — a deliberately-broken sample project (see examples/README.md)
# — and presents the check's nonzero exit as SUCCESS: the demo succeeds by
# demonstrating the catch. Always exits 0.
DEMO_DIR     := examples
ARCH_SCRIPTS := $(abspath arch-coherence/scripts)
# Absolute interpreter — the demo `cd`s into examples/, so a venv-relative
# python path would no longer resolve from there.
DEMO_PYTHON  := $(if $(VENV),$(abspath $(VENV))/bin/python3,python3)
demo:
	@echo "racecar demo — running the upward-import check against $(DEMO_DIR)/ ..."
	@echo "  ($(DEMO_DIR)/ is DELIBERATELY broken; the check is supposed to catch it)"
	@echo
	@out=$$(cd $(DEMO_DIR) && PYTHONPATH="$(ARCH_SCRIPTS)" \
	    $(DEMO_PYTHON) "$(ARCH_SCRIPTS)/check_upward_imports.py" \
	    $$(find src -name '*.py') 2>&1); status=$$?; \
	  echo "$$out"; \
	  count=$$(printf '%s\n' "$$out" | grep -c 'upward import forbidden' || true); \
	  echo; \
	  if [ $$status -ne 0 ]; then \
	    echo "racecar caught $$count intentional violation(s) in $(DEMO_DIR)/ — demo succeeded."; \
	    echo "This is the catch racecar gives you on real code. See examples/README.md."; \
	  else \
	    echo "racecar demo FAILED: the check passed, but examples/ is supposed to be broken."; \
	    echo "Did someone fix the intentional violation? See examples/README.md."; \
	    exit 1; \
	  fi

# Scaffold a new racecar-conforming project from templates/classic/. Pass
# scaffolder flags via ARGS, e.g.:
#   make init ARGS="--shape src --name widgets --package widgets --dest /tmp/widgets"
init:
	$(PYTHON) scripts/init_project.py $(ARGS)

# Sync the canonical check scripts into an existing adopter repo (local racecar clone required).
# Usage: make sync-scripts DEST=/path/to/repo
# Adds --dry-run to preview without writing: make sync-scripts DEST=... DRY_RUN=--dry-run
# Adds missing scaffolding (create-if-missing): make sync-scripts DEST=... TEMPLATES=--templates
sync-scripts:
	$(PYTHON) scripts/sync_scripts.py --dest $(DEST) $(DRY_RUN) $(TEMPLATES)

# Smoke-test the remote sync script against a temp dir to verify it fetches from GitHub.
# REF defaults to main; override with: make sync-remote-test REF=v0.6.0
REF ?= main
sync-remote-test:
	@tmpdir=$$(mktemp -d) && mkdir -p "$$tmpdir/scripts" && \
	  echo "sync_remote smoke test — fetching ref=$(REF) into $$tmpdir" && \
	  $(PYTHON) scripts/sync_remote.py --dest "$$tmpdir" --ref $(REF) && \
	  count=$$(ls "$$tmpdir/scripts/" | wc -l | tr -d ' ') && \
	  echo "$$count scripts written to $$tmpdir/scripts/" && \
	  rm -rf "$$tmpdir"

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
	@echo "make install-dev   - install-deps plus the django stack (pylint-django, DOT, webauthn) for generated-output lint tests"
	@echo "make expert           - install the optional racecar-expert-mode overlay (skill symlink + CLAUDE.md pointer)"
	@echo "make expert-uninstall - remove the racecar-expert-mode overlay"
	@echo "make doctor [FIX=--fix] - verify install/wiring/load layer by layer; --fix repairs wiring"
	@echo "make check-docs       - run the mechanical pre-pass on this repo's own docs"
	@echo "make check-subsystem-docs - verify every major subsystem in an import-linter layer owns README + CLAUDE"
	@echo "make check-brief      - validate the racecar-llm-summary brief bundle at docs/summary/<REPO>.md"
	@echo "make lint          - pylint racecar's own delivered scripts to zero findings (tests excluded)"
	@echo "make test         - run the test suites under each skill"
	@echo "make check        - run check-docs, check-subsystem-docs, lint, test, and check-brief"
	@echo "make demo         - run a racecar check against examples/ and show it catching a real violation"
	@echo "make init ARGS=.. - scaffold a new conforming project from templates/classic/ (see scripts/init_project.py --help)"
	@echo "make sync-scripts DEST=<path> [TEMPLATES=--templates] - sync check scripts into an adopter repo; --templates adds missing scaffolding"
	@echo "make sync-remote-test [REF=<ref>] - smoke-test remote sync by fetching scripts from GitHub into a temp dir"
	@echo "make clean        - remove caches and build artifacts (never the venv)"
	@echo "make distclean    - clean + remove the virtualenv"
	@echo "make obsidian      - list the obsidian sync modes (obsidian-data / obsidian-docs)"
	@echo "make obsidian-data - mirror $(DATA_DIR)/ into the vault under <org>-<repo>/data/"
	@echo "make obsidian-docs - mirror all [A-Z]+.md (whole repo) into <org>-<repo>/docs/"
