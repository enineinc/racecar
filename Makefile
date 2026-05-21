# Root Makefile — self-verification for this framework's own docs and scripts.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so tooling resolves to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif
PYTHON := $(if $(VENV),$(VENV)/bin/python3,python3)

.PHONY: install install-deps expert expert-uninstall check-docs check-brief test check help

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

check-brief:
	$(PYTHON) llm-summary/scripts/check_brief.py

test:
	$(PYTHON) -m pytest arch-coherence/tests doc-coherence/tests llm-summary/tests scripts/tests

check: check-docs test check-brief

help:
	@echo "make install          - install python deps then bootstrap into Claude Code config"
	@echo "make install-deps     - install python deps from pyproject.toml dev group"
	@echo "make expert           - install the optional racecar-expert-mode overlay (skill symlink + CLAUDE.md pointer)"
	@echo "make expert-uninstall - remove the racecar-expert-mode overlay"
	@echo "make check-docs       - run the mechanical pre-pass on this repo's own docs"
	@echo "make check-brief      - validate the racecar-llm-summary brief bundle at docs/<repo>/<REPO>.md"
	@echo "make test         - run the test suites under each skill"
	@echo "make check        - run check-docs, test, and check-brief"
