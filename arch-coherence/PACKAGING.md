# Packaging & Tooling — racecar standard

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

This file is the project-shell counterpart to [`PYTHON.md`](PYTHON.md). PYTHON.md governs how Python code is organized inside `src/`; this file governs the build, install, lock, and verify shell *around* `src/`.

## Scope: one opinion, four supported project shapes

PACKAGING.md is **one opinion** of how to package a Python project. It is opinionated, not universal — a uv-shop has a different defensible opinion — but within racecar this opinion is the standard.

The opinion accommodates four project shapes. The choice of shape is local to the project; the rest of the opinion (PEP 621 + PEP 735 pyproject as sole source of truth, `make check-full` as CI gate, the dev tool set, `.venv/` discipline, no VC-backed tooling) is identical across all four. From the shape, `racecar.mk` sets several variables that the rest of the build reads: `SRC` (where the Python source lives), `PKG` (the importable package path used by audits), `DJAPP` (the Django app directory, empty when not Django), `LIB_PYPROJECT` (path to the library pyproject), and `DJAPP_PYPROJECT` (path to the djapp pyproject, only for Shape pypkg+djapp).

### How the shape is determined: governed by what is on disk

The shape is **not declared anywhere**. It is a function of the project's layout: racecar reads which files exist and computes the shape from them. This is deliberate. The directory structure already *is* the statement of shape, so a separate declared value (a `shape = "..."` key) would be a second home for the same fact, which is the drift this framework exists to prevent. Lay down the canonical files for a shape and the project *is* that shape; there is no token to also set, none to forget, and none to let go stale.

The shape is the result of this ordered decision (first match wins). Read "`X` exists" as "the path `X` is present in the repo":

1. `pypkg/src/pyproject.toml` exists **and** a `djapp/` tree exists → **`pypkg+djapp`**
2. `pypkg/src/pyproject.toml` exists → **`pypkg`**
3. root `pyproject.toml` exists **and** Django is present → **`djapp`**
4. root `pyproject.toml` exists → **`src`**
5. none of the above → **stock** (no recognized shape: neutral defaults, see §7)

where a **`djapp/` tree** means `djapp/manage.py` exists, and **Django is present** means a root `manage.py` or a `djapp/` tree exists. The marker is always `manage.py`, never a bare `djapp/` directory: a `djapp/` holding only a pyproject (no `manage.py`) is not a runnable Django app, so it does not make the project a djapp.

That rule lives in exactly two places, held in lockstep by a coherence test: `arch-coherence/scripts/check_packaging.py` (`detect_shape`, used by the audit) and `templates/classic/racecar.mk` (the same decision in Make, so the build is self-contained — see §7). It is duplicated on purpose, not shared: the build must be able to determine its own shape with nothing but `make` present (no Python, no venv), and a foundation that needs an external process to know what it is would not be a foundation. The cost of the duplication is bounded by the coherence test, not waved away.

**Shapes are orthogonal to faces.** This file's shape axis answers *how the project is packaged*; the *faces axis* (how the one library is exposed: `cli` / `api` / `mcp` / `django`) is a separate concern with its own home in [`FACES.md`](FACES.md). A `src`-shape project can be `lib + cli + mcp`; the `djapp` shape is one packaging of the `django` face. Do not conflate the two axes; see [`FACES.md`](FACES.md) §8.

| Shape | When to pick it | Library pyproject | djapp pyproject | `SRC` | `PKG` | `DJAPP` |
|---|---|---|---|---|---|---|
| **`src`** | Plain installable Python package; no Django | `pyproject.toml` (root) | — | `src` | `src/<pkg>` | *(unset)* |
| **`pypkg`** | Installable Python package nested for future expansion; no Django yet | `pypkg/src/pyproject.toml` | — | `pypkg/src` | `pypkg/src/<pkg>` | *(unset)* |
| **`pypkg+djapp`** | Shared installable Python package *plus* a Django app that imports it | `pypkg/src/pyproject.toml` | `djapp/pyproject.toml` | `pypkg/src` | `pypkg/src/<pkg>` | `djapp` |
| **`djapp`** | Straight Django, no separately-installable package | `pyproject.toml` (root) | — | `djapp` | `djapp/<app>` | `djapp` |

Shape `djapp` has two placements, distinguished by where `manage.py` sits — both are the same shape, same library pyproject at root, same canon:

- **Nested** — `djapp/manage.py`; the table row above (`SRC=djapp`, `DJAPP=djapp`, `PKG=djapp/<app>`).
- **Standalone** — `manage.py` at repo root; the whole repo *is* the Django project (e.g. an `apps/` + `config/` layout). `racecar.mk` sets `SRC=.` and leaves `DJAPP` empty (with `SRC=.` the whole tree is already covered), `PKG` defaults to `.`; narrow `PKG` to the actual Django package directories with a `:=` override in the owned `Makefile`. Both placements are the same `djapp` shape; `racecar.mk` and `check_packaging.py` recognize either.

Invariants across all four shapes — these never move:

- One **library pyproject** per project, with the canonical `[project]` table, `[build-system]`, `[dependency-groups].dev` (PEP 735), and all `[tool.*]` configurations (`black`, `isort`, `pylint`, `pytest`, `mypy`, `coverage`, `importlinter`). Its location varies by shape (see table) but its contents are uniform.
- `Makefile`, `CHANGELOG.md`, `.gitignore`, `.pre-commit-config.yaml`, `scripts/` at repo root.
- `.venv/` at repo root. One venv per project regardless of shape.
- All tool invocations in the Makefile pass `--config` / `--rcfile` / `--config-file` / `-c` flags pointing at `LIB_PYPROJECT`. Tools do not auto-discover the library pyproject; the Makefile names it explicitly.

What changes between shapes:

- The location of the library pyproject (per the table).
- The presence and location of the djapp pyproject (only Shape pypkg+djapp).
- Whether a `requirements.txt` lockfile is committed at all — it's **optional** (see §5). If committed, the standard location is alongside the pyproject (`requirements.txt` at root for shapes `src`/`djapp`, `pypkg/src/requirements.txt` for `pypkg`/`pypkg+djapp`; `pypkg+djapp` may additionally have `djapp/requirements.txt`).
- The Makefile's `SRC`, `PKG`, `DJAPP`, `LIB_PYPROJECT`, `DJAPP_PYPROJECT` values.
- For Shape `pypkg+djapp` and `djapp`: presence of `djapp/manage.py` triggers the Django-specific audit (`scripts/check_dj_model_ref_as_string.py`) and pre-commit hook automatically.

