---
name: racecar-normalize
description: Sync canonical racecar check scripts into the current project, run every checker, and report every finding so the user knows what to fix. Use when asked to "normalize for racecar", "validate against racecar", "what does racecar find in this project", "bring this project up to racecar standards", or any phrasing that implies auditing or updating an existing project against racecar conventions.
---

# racecar-normalize

Syncs the canonical racecar check scripts into the current project, runs every checker plus `lint-imports`, and reports every finding. Does not fix anything without explicit consent per finding.

## Step 1: locate the project root and identify the shape

`<project_root>` is the directory containing the `Makefile`. Default to `.`.

These files and directories are **always at `<project_root>`**, regardless of shape:

    Makefile
    .venv/
    scripts/
    .gitignore
    .pre-commit-config.yaml
    CHANGELOG.md

The shape determines where the **library pyproject** lives. Identify it from the filesystem before running any checker:

| Shape | Signal | Library pyproject |
|-------|--------|-------------------|
| `src` | `pyproject.toml` at root; no `pypkg/`, no `manage.py`, no `djapp/` | `pyproject.toml` |
| `pypkg` | `pypkg/src/pyproject.toml` exists; no `djapp/` | `pypkg/src/pyproject.toml` |
| `pypkg+djapp` | `pypkg/src/pyproject.toml` AND (`djapp/manage.py` or `djapp/pyproject.toml`) | `pypkg/src/pyproject.toml` |
| `djapp` | `pyproject.toml` at root AND (`manage.py` or `djapp/manage.py`) | `pyproject.toml` |

Shape `djapp` has two placements (PACKAGING.md §"Scope"): **nested** (`djapp/manage.py` — source lives in `djapp/`) and **standalone** (`manage.py` at root — the whole repo is the Django project, e.g. an `apps/` + `config/` layout). Note which placement applies; it changes `<src>` below.

All checkers are invoked with `<project_root>` as their root reference (via `--root <project_root>` where the flag exists, or by running from `<project_root>` via the absolute-path convention below). Never `cd` into a subdirectory to run a checker.

## Step 2: sync the check scripts (and missing scaffolding)

Check whether a local racecar checkout is accessible by resolving the symlink at `~/.claude/skills/racecar-normalize` and looking for `scripts/sync_scripts.py` one level up from `normalize/`. If found, use the local sync:

    python3 <racecar_root>/scripts/sync_scripts.py --dest <project_root> --templates

Otherwise fetch remotely:

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest <project_root> --templates

`--templates` additionally delivers any **missing** scaffolding (`Makefile`, `.pre-commit-config.yaml`, `.gitignore`, `scripts/install_system_deps.sh`) — create-if-missing only; existing files are never overwritten. A freshly-created Makefile has its shape variables (`SRC`, `PKG`, `DJAPP`, `LIB_PYPROJECT`) unset — set them per the Step 1 shape before running any `make` target, and tell the user you did.

Report the sync output verbatim (created / updated / unchanged / exists per file).

## Step 3: run the checkers

Resolve `<scripts>` as `<project_root>/scripts` once. Use absolute paths for every invocation. Never `cd` into a subdirectory -- CWD must not matter.

    python <scripts>/check_upward_imports.py --root <project_root> $(find <project_root>/<src> -name '*.py' -not -path '*/migrations/*')
    python <scripts>/check_cli_commands.py <pkg>          # skip if no __main__.py exists anywhere
    python <scripts>/check_packaging.py --root <project_root>
    python <scripts>/check_face_orchestration.py --root <project_root>   # no-ops without [tool.racecar.faces]; Findings only
    python <scripts>/check_dj_model_ref_as_string.py     # Django only: skip if no manage.py
    python <scripts>/check_docs.py
    python <scripts>/check_todo_format.py
    python <scripts>/check_claude_shape.py
    python <scripts>/check_file_placement.py

`<src>` is the source directory from the shape table: `src` for shape `src`, `pypkg/src` for shape `pypkg`/`pypkg+djapp`, `djapp` for nested shape `djapp`. For **standalone** shape `djapp` (`manage.py` at root) there is no single `<src>` directory — enumerate the top-level Python package directories (direct children of `<project_root>` containing `__init__.py` or recognizable Django app/config layout, e.g. `apps/`, `config/`, `common/`) and pass those; never scan `scripts/`, `venv/`, `.venv/`, `migrations/`, or test fixtures.

For `check_dj_model_ref_as_string.py`: if `manage.py shell` fails to start (missing dependency, misconfigured settings), report it as "skipped -- Django shell failed to start" and continue. Do not exit.

## Step 4: run lint-imports

After the checkers, attempt to run import-linter:

    lint-imports

Look for the binary at `<project_root>/<venv>/bin/lint-imports`, `<project_root>/.venv/bin/lint-imports`, or bare `lint-imports` on PATH (in that order). Run it from `<project_root>`. If not found, report "skipped -- lint-imports not installed" and continue.

If found but no `[[tool.importlinter.contracts]]` section exists in the library pyproject (location per shape table), report "skipped -- no import-linter contracts configured" and continue.

If found and contracts exist, include the full output in the report. A non-zero exit is a finding, not a fatal error -- continue to the report step.

## Step 5: check pre-commit wiring and system-deps

Check that the git hook is installed:

    test -f .git/hooks/pre-commit

If the file is absent, report it as a gap: "pre-commit hooks not installed -- run `pre-commit install` (or `make install-dev`)." Offer to run `pre-commit install` if the user consents.

Check the system-deps surface:

    test -x <project_root>/scripts/install_system_deps.sh

If absent or not executable, report it as a gap (Step 2 with `--templates` creates it). Also confirm the Makefile has a `system-deps` target wired to that script — `check_packaging.py` flags a missing target, but a target pointing at a nonexistent script is a finding to report here.

## Step 6: report findings

Emit a single consolidated report after all checkers have run. Group by checker. Within each checker, order: Blocker, then Finding, then Warning.

Format:

    ## check_packaging.py
    BLOCKER  pyproject.toml  [build-system].requires  must be ['setuptools>=64']; got ['setuptools>=61.0']
    FINDING  VERSION         deprecated-file           VERSION file is no longer canon; ...
    ...

    ## check_dj_model_ref_as_string.py
    SKIPPED — Django shell failed to start: ModuleNotFoundError: No module named 'oauth2_provider'

    ## lint-imports
    SKIPPED — no import-linter contracts configured

    ## check_docs.py
    OK — no findings

End with a summary line:

    Blockers: N  |  Findings: N  |  Skipped: N  |  Clean: N  |  lint-imports: passed/failed/skipped

## Step 7: offer to fix

After the report, ask the user which findings to address. Fix only what the user explicitly approves, one finding or checker at a time. Do not batch fixes without per-finding consent.

How to fix the two structural surfaces — reference, not invention:

- **Makefile findings** (missing targets, forbidden tools, `install-dev` gaps): read `<racecar_root>/templates/classic/Makefile` and port the missing target's recipe, adapting only the shape variables (`SRC`, `PKG`, `DJAPP`, `LIB_PYPROJECT`). Propose the diff target-by-target; do not rewrite the whole Makefile, and leave project-specific targets (under `##@` group markers) untouched.
- **pyproject findings** (canon values, missing `[tool.*]` blocks, dev-group drift): the canon values live in `arch-coherence/PACKAGING.md` (§6 dev tools, §7 tool config) and `check_packaging.py`'s output names the expected value per finding. Apply the named value; do not restyle anything the checker did not flag.

Both surfaces are per-project-customized, which is why sync never overwrites them — the fix path is always checker-finding → reference template/canon → minimal approved diff.
