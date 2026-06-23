# Changelog

All notable changes to racecar are recorded here, in the style of
[Keep a Changelog](https://keepachangelog.com). racecar is pre-1.0, so a minor
bump may carry breaking changes for adopters; those are marked **Breaking**.

## 0.10.2 - 2026-06-23

### Changed
- **The llm-summary brief no longer carries `target.sha`.** The frontmatter snapshot
  SHA was circular (a brief is written before its own commit exists, so it could only
  ever name the parent) and low-value to the brief's reader, who asks the file what the
  system is, not which commit. `check_brief` no longer requires or validates it;
  `target.date` and `generator.version` remain as provenance. An existing brief that
  still carries a sha validates fine, the field is ignored.

## 0.10.1 - 2026-06-23

### Fixed
- **The Django string-relation gate no longer requires Django to boot.**
  `check_dj_model_ref_as_string` booted `manage.py shell` eagerly to resolve
  `INSTALLED_APPS`, so an architecture gate (a static import-graph concern) hard-failed
  whenever an inactive Django scaffold could not fully boot, for example a djapp that
  lists dev-only apps it does not install. The boot is now lazy: the static AST walk
  runs first, Django is booted only to classify violations that exist, and a boot that
  does not complete degrades to an UNCLASSIFIED report (exit 1 on the finding) instead
  of a configuration error (exit 2). A clean tree never boots. This restores
  discrete-first: the deterministic pass does all it can before any runtime step.
  Surfaced by a real adopter whose djapp could not boot in dev.

## 0.10.0 - 2026-06-23

The shape-and-Makefile release: the project shape is now inferred from the
filesystem, the Makefile is split into an owned thin file plus canonical
`racecar.mk`, and a speculative shared-context module was removed. Several
changes are breaking for existing adopters; `racecar-upgrade` reconciles them
without clobbering the owned `Makefile`.

### Added
- **Self-detecting `racecar.mk`.** A single canonical file, identical in every
  repo, computes the project shape (`src` / `pypkg` / `pypkg+djapp` / `djapp`)
  from the layout at make-time and selects the matching source variables, falling
  back to stock for any unrecognized layout (PACKAGING.md §7).
- **The Makefile fold.** Projects keep an owned thin `Makefile` that
  `include`s `racecar.mk`; project customization lives in the owned Makefile,
  canon lives in `racecar.mk`. There is no override registry.
- **Manifest-driven remote sync.** `sync_remote.py` (the no-clone `curl | python`
  path) now fetches a generated, drift-tested `scripts/racecar-manifest.txt`, so
  it delivers exactly what local `make sync` delivers, including checker
  implementation packages and the Django-only checks.
- **`make lint` over racecar's own scripts.** The framework now passes its own
  pylint bar at 10/10; the tooling is no longer self-exempt.
- **`pylint-django` as a canonical Django dev tool.** Required in the django group
  for any repo with a `manage.py`; `racecar.mk`'s lint loads it on the djapp only
  (`--load-plugins=pylint_django`), so a Django app stops false-positiving on every
  ORM idiom against the plain library config.
- **A `print-%` target in `racecar.mk`** (`make -s print-LIB_PYPROJECT`), so the
  pre-commit hooks read shape-derived config through Make.

### Changed
- **Breaking: shape is governed by what is on disk, not declared.** There is no
  `[tool.racecar].shape` entry; the Make build and `check_packaging.detect_shape`
  infer it identically, pinned by a coherence test.
- **Breaking: the Makefile contract.** Per-shape Makefile overrides are gone;
  upgrade replaces a project's build wiring with the owned-Makefile + `racecar.mk`
  split. `racecar-upgrade` performs this without touching your customization.
- `check_packaging` is reorganized into a thin entry plus a one-audit-per-module
  `check_packaging_rules/` package, composed by a plain `run_all`.
- Documentation checks are reference-driven (reachability from README / CLAUDE /
  SKILL seeds), not a fixed taxonomy. Dense lens content moved to named topic docs
  (`AXIOMS.md`, `WORKFLOW.md`, `PROTOCOL.md`, `SPEC.md`) with human-readable
  resolver READMEs.

### Fixed
- **Django is recognized by `manage.py`, never a bare `djapp/` directory.** A
  `djapp/` holding only a pyproject is no longer mis-detected as Django. Fixed in
  `detect_shape`, `racecar.mk`, and `init`.
- **The makefile-fold corruption.** `init --shape djapp` shipped a scaffold the
  build mis-detected as `src`, so `make sync` rewrote `racecar.mk` to the wrong
  shape; the self-detecting `racecar.mk` makes this impossible.
- **Remote/local sync drift.** `sync_remote` and `sync_scripts` carried divergent
  hardcoded script lists, and the remote path could not deliver packages; both now
  read one manifest.
- **The Makefile fold broke the config-deriving pre-commit hooks.** isort, black,
  import-linter, and validate-pyproject grepped the owned `Makefile` for
  `LIB_PYPROJECT` / `DJAPP`, which the fold moved into `racecar.mk` (computed from
  the layout); they failed with "Could not read any configuration." They now read
  the resolved values via `make -s print-X`.
- **The Django string-relation gate was a false green on `pypkg+djapp`.**
  `check_dj_model_ref_as_string` looked for its pyproject, its `manage.py`, and the
  packages it walks all at the repo root, where on `pypkg+djapp` none of them are, so
  it skipped silently and passed over real broken models. It now takes the contract
  (library pyproject) and `manage.py` from `detect_shape` and globs each
  `root_package` from the tree, finding each wherever it lives. A good/bad
  `pypkg+djapp` fixture pair guards it. Surfaced by a real adopter upgrade.

### Removed
- **Breaking: `check_claude_shape`** (the last fixed-taxonomy documentation gate).
- **`repo_context.py`**, a shared role-map module that had no consumers; its
  source-root helpers returned to the faces detector, their origin.
- Stale synced scripts are now removed from an adopter on sync (so a repo that
  received `repo_context.py` has it cleaned up by the next `racecar-upgrade`).