Versioning details (library-only version in `[project].version`; djapp pyproject has no `[project]` block and no version) are covered in §8.

This opinion does not accommodate everything. uv-shops, Bazel monorepos, src-on-top layouts without `src/`, and pyproject-at-package-root layouts other than `pypkg/src/` are deliberately not supported. A project adopting this opinion picks one of the four shapes and commits.

## What is and isn't institutional canon

**What this is.** Mainstream modern Python practice — the PEP-defined parts (517/518/621 packaging, 735 dependency groups, 405 virtualenv, 484 typing) and the de facto community tool stack that serious shops use today (black, isort, pylint, mypy, pytest, pytest-cov, pip-audit, pre-commit, validate-pyproject) — plus a thin racecar overlay: a specific `Makefile` contract with split `check` (fast) and `check-full` (parallel CI gate), the `scripts/` layout for racecar's own checkers, `import-linter` as a required architectural gate, and the Blocker/Finding severity vocabulary.

**What this is not.** A novel framework, and not a universal Python standard. The PEPs are real PEPs; the community tools are the ones already on most projects' CI; the conventions (`.venv/` for the venv, `pyproject.toml` as sole source of truth for deps, `make check-full` as the CI gate) are widely recognized. A reviewer who walks into a racecar project from another modern Python shop will recognize 90% of the surface. The remaining 10% is racecar-specific and labeled as such where it appears below.

**How each section is labeled.** Sections that codify PEPs cite them. Sections that name de facto community tools say so. Sections that encode a racecar choice — the exact Makefile target list, the required hook IDs, the Blocker/Finding scheme — say so explicitly, so the next reviewer can tell what's institutional, what's mainstream, and what's racecar's call.

For language-agnostic coherence axioms, see [`README.md`](README.md). For Python module structure, imports, and `__init__.py` / `__main__.py` roles, see [`PYTHON.md`](PYTHON.md). For the CLI surface declared by `__main__.py`, see [`CLI.md`](CLI.md).

Sections are ordered as a DAG — most independent first, most dependent last.

## 1. Governance — PSF/PyPA and community OSS only

Racecar projects' packaging stack is governed by neutral institutions or by community OSS projects with established maintainership, not by venture-backed private companies. This is a structural choice, not a quality judgment: VC-backed tools may be excellent today, but their long-term direction depends on a board, not on community consensus. Lockfile formats, command interfaces, and PEP non-compliance can change to match the vendor's monetization roadmap. PSF/PyPA-track tools and mature community OSS are slow but structurally stable: they answer to the language community.

This rule is racecar's, not PSF's. PSF does not maintain a "banned tools" list. The tools below are real and their governance is verifiable; the *choice* to weight governance over ergonomics is racecar's call, and within racecar this opinion is binding.

**Tools used (institutional or mature community OSS):**

| Function | Tool | Governance |
|---|---|---|
| Installer | `pip` | PyPA |
| Build frontend | `build` | PyPA |
| Build backend | `setuptools` | PyPA |
| Virtual environment | stdlib `venv` (PEP 405) | CPython |
| Upload | `twine` | PyPA |
| Vulnerability scanner | `pip-audit` | PyPA |
| Pyproject validator | `validate-pyproject` | community OSS (Bravalheri) |
| Formatter | `black` | Łukasz Langa / PSF-adjacent; de facto community canon |
| Import sorter | `isort` | community OSS |
| Template formatter | `djhtml` | community OSS (Vens); Django/Jinja shapes only |
| Linter | `pylint` | community OSS |
| Type checker | `mypy` | community OSS; PEP 484 reference impl |
| Test runner | `pytest` | community OSS |
| DAG check | `import-linter` | community OSS |
| Git hooks | `pre-commit` | community OSS |

**Tools that are not canon and must not be adopted:**

- `uv` — Astral (Accel-backed)
- `ruff` — Astral (Accel-backed)
- Any future Astral product or other VC-backed packaging / linting / type-checking tool

The "10× faster" or "all-in-one workflow" pitch does not override this rule. Speed and ergonomics are real wins, but they are not worth single-vendor governance risk on the dependency-resolution path. Accept slower installs.

**Tools that are community OSS but parallel ecosystems** (poetry, pdm, hatch, pipenv): not canon. These maintain proprietary lockfile formats or non-PEP-compliant project models. They are not banned by the governance rule, but they fragment the ecosystem. Stay on pip.

## 2. Alternatives considered and avoided

The §1 canon is the result of an explicit comparison. Recording the trade-off here keeps the next reviewer from re-litigating it under the impression nobody thought it through.

### uv (Astral) — considered, avoided

The technical case for uv is real:

- 10–100× faster than pip on cold installs and lockfile resolution.
- Built-in lockfile (`uv.lock`) — closes the gap that PEP 665 was rejected and PEP 751 is still in draft.
- One binary covers pip + virtualenv + pip-tools + pyenv. Less surface to learn.
- Better resolver: finds compatible version sets in cases where pip falls back to "no solution" or takes minutes.
- Drop-in `uv pip install` interface is pip-compatible at the verb level.
- Standard venv on disk: a `uv venv` and a `python -m venv` are byte-equivalent and either tool can manage either.

The reasons it is not canon are structural, not technical:

- **Single-vendor governance.** Astral is a venture-backed private company (Accel-led, ~$20M raised). Long-term monetization plan is unproven. Realistic outcomes a long-horizon buyer must price in: Astral pivots, gets acquired, or sunsets uv; or moves key features (private indices, workspaces, cloud cache) into a paid tier; or diverges from PyPA standards in ways that hurt portability.
- **Lockfile lock-in.** `uv.lock` is a uv-specific format. pip cannot read it. `uv export -o requirements.txt` exists but loses platform-specific resolution detail in the translation.
- **Interface lock-in.** `uv add`, `uv sync`, `uv run`, `[tool.uv.workspace]`, `[tool.uv.sources]` have no pip equivalents. Once a project uses them, leaving uv means rewriting the project's tooling story.
- **Asymmetric escape hatch.** It is cheap to *try* uv (the venv it produces is the same venv pip would produce). It is expensive to *leave* uv once you have built infrastructure around its workflow.

