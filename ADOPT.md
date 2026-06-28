# Adopting racecar in a project

Three paths: **new project** (scaffold from scratch), **existing project with a local racecar clone** (sync scripts locally), and **existing project without a local clone** (sync scripts remotely via curl).

## Picking a shape

Pick the shape that matches your project's layout:

| Shape | When to pick it |
|---|---|
| `src` | Plain installable Python library; no Django |
| `src+server` | Library (`src/<pkg>`) plus a Django server (`server/`) that imports it |
| `server` | Standalone Django (`server/`), no separately-installable library |

Full shape reference: [`arch-coherence/PACKAGING.md`](arch-coherence/PACKAGING.md) §"Scope".

## Path A: new project

**1. Scaffold**

From the racecar repo root:

    make init ARGS="--shape src+server --name myproject --package myproject --dest /path/to/new/repo"

Substitute `src+server`, `myproject`, and the dest path for your project. Optional flags: `--version`, `--description`, `--author`, `--email`. See `python scripts/init_project.py --help`.

The scaffolder writes: the Makefile (shape vars set), library pyproject (placeholders filled), server pyproject (Shape `src+server` only), `.pre-commit-config.yaml`, `.gitignore`, a skeleton `__init__.py`, and the canonical check scripts under `scripts/`.

**2. Edit the importlinter contract**

Open the library pyproject (`src/pyproject.toml` for Shape `src+server`, `pyproject.toml` for others). Find `[[tool.importlinter.contracts]]` and replace the placeholder layer list with your real package layout. A fresh project with one package is fine as a starting point; add layers as the package grows.

**3. Install dev dependencies**

    cd /path/to/new/repo
    make install-dev

This creates `.venv/`, upgrades pip to 25.1+, and installs the library in editable mode plus the full dev tool set.

**4. Enable git hooks**

    .venv/bin/pre-commit install

Run from the repo root. This wires the pre-commit hooks declared in `.pre-commit-config.yaml` so they run on every `git commit`.

**5. Verify**

    make check-full

All checks should pass on a fresh scaffold. If any fail, they are real findings in the skeleton code or config — fix before proceeding.

## Path B: existing project

For a repo already set up with racecar conventions but whose check scripts are behind the current racecar version.

**Sync the scripts** (from the racecar repo root):

    make sync-scripts DEST=/path/to/existing/repo

Preview without writing first:

    make sync-scripts DEST=/path/to/existing/repo DRY_RUN=--dry-run

The sync copies only the canonical check scripts into `<dest>/scripts/`. It leaves any project-specific scripts in that directory untouched. Unchanged scripts are reported but not rewritten.

**Optionally deliver missing scaffolding** — add `--templates` (direct invocation):

    python3 scripts/sync_scripts.py --dest /path/to/existing/repo --templates

This creates `Makefile`, `.pre-commit-config.yaml`, `.gitignore`, and `scripts/install_system_deps.sh` **only where missing** — existing files are never overwritten, because templates are per-project-customized (drift in an existing Makefile is `check_packaging.py`'s to report, not sync's to clobber). A freshly-created Makefile needs its shape variables set before use.

After syncing, run `make check-full` in the target repo and commit the updated scripts.

## Path C: remote sync (no local racecar clone)

For a repo that wants to update its check scripts without having racecar checked out locally. Fetches scripts directly from GitHub using only the Python stdlib.

**Run in one step from the adopter repo root:**

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest .

**Pin to a specific release:**

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest . --ref v0.13.0

**Preview without writing:**

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest . --dry-run

**Also deliver missing scaffolding** (create-if-missing, never overwrites):

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest . --templates

The `--ref` argument accepts any branch name, tag, or full commit SHA. Default is `main` (latest). Pin to a tag for reproducible updates.

After syncing, run `make check-full` and commit the updated scripts.

This curl one-liner **is the delivery mechanism**: any repo, any machine with Python and curl, no racecar clone. `/racecar-normalize` invokes it automatically as its sync step; running it by hand is the same operation.

## Makefile help grouping convention

The canonical `help` target sorts targets alphabetically within each group. Racecar canon targets (install, check, fmt, lint, arch, docs, test, clean, etc.) appear ungrouped at the top. Project-specific targets are grouped under `##@` section markers:

    ##@ Django
    run: ## runserver on http://localhost:8000
    ...

    ##@ Project
    my-custom-target: ## description
    ...

Add `##@` markers only for targets that are not racecar canon. Leave canon targets ungrouped.

## Keeping in sync

The canonical check scripts are the source of truth. When racecar updates them, update each adopter repo using Path B or Path C and commit the results. Path B requires a local racecar clone; Path C works from any machine with Python and curl.

The Makefile and pyproject templates have a **create-if-missing** path only (`--templates`); an existing copy is never overwritten by any sync. To pick up template changes in an existing file, review `diff -u templates/classic/Makefile <repo>/Makefile` manually and merge intentionally — or fix finding-by-finding from `check_packaging.py` output, which names the expected value per violation.