The "single-vendor governance" concern is what tips the decision. pip is maintained by the PyPA, a community of maintainers operating under PSF oversight. Its governance is boring institutional OSS — slow, but extremely unlikely to disappear, change pricing, or take strategic direction from a board. That is structurally different from a YC-backed company's product, no matter how good the current code is. The decision is to accept slower installs in exchange for tooling that is not exposed to vendor-roadmap risk on the dependency-resolution path.

A racecar project may not introduce a `[tool.uv.*]` block, `uv.lock`, `uv add`, `uv sync`, `uv run`, or `uv tool` — see §9 Enforcement.

### ruff (Astral) — considered, avoided

The technical case for ruff is similar to uv's: written in Rust, extremely fast, consolidates flake8 + pycodestyle + pyflakes + several plugin lints into one tool, increasingly absorbs isort and black's responsibilities too. Excellent rule coverage.

The reasons it is not canon are the same as uv's: Astral, VC-backed, single-vendor governance, interface lock-in (rule names, config schema). The §1 governance rule applies equally to ruff. Stay on `black` + `isort` + `pylint`.

A racecar project may not introduce a `[tool.ruff]` block or invoke `ruff` from the Makefile.

### poetry — considered, not canon

Created by Sébastien Eustace, community OSS, no VC governance. The governance concern in §1 does not apply.

The reason poetry is not canon is ecosystem fragmentation: `poetry.lock` is a proprietary lockfile format; `[tool.poetry]` is a non-PEP-621 project metadata block (poetry has been migrating toward PEP 621 but the legacy block is still in heavy use); `poetry install` resolves differently from pip in subtle ways. A project that adopts poetry leaves the pip ecosystem in practice.

Pip + pip-tools achieves the same outcome (declared deps + resolved lockfile + venv discipline) with PSF-track tooling. The marginal ergonomic win is not worth the ecosystem split.

### pdm — considered, not canon

PEP 621-compliant from day one, community OSS. Better PEP alignment than poetry. Still maintains its own lockfile format (`pdm.lock`) and its own resolver. Same fragmentation argument as poetry. Not canon.

### hatch — considered, not canon

Hatch is part of the PyPA ecosystem (it's PyPA-maintained), so the governance argument *favors* it. Its primary roles are build backend (`hatchling`) and project/environment management.

The reason hatch is not canon as the project-management layer is friction: hatch wants to manage environments and scripts via `[tool.hatch.envs.*]`. Adopting that displaces the simple Makefile + venv discipline this document specifies. The cost (rewriting every project's developer workflow) exceeds the benefit (saving a Makefile).

`hatchling` as a *build backend* (replacement for `setuptools` in `[build-system]`) is a reasonable future direction; revisit when PyPA promotes it. Until then, `setuptools` is the default and works.

### pipenv — considered, not canon

Pipenv was the original "pip + virtualenv + lockfile" tool, PyPA-affiliated. Its `Pipfile` / `Pipfile.lock` format predates PEP 621 and has been superseded in practice. Maintenance has been intermittent. Not canon; not recommended for new projects.

### pip-tools — considered, not in canon

Jazzband-maintained (community OSS, neutral governance). `pip-compile` produces a portable `requirements.txt` lockfile from `pyproject.toml`. The canon does not require lockfiles (see §5), so pip-tools is not on the canon dev list. pip-tools 7.x also does not yet support `pip install --group` for PEP 735 dependency groups, the canon's dev-deps mechanism; if it adds `--group` support and a project wants a lockfile, install it project-side as needed.

## 3. Reference templates

Five canonical files live in [`../templates/classic/`](../templates/classic/). Which subset a project copies depends on its shape (see §"Scope"):

| Template | Copy to project as | Used by shapes |
|---|---|---|
| `library-pyproject.toml` | `pyproject.toml` (Shape src/djapp) or `pypkg/src/pyproject.toml` (Shape pypkg/pypkg+djapp) | all |
| `djapp-pyproject.toml` | `djapp/pyproject.toml` | `pypkg+djapp` only |
| `Makefile` | `Makefile` (repo root) | all |
| `pre-commit-config.yaml` | `.pre-commit-config.yaml` (add leading dot) | all |
| `gitignore` | `.gitignore` (add leading dot) | all |

**The rule:** copy verbatim, substitute the documented `<placeholder>` values, change nothing else. Any deviation from the templates is an audit finding unless justified in writing in the file's comment header.

### Placeholder substitution table

| Placeholder | What to substitute | Where it appears |
|---|---|---|
| `<project_name>` | The dist name on PyPI (kebab-case ok), e.g. `athena` | library pyproject `[project].name` |
| `<x.y.z>` | Semver string | library pyproject `[project].version` |
| `<one-line description>` | One-sentence summary | library pyproject `[project].description` |
| `<your name>` / `<email>` | Author identity | library pyproject `[project].authors` |
| `<runtime dep>` | One line per direct runtime import, version-pinned | library pyproject `[project].dependencies` |
| `<root>` | The top-level Python package, e.g. `athena` | library pyproject `[tool.importlinter]` |
| `<where>` | Setuptools package source path; `["src"]` for Shape src, `["."]` for Shape pypkg/pypkg+djapp | library pyproject `[tool.setuptools.packages.find].where` |
| Layered DAG rows | Project-specific peer/leaf arrangement | library pyproject `[[tool.importlinter.contracts]].layers` |
| djapp deps | Django runtime deps for the djapp | djapp pyproject `[dependency-groups].runtime` |

Everything else in the templates is uniform across racecar projects. Tool configuration (`[tool.black]`, `[tool.isort]`, `[tool.pylint]`, `[tool.pytest]`, `[tool.mypy]`), the `[dependency-groups].dev` list (§6), `[build-system]`, `requires-python`, `target-version` — none of these vary project-to-project.

### Pyproject rules (library pyproject)

- **`[project].dependencies` lists direct runtime imports only.** Transitive deps are pip's job at install time. This is the readable contract: "what does this project itself need to run."
- **Dev deps go in `[dependency-groups].dev` (PEP 735), not `[project.optional-dependencies].dev`.** The old location is rejected by the checker. See §6.
- **No `[tool.uv.*]`, `[tool.ruff.*]`, `[tool.poetry.*]`, `[tool.pdm.*]`, `[tool.hatch.envs.*]` blocks.** Standard PEP tables only; see §1 and §2.
- **`requires-python` matches `target-version` in black/mypy.** A drift here is an audit finding.
- **`[project].version` is the sole source of truth for the project's version.** No separate `VERSION` file (see §8).

### pylint canon

The `[tool.pylint]` configuration is **identical across racecar projects** — like the rest of the tool config it lives in the library pyproject, not in a standalone `.pylintrc` (a root `.pylintrc` is rejected by the checker; this keeps one home for tool config and preserves the explicit-`--rcfile`, no-auto-discovery discipline of §7). The canonical block is in [`../templates/classic/library-pyproject.toml`](../templates/classic/library-pyproject.toml); `scripts/check_packaging.py` enforces it. The shape:

- **Disable set is fixed.** A project may *append* its own disables, but every entry in the canonical `[tool.pylint."MESSAGES CONTROL"].disable` must be present: the pre-commit-plumbing noise codes, plus `duplicate-code` (R0801 fires on argparse / pydantic / dataclass boilerplate) and the two `use-implicit-booleaness` idioms.
- **Docstrings: class and function required, module not.** `missing-module-docstring` is disabled — a module's role lives in its subsystem `README` / `DESIGN` / `SYSTEM` / `CLAUDE` doc, not a one-line restatement of the filename. `missing-class-docstring` (C0115) and `missing-function-docstring` (C0116) must **not** be disabled: a class docstring states what the abstraction is, the highest-value orientation per token; functions follow. Names exempt from the requirement, via `[tool.pylint.BASIC]`: private (`^_`), pytest functions (`test_*`), `Test*` classes, and bodies under `docstring-min-length` lines.
- **Complexity caps are raised, not disabled.** `[tool.pylint.DESIGN]` bumps `max-args` / `max-locals` / `max-branches` etc. so cohesive data and CLI-builder code passes, while keeping the backstop. Disabling `too-many-*` outright is non-canon — raise the cap instead.
- **`min-similarity-lines = 12`** clears the false positives that the default of 4 raises on idiomatic per-verb CLI scaffolding.
- `load-plugins` stays the library set (`pylint_pytest`) for all shapes; Django projects do NOT add `pylint_django` here. It is loaded on the djapp only, by `racecar.mk`'s `lint` target, for the reasons in §6.

### Pyproject rules (djapp pyproject — Shape pypkg+djapp only)

- **`[dependency-groups].runtime` declares the Django runtime deps.** Required.
- **No `[project]` block.** djapp is not a publishable package; declaring `[project]` invents a fake `name`/`version` that the racecar audit will flag.
- **No `[build-system]`.** djapp is not pip-installable as a wheel; it runs via `python djapp/manage.py`.
- **No `[tool.*]` blocks.** Tool configurations live in the library pyproject and are passed to tools via `--config` / `--rcfile` / `--config-file` flags in the Makefile.

## 4. Virtual environment discipline

PEP 405 defines the `venv` module; how to use it on disk is convention. Racecar adopts the most common modern convention: a repo-local `.venv/` directory, created from system Python.

- Path: `.venv/` at repo root. Always. (Widely-used convention; not a PEP. `venv`, `env`, `.env` are also seen.)
- Creation: `python3 -m venv .venv`. Stdlib PEP 405.
- `.venv/` is in `.gitignore`.
- Targets in the Makefile run `.venv/bin/python` directly. **No target requires the venv to be "activated"** — `source .venv/bin/activate` is a developer convenience, not part of any automated workflow.
- The venv is recreatable from scratch via `make install`. Never edit anything inside `.venv/`.

The repo-local pattern means switching projects is a `cd`, not a `pyenv shell` or `conda activate`. It also means CI uses the same setup as developers do: create venv, install deps, run targets.

## 5. Dependencies (pyproject is the source of truth)

Single-source model:

- **`pyproject.toml`** — the *only* source of truth. Direct deps in `[project].dependencies`; dev/runtime dependency groups in `[dependency-groups]` (PEP 735). Edited by humans.
- **`requirements.txt`** — **optional**. A racecar project does not have to commit a lockfile. If a project chooses to commit one (as a snapshot, deployment artifact, CI input), the checker validates that it's a real pip-compile or pip-freeze output (rejects empty / placeholder files). The canon does not provide a generation mechanism, and the Makefile does not include a `lock` target — projects that want lockfiles roll their own (`pip freeze`, `pip-compile`, or external tooling).

### PEP 735 dependency groups

Dev dependencies and djapp runtime dependencies are declared in PEP 735 `[dependency-groups]`, not in `[project.optional-dependencies]`. The semantics are different:

- `[project.optional-dependencies]` are *extras* of the project — they travel with the wheel when published. `pip install my-pkg[dev]` works at install time.
- `[dependency-groups]` are *separate from the project* — they're not part of the wheel and exist purely for development/runtime grouping. `pip install --group dev` (pip 25.1+) installs them.

This separation is the right semantic for dev deps (they're not "optional features" of the project) and is required for the djapp pyproject (which has no `[project]` block to attach optional-dependencies to).

**Why this matters for racecar:** the djapp pyproject is `[dependency-groups]`-only — no `[project]`, no fake `name`/`version`. PEP 735 is what makes that file legal as a pyproject.

### Workflow

1. Add a direct dependency: edit `[project].dependencies` (runtime) or `[dependency-groups]` (dev / djapp runtime) in the relevant pyproject.
2. `make install` (runtime only) or `make install-dev` (runtime + dev group). pip resolves at install time from the pyproject pins.

### Minimum pip version: 25.1

Installing a `[dependency-groups]` group requires `pip install --group <name>`, available in pip 25.1+. `make install` upgrades pip to at least 25.1 as part of its bootstrap.

### Why no lockfile in canon

Lockfile reproducibility is a real benefit, but it solves a problem that doesn't apply at typical racecar-project scale (one developer, deployment by `git clone && make install`, no PyPI publish, no regulated environment). The cost (maintenance overhead, tooling complexity, noisy diffs, file rot) outweighs the benefit. Racecar treats `requirements.txt` as optional: validate-if-present, never required.

A project that grows into a multi-deploy / multi-dev / regulated context can opt in to lockfiles without changing canon — generate `requirements.txt` with whatever tool (pip freeze, pip-compile, etc.) and commit it. The checker will validate it's real and let it through.

### Optional extras

`[project.optional-dependencies]` is still appropriate for genuine user-installable extras (e.g. `cdsapi` for weather as an opt-in feature). The distinction: optional-dependencies for features users opt into when installing the wheel; dependency-groups for development/runtime grouping that's project-local.

## 6. The dev tool set

Every racecar Python project's library pyproject `[dependency-groups].dev` is the same list (PEP 735):

```toml
[dependency-groups]
dev = [
    "black",              # format
    "isort",              # import order
    "pylint",             # lint
    "pylint-pytest",      # pylint plugin: suppress test-fixture false positives
    "mypy",               # types
    "pytest",             # tests
    "pytest-cov",         # coverage measurement via coverage.py
    "pip-audit",          # dependency vulnerability scan (PyPA)
    "import-linter",      # DAG enforcement (see PYTHON.md §4)
    "pre-commit",         # git hooks
    "validate-pyproject", # PEP 621 schema validation (community OSS)
    "pyyaml",             # frontmatter parser for check_brief.py (llm-summary briefs)
]
```

**Status of each tool.** Eight of the twelve are mainstream de facto canon in modern Python: black, isort, pylint, mypy, pytest, pytest-cov, pip-audit, and pre-commit appear on the CI of most serious community projects. A reviewer at any modern Python shop will recognize them. The remaining four are racecar's specific commitments:

- `import-linter` — [`PYTHON.md`](PYTHON.md) §4 makes the import-graph DAG an enforced architectural property.
- `pylint-pytest` — racecar projects use pytest as the canonical test runner; the plugin suppresses W0621 (redefined-outer-name) false positives on fixture parameters, which would otherwise force every fixture-consuming test to carry a noisy disable.
- `validate-pyproject` — defends against PEP 621 structural typos (e.g. `[project].naem`) that the racecar audits assume away.
- `pyyaml` — the YAML frontmatter parser `check_brief.py` needs to validate an `llm-summary` brief. The brief lives in the adopter's own `docs/summary/<REPO>.md`, so the adopter must be able to validate it without the racecar checkout; that self-sufficiency is why `check_brief.py` is synced (it is the one synced check with a non-stdlib dependency, and `pyyaml` is its reason for being canon). The template `docs:` target runs `check_brief` guarded, so a repo with no brief pays only the inert dependency.

`pip-tools` is intentionally not on the list: the canon does not include a lockfile-generation workflow (see §5). Projects that want a lockfile install pip-tools themselves or use `pip freeze`.

**Django shapes add two canonical dev tools.** Shapes `pypkg+djapp` and `djapp` install a second PEP 735 group, `[dependency-groups].django`, for Django-only dev tools. Two entries are racecar-canonical; `check_packaging.py` requires both in the django group for any repo with a `manage.py`. The rest of that group (test, coverage, DRF helpers) is project-choice, not canon.

- **`djhtml`** — an idempotent, permissively-licensed community-OSS reindenter for Django/Jinja template tags. `black` owns the Python; templates carry no Python to format, so `djhtml` is the template-side counterpart. It runs in `make fmt` / `make fmt-check` gated on `$(DJAPP)` (a no-op in non-Django shapes) and as a `types: [html]` pre-commit hook. `djhtml`, not the heavier `djlint`, is the canon: djlint's reformatter is a louder linter-first tool under a GPL license whose idempotence is empirical rather than structural; `djhtml` only reindents, so its idempotence is by construction.
- **`pylint-django`** — the community-OSS pylint plugin that teaches pylint the Django ORM (so `Model.objects`, the `Meta` inner class, and the model metaclass stop raising false positives). It is loaded **on the djapp only**: `racecar.mk`'s `lint` target lints `$(SRC)` with the plain library config and lints `$(DJAPP)` with `--load-plugins=pylint_django`. The library is not Django and may not even import it, so the plugin is not loaded over the library tree, and adopters do not hand-edit `[tool.pylint.MAIN].load-plugins` (re-syncing `racecar.mk` is the whole change). Without it the django app lints against the library config and false-positives on every ORM idiom, which kept `make check` red.

**Racecar's specific commitments.** Pinning the exact list (rather than letting projects choose between e.g. pylint and flake8) is racecar's call. It produces consistency across projects at the cost of some flexibility. Adding a tool to this list is a standards-change conversation, not a project-by-project decision.

**Specifically not on the list:**

- `flake8`, `pyflakes`, `pycodestyle` — pylint covers the same ground; running two linters is duplicated effort. (racecar choice; both pylint and flake8 are legitimate.)
- `ruff` — VC-backed (Astral); see §1 and §2.
- `coverage.py` directly — `pytest-cov` (above) wraps it; no need to depend on it separately.
- `tox` / `nox` — `make check-full` does what they do for our cases; no matrix testing needed. (racecar choice; tox/nox are widely used elsewhere.)
- `bandit` — code-level security linting is project-specific; pip-audit covers the dependency-CVE axis.
- `pip-tools` — see §5; no lockfile workflow in canon.

### Shape-specific sidecar groups

`[dependency-groups].dev` is the universal canon. Shape-specific tools that don't belong in the universal list go in a named sidecar group installed alongside `dev`. The checker only validates `dev`; sidecar groups are invisible to it.

**`djapp` shape — `django` group.** Django projects add a `django` dependency group for tools that are either Django-specific or required because Django's test runner replaces pytest:

```toml
[dependency-groups]
django = [
    "coverage>=7.4",              # Django test runner needs coverage directly (pytest-cov is pytest-only)
    "django-debug-toolbar>=4.0",  # local dev; wired in INSTALLED_APPS
    "drf-spectacular[sidecar]>=0.27",  # OpenAPI schema + Swagger UI (DRF projects)
    "pylint-django>=2.5",         # suppresses false-positive E1101 on Django model fields
]
```

The `install-dev` Makefile target auto-detects Django and installs the `django` group if any dependency string starting with `"django` is found in the library pyproject:

```makefile
install-dev: install
	$(PIP) install --group $(LIB_PYPROJECT):dev
	$(BIN)/pre-commit install
	@if grep -qi '"django' $(LIB_PYPROJECT); then $(PIP) install --group $(LIB_PYPROJECT):django; fi
```

Projects that do not use DRF may omit `drf-spectacular`. Projects not using debug-toolbar may omit it. `coverage` and `pylint-django` are expected on all djapp-shape projects.

## 7. Makefile contract

This is the most racecar-specific section in the file. PEPs do not define a `Makefile` shape for Python projects, and many projects use `tox` / `nox` / shell scripts instead of Make. Racecar requires Make and prescribes a target surface so every project's developer experience (`make check`, `make install`, etc.) is identical. The targets *inside* the file (calling `black`, `pytest`, `mypy`, etc.) are mainstream tool invocations; the *contract* — exactly which targets exist, what they chain, what `make check` includes — is racecar's.

### The fold: owned `Makefile` + identical `racecar.mk`

The build is split into two files so that the canonical half is never hand-maintained:

- **`Makefile`** (owned; the front door). A thin root you own and edit freely: project-specific targets and variable overrides, plus `include racecar.mk`. racecar never rewrites it. In the simplest case it is one line: `include racecar.mk`. Skeleton: [`../templates/classic/Makefile`](../templates/classic/Makefile).
- **`racecar.mk`** (canonical; vendored). Every standard target plus the shape logic. It is **identical in every racecar project** — there is no per-repo content. It detects the shape from the layout at make-time (the §"Scope" decision, written in Make) and sets `SRC` / `PKG` / `DJAPP` / `LIB_PYPROJECT` / `DJAPP_PYPROJECT` with `?=`, falling back to stock for an unrecognized layout. `make sync` copies it verbatim from [`../templates/classic/racecar.mk`](../templates/classic/racecar.mk); any hand-edit is lost on the next sync. It is committed, so `make` runs offline with nothing from racecar present.

Why the split: a single hand-filled template drifts. When the canonical machinery and the project's own customization share one file, trimming or editing the former to suit a project (the common, reasonable urge) silently diverges it from base. The fold removes the surface entirely — `racecar.mk` is the same bytes everywhere (so there is nothing per-repo to drift), and the project half is a separate owned file (so overwriting `racecar.mk` never clobbers it). Because the shape is computed live from what is on disk, there is no stored shape value, no stamp, and no "regenerate for the new shape" step: restructure the repo (e.g. add `pypkg/src/`) and the next `make` simply reads the new layout. `check_packaging` reads both files for the target contract.

A repo that predates the fold (a single full Makefile, no `racecar.mk`) still passes; `check_packaging` nudges it to `make sync` (`no-racecar-mk`). Migration is a **manual upgrade step**, not something `sync` automates: `sync` only drops the canonical `racecar.mk` and never touches the existing `Makefile`. So adoption is finished by hand — extract project-specific targets into the owned `Makefile`, add `include racecar.mk`, and remove the canonical recipes the include now supplies (never clobbering a customized recipe). Until that hand-step runs, the repo is in the half-migrated state where `racecar.mk` sits inert beside a monolith that does not include it; `check_packaging` flags that state `racecar-mk-not-included` (a Blocker, because the canonical build is dead weight), distinct from the pre-fold nudge. See [`../upgrade/README.md`](../upgrade/README.md) step 4.

### Target surface

Every project's `make help` lists the same targets:

| Target | Purpose |
|---|---|
| `help` | Self-documenting help generated from `## …` annotations |
| `venv` | Create `.venv/` if missing |
| `install` | venv + editable library install (resolves deps from pyproject) |
| `install-dev` | `install` + PEP 735 dev group (requires pip ≥ 25.1) |
| `check` | **Fast gate** (pre-commit cadence, ~30s): `fmt-check lint test` |
| `check-full` | **Full gate** (pre-push / CI cadence, parallel): adds `typecheck arch docs` |
| `audit` | `pip-audit` for dependency vulnerability scanning (standalone; run weekly / on-demand) |
| `fix` | Auto-fix what can be auto-fixed (currently `fmt`) |
| `fmt` | Apply `isort` then `black` to `$(SRC)` (and `$(DJAPP)` if set) |
| `fmt-check` | Same as `fmt` but `--check-only` (no writes) |
| `lint` | `pylint --rcfile $(LIB_PYPROJECT)` plus the no-upward-imports pre-commit hook |
| `test` | `pytest -c $(LIB_PYPROJECT)`, scoped via `PYTEST_ARGS`; exit 5 (no tests collected) treated as success |
| `coverage` | `pytest --cov=$(PKG) --cov-branch --cov-report=term-missing --cov-report=html`; HTML at `htmlcov/index.html` |
| `typecheck` | `mypy --config-file $(LIB_PYPROJECT) $(SRC)` |
| `arch` | `lint-imports --config $(LIB_PYPROJECT)`, `check_upward_imports`, `check_cli_commands`, `check_packaging`, `check_face_orchestration` (advisory; no-ops without faces verticals; see [`FACES.md`](FACES.md) §7) (+ `check_dj_model_ref_as_string` if Django) |
| `docs` | `check_docs.py` mechanical pre-pass |
| `system-deps` | Install system-level dependencies not available via pip (idempotent; called by `install`) |
| `clean` | Remove caches and build artifacts — *never* data or `.venv` |
| `distclean` | `clean` plus removing `.venv` |

### Variables

`racecar.mk` sets these variables. The shape-dependent five (`SRC`, `PKG`, `DJAPP`, `LIB_PYPROJECT`, `DJAPP_PYPROJECT`) are chosen by the make-time shape decision (§"Scope") and assigned with `?=`, so the owned `Makefile` can override any with an earlier `:=`. The rest are fixed:

| Variable | Default | Purpose |
|---|---|---|
| `VENV` | auto-detected: `.venv` / `venv` / `../venv` | Repo-local venv path |
| `PYTHON` | `$(VENV)/bin/python` or `python3` | Python interpreter |
| `PIP` | `$(PYTHON) -m pip` | Installer |
| `BIN` | `$(VENV)/bin` or `~/.local/bin` | Where to find tool entry-points (`lint-imports`, `pre-commit`) |
| `SRC` | `src` | Source root to format/lint/type-check |
| `PKG` | auto-derived: the package dir under `SRC` (`src/<pkg>`, `pypkg/src/<pkg>`), or `SRC` itself when `SRC` is `.` or is itself a package | Importable package dir the CLI/coverage/arch audits require (not the namespace source root) |
| `DJAPP` | empty | Django app directory; triggers `check_dj_model_ref_as_string.py` when set |
| `LIB_PYPROJECT` | `pyproject.toml` | Library pyproject path (location varies by shape — see §"Scope") |
| `DJAPP_PYPROJECT` | empty | djapp pyproject path (only Shape pypkg+djapp) |
| `PYTEST_ARGS` | empty | Pass-through pytest args, e.g. `make test PYTEST_ARGS="-k foo -q"` |

### Tool config discovery

Tools (`black`, `isort`, `pylint`, `mypy`, `pytest`, `lint-imports`) are invoked with an explicit `--config` / `--rcfile` / `--config-file` / `-c` flag pointing at `$(LIB_PYPROJECT)`. They do **not** rely on auto-discovery by walking up from cwd. This is racecar's call: it works uniformly across all shapes (whether the library pyproject is at repo root or at `pypkg/src/pyproject.toml`), and it stays correct when the Makefile is invoked from `cd` other than the directory containing the pyproject.

### Multi-root first-party detection (Shape `pypkg+djapp`)

For Shape `pypkg+djapp`, `fmt` runs `isort` over **two** source roots — `$(SRC)` (`pypkg/src`) *and* `$(DJAPP)` (`djapp`) — from a single config that lives in only one of them (`pypkg/src/pyproject.toml`). isort classifies each import as first-party or third-party. Over a *single* tree it auto-detects first-party packages by inspecting what is importable from that tree, so `profile = "black"` alone suffices for the single-root shapes (`src`, `pypkg`, `djapp`). Over the *second* tree it cannot: there is no settings file rooted at `djapp/`, so isort misclassifies djapp's first-party packages (`apps`, `core`, `project`, …) as third-party and reorders dozens of files — while a profile-only check reports green. The same blind spot hits `import-linter`: a bare `root_package = "<lib>"` audits only the library import graph and never looks at the djapp graph at all.

Therefore, for Shape `pypkg+djapp` specifically, the library pyproject must close the multi-root gap explicitly (these are **not** required for single-root shapes, where auto-detection covers them):

- **`[tool.isort].src_paths` must include `"djapp"`** — so isort scans the djapp tree as a source root, not as third-party site-packages.
- **`[tool.isort].known_first_party` must list every djapp top-level package** — so those imports are classified first-party instead of third-party. The checker derives the expected set from the importable top-level directories under `djapp/`.
- **`[tool.importlinter]` must cover the djapp roots** — name them in `root_packages` (plural) or reference them from a contract's modules — so `lint-imports` actually audits the djapp import graph, not just the library's.

These are racecar's call, the natural consequence of the two-root `fmt`/`arch` invocation; for single-root shapes isort and import-linter auto-detect over their one tree and the assertions do not apply.

### Discipline rules

- **Tools invoked via `$(PYTHON) -m <tool>` or `$(BIN)/<tool>`** — never bare names. This is why no target needs an *activated* venv; it also sidesteps the GNU Make 3.81 (macOS) PATH-export bug.
- **`clean` is safe to run any time.** It removes caches (`__pycache__`, `.mypy_cache`, `.pytest_cache`, `.import_linter_cache`) and build artifacts (`build/`, `dist/`, `*.egg-info/`, coverage outputs). It never removes data directories, the venv, or anything a developer would not want to lose.
- **`distclean` extends `clean` by removing `.venv/`.** Use when reproducing from scratch or after a Python upgrade.
- **`system-deps` installs OS-level dependencies that pip cannot provide** (e.g. `poppler` for `pdftotext`, `wkhtmltopdf`, `ffmpeg`). `install` depends on it, so a cold `make install` always runs it. The implementation lives in `scripts/install_system_deps.sh` (copy from `templates/classic/install_system_deps.sh`). The script must be idempotent — it checks for each command's presence before installing. Projects with no system deps keep the stub with no calls.
- **Customize in the owned `Makefile`, never in `racecar.mk`.** Add project-specific targets below the `include`; override a canonical recipe by redefining it there (GNU Make: last definition wins); override a shape variable by setting it with `:=` above the include. Edits to `racecar.mk` are erased on the next `make sync`.

## 8. Versioning and `CHANGELOG.md`

### Version source: library pyproject

The library pyproject's `[project].version` is the **sole** source of truth for the project's version:

- Shape `src` / `djapp` — `pyproject.toml [project].version` at repo root.
- Shape `pypkg` / `pypkg+djapp` — `pypkg/src/pyproject.toml [project].version`.

For Shape `pypkg+djapp`: the djapp pyproject has no `[project]` block and therefore no version. djapp is a deployment, not a release — its release tracking (git SHA, deploy timestamp, image tag) lives outside racecar canon.

**No separate `VERSION` file.** A `VERSION` file at repo root duplicating the pyproject version is a drift class for marginal benefit (shell-readability without parsing TOML); pyproject is the single source. Shell scripts that need the version read it via:

```bash
python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
```

The checker emits a Finding when a legacy `VERSION` file is detected **only when the library pyproject declares `[project].version`** — i.e. when a canonical version exists for `VERSION` to be redundant with. A repo that declares no `[project]` table is not a deployable/publishable package (a docs, scripts, or standards-framework repo); it has no pyproject version to supersede a `VERSION` file, so `VERSION` is its legitimate version home and is not flagged. This rule deprecates `VERSION` only where a real `[project].version` exists to replace it.

### `CHANGELOG.md`

Follows the [Keep a Changelog](https://keepachangelog.com/) format (an external community standard, not a PEP): most recent version on top, sections per release: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` (subset as relevant). Each entry is a bullet starting with a module/area tag in bold: `- **prices**: …`.

```markdown
# Changelog

## [Unreleased]

## 0.2.0 - 2026-05-28

### Added
- **module**: short description of what changed and why it matters.

### Changed
- **module**: signature change or behavior change, with the old → new shape.

### Removed
- **module**: what went away and what supersedes it.

## 0.1.1 - 2026-03-27

### Added
- ...
```

Rules:

- Date format `YYYY-MM-DD`.
- `## [Unreleased]` is canonical and accepted by the checker: it is the honest header for a repo that has not yet cut its first release (a freshly-scaffolded `CHANGELOG.md` is exactly `# Changelog` + `## [Unreleased]`, zero fabrication), and the accumulation point for changes between releases. When a version ships, rename it to `## X.Y.Z - YYYY-MM-DD` and open a fresh `## [Unreleased]` above.
- Bullets explain *why*, not just *what*. The diff already explains *what*.
- A `0.x.0` minor bump signals structural change or breaking API; a `0.x.y` patch bump signals fixes only. Above `1.0.0`, semver rules apply strictly.

## 9. Enforcement

The Makefile is the contract. **`make check`** is the local fast gate (~30s, pre-commit cadence); **`make check-full`** is the CI gate (parallel, pre-push / push-to-remote). CI runs `make check-full` and nothing else. If a check is missing, add it to the appropriate target; do not add an out-of-band CI step.

### Mechanical check: `scripts/check_packaging.py`

The audits below are mechanized by `arch-coherence/scripts/check_packaging.py`, which is invoked by `make arch` (chained into `make check-full`). The script is pure-stdlib (no pydantic, no PyYAML; `tomllib` plus narrow regexes for line-oriented YAML/Make/.gitignore), and reports two severities:

- **Blocker** — non-zero exit, blocks the gate. Default exit behavior.
- **Finding** — recommendation; passes by default. `python check_packaging.py --strict` flips Findings to Blockers for hardened CI gates.

The script lives in racecar (`arch-coherence/scripts/check_packaging.py`) and is copied or symlinked into each project's `scripts/` directory alongside `check_upward_imports.py` and `check_cli_commands.py`. Tests for the checker live at `arch-coherence/tests/test_check_packaging.py`.

### Audits

**pyproject.toml structural:**
- **`requires-python` differs from `target-version` in black or `python_version` in mypy** — Blocker.
- **PEP 621 required keys missing from `[project]`** — Blocker.
- **`[project].version` not a semver string** — Blocker.
- **`[dependency-groups].dev` missing or diverges from the canon §6 list** — Blocker for missing tools; Finding for unexpected extras.
- **Dev deps in the deprecated `[project.optional-dependencies].dev` location instead of PEP 735 `[dependency-groups].dev`** — Blocker.

**Non-canon tool config:**
- **Presence of `[tool.uv.*]`, `[tool.ruff.*]`, `[tool.poetry.*]`, `[tool.pdm.*]`, `[tool.hatch.envs.*]`, or any non-canon tool config block** — Blocker per §1 and §2.
- **Invocation of `uv`, `ruff`, `poetry`, `pdm`, or `pipenv` from the Makefile** — Blocker per §1 and §2.
- **Presence of `uv.lock`, `poetry.lock`, `pdm.lock`, or `Pipfile.lock`** — Blocker. These indicate use of a non-canon tool.

**Lockfile (committed requirements.txt is optional but must be real if present):**
- **`requirements.txt` exists but is empty or comments-only** — Blocker. Either populate or remove.

**Versioning:**
- **Legacy `VERSION` file at repo root** — Finding (pyproject is the sole source now; delete the file).

**Makefile:**
- **Missing canonical target from §7** — Blocker. Includes `check`, `check-full`, `coverage`, `audit`, `docs`.
- **`racecar.mk` present but the `Makefile` does not `include` it** (`racecar-mk-not-included`) — Blocker. The canonical build is inert and a monolithic `Makefile` still drives the build; this is the half-migrated state an upgrade leaves. Finish the fold (add the `include`, drop the canonical recipes). Distinct from the pre-fold nudge (`no-racecar-mk`, a Finding) and from an `include` whose target is absent (`racecar.mk` `missing-file`, a Blocker).
- **Fast `check` chain missing `fmt-check`, `lint`, or `test`** — Finding.
- **`clean` removes data, `.venv`, or anything outside the §7 contract** — Blocker.

**Pre-commit:**
- **Required hooks missing**: `black`, `isort`, `import-linter`, `validate-pyproject`, `no-upward-imports-in-business-modules`, `doc-coherence-mechanical-pre-pass` — Blocker.

**.gitignore:**
- **`.venv/` not gitignored** — Blocker.
- **`__pycache__/` not gitignored** — Finding.

**CHANGELOG:**
- **`CHANGELOG.md` missing or `## <version> - <date>` heading malformed** — Finding.

**Shape pypkg+djapp specific:**
- **Library `[tool.isort]` omits `src_paths` covering `djapp`, or omits a `known_first_party` listing the djapp first-party roots** — Blocker. `profile = "black"` alone is a false green for multi-root isort (see §7 "Multi-root first-party detection").
- **`[tool.importlinter]` names only the library and never covers the djapp roots** — Blocker. `lint-imports` would audit only the library import graph.
- **`djapp/pyproject.toml` declares `[project]`, `[build-system]`, or any `[tool.*]` block** — Finding. djapp pyproject is intended to be PEP 735 `[dependency-groups]`-only.

## What this file does not cover

- **What goes inside `src/`**: see [`PYTHON.md`](PYTHON.md).
- **The CLI surface declared by `__main__.py`**: see [`CLI.md`](CLI.md).
- **Naming, formatting at the line level, test conventions, Definition of Done**: see [`../eng-review/PYTHON.md`](../eng-review/PYTHON.md).
- **CI configuration** (GitHub Actions, GitLab CI, etc.): out of scope here; the contract is "CI runs `make check-full`."
- **Containerization** (Dockerfile, devcontainer): out of scope; if a project containerizes, the container's entrypoint should still be `make <target>`.
- **Documentation generation** (Sphinx, MkDocs): out of scope.
