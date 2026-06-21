# Python — Architectural Coherence

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

The Python-specific expression of architectural coherence. For the language-agnostic axioms this section derives from, see [`README.md`](README.md). For Python engineering hygiene — naming, formatting, testing, linting workflow, Definition of Done — see [`../eng-review/PYTHON.md`](../eng-review/PYTHON.md). For Django-specific coherence, see [`DJANGO.md`](DJANGO.md).

Sections are ordered as a DAG — most independent first, most dependent last.

## 1. Module Structure

How code is organized into files and packages. Every package has two specialty files — `__init__.py` and `__main__.py` — with opposite roles on the dependency graph. This section owns the Python-specific shape of the direction axiom in [check 2 Direction](README.md#2-direction).

**`__init__.py` — the package's face to the outside.** It declares what the package IS when imported. It is for orchestration and re-exports only; business logic lives in named modules. If `__init__.py` has more than a few re-export lines, move the logic to a named module and re-export. `__init__.py` may import upward — only to the environment layer (see [the environment-layer exception](README.md#environment-layer-exception)). When a child package needs inherited state, its `__init__.py` imports from the environment layer and re-exports into its own namespace.

**`__main__.py` — the execution entry point.** It imports outward, reaching down into the package's own subtree to dispatch work. Its dependencies go inward-subtree only; never upward to a parent package (env-layer carve-out excepted). For the full `__main__.py` + `commands()` / `subcommands()` / `parser()` pattern that makes this structural, see [CLI.md](CLI.md).

**Other `.py` modules never import upward directly.** Business-logic modules stay within their own subtree, import from peers in the allowed direction (see [check 2 Direction](README.md#2-direction)), or read inherited state through their own package's `__init__.py` — not from the root directly. This is the rule `check_upward_imports.py` enforces; see §4.

**When a library is exposed through more than one face**, these module roles map onto the `lib → api → {cli, mcp, web/django}` tiers: the worker is `lib`, the orchestration policy is `api`, and each face is a wrapper on `api` (the cli face being `__main__`). Where orchestration lives, the per-vertical co-location, the canonical file names (an autodiscovery contract: `lib.py` / `api.py` / `mcp.py` / `__main__.py`), and the single gated `layers` contract plus the advisory detector are in [FACES.md](FACES.md) (one home; not restated here).

## 2. Imports

How modules connect to each other. Depends on module structure being sound.

**Direction.** Imports flow outward or downward only. This is an architectural rule — see [check 2 Direction](README.md#2-direction) for the axiom and rationale. This section covers the file-level enforcement.

**Top-level only.** All imports live at the top of the file. No exceptions. Lazy imports — imports inside functions, methods, or conditional blocks — are never acceptable. They are a band-aid over a structural problem. If moving an import to the top of the file breaks something, that breakage is the real bug. Diagnose it: extract shared code into a third module, restructure the dependency graph, or flag it for discussion. Do not bury it inside a function and move on.

**Circular dependencies.** A lazy import is usually a symptom of a circular dependency that was papered over instead of resolved. The fix is structural. See [check 1 Acyclicity](README.md#1-acyclicity-root-axiom).

## 3. CLI

The CLI surface (`__main__.py` patterns, `commands()` / `subcommands()` / `parser()` contracts, audit JSON schema, mutex group encoding) is its own document — see [CLI.md](CLI.md). The Python-language piece of the rule lives here:

**No inward references in `__main__.py`.** Entry points are the top layer of the dependency graph; they import downward into their own subtree only. No `from ..` — that would couple children to parents and mask circular dependencies (see [check 1 Acyclicity](README.md#1-acyclicity-root-axiom) and [check 2 Direction](README.md#2-direction)).

## 4. Enforcement

Enforcement here is local confirmation the owner can rely on, not a CI gate that replaces owner judgment — see [OWNERSHIP.md](../shared/OWNERSHIP.md).

Five tools enforce the coherence rules:

- `import-linter` checks acyclicity and direction ([`README.md`](README.md) checks 1–2).
- `scripts/check_upward_imports.py` enforces §1 (no upward imports from business modules to the root package), file-by-file.
- `scripts/check_cli_commands.py` enforces the [CLI contract](CLI.md) — `commands()` / `subcommands()` / `parser()` plus the three patterns plus the audit JSON schema — by walking the CLI tree, confirming every `python -m <pkg>` lists its registered children, introspecting argparse parsers when `parser()` is exposed, and surfacing orphan `__main__.py` files that no parent registers.
- `scripts/check_dj_model_ref_as_string.py` enforces [DJANGO.md §2](DJANGO.md#2-orm-relations) (no cross-module string ORM relations); skipped automatically when the consumer repo has no `manage.py`.
- `scripts/check_face_orchestration.py` is the advisory detector for [FACES.md §7](FACES.md#7-the-advisory-detector): it identifies each vertical's `lib` / `api` / faces (by canonical name, `[tool.racecar.faces]` manifest, or structural inference) and flags non-classifiable verticals plus orchestration restated across faces. Findings (recommendations), exit 0 by default; `--strict` exits 1. Discovers verticals structurally; no-ops when none are found. Runs via `make arch`, not pre-commit.
- `scripts/check_docs.py` enforces the [doc-coherence](../doc-coherence/README.md) mechanical pre-pass.

`check_upward_imports.py`, `check_docs.py`, and `check_dj_model_ref_as_string.py` are wired into `pre-commit` and run on every commit via `.pre-commit-config.yaml`. `check_cli_commands.py` is a full-tree audit — it shells out `python -m <pkg>` for every node, which is too expensive for a per-commit hook — so it runs via `make arch PKG=<path>`, in CI, or on-demand. The per-project contract (layers, forbidden edges) lives in `pyproject.toml` under `[tool.importlinter]`.

For linter configuration and workflow (formatter-as-canonical, no inline suppressions, full-codebase scope), see [`../eng-review/PYTHON.md` §5 Linting & Verification](../eng-review/PYTHON.md#5-linting-verification).

Templates live in [`../templates/classic/`](../templates/classic/) — a single canonical set (black + isort + pylint; no ruff). The project shapes, the full file inventory (`library-pyproject.toml`, `djapp-pyproject.toml`, `Makefile`, `pre-commit-config.yaml`, `gitignore`), and the copy-and-substitute procedure live in [`PACKAGING.md`](PACKAGING.md). The arch-coherence-specific steps on top of that procedure are:

1. Copy the check scripts into your project's `scripts/` directory:
   - `arch-coherence/scripts/check_upward_imports.py`
   - `arch-coherence/scripts/check_cli_commands.py`
   - `arch-coherence/scripts/check_packaging.py` (also imported by `check_upward_imports.py` and `check_face_orchestration.py` for shape detection)
   - `arch-coherence/scripts/check_face_orchestration.py` (faces projects; no-ops without `[tool.racecar.faces]`)
   - `arch-coherence/scripts/check_dj_model_ref_as_string.py` (Django projects; skipped at runtime otherwise)
   - `doc-coherence/scripts/check_docs.py`
2. In the library pyproject's `[tool.importlinter]`, replace `<root>` with your top-level package name and fill the layer rows with your own packages.
3. `pre-commit install` to enable the hooks.

### Bumping pinned versions

Run `pre-commit autoupdate` when you want newer tool releases; review the resulting diff like any other change and commit the bumps your judgment accepts. The framework does not prescribe a cadence — that is an owner decision.

### Update triggers — when to modify pyproject.toml

Any architectural change in the source tree requires a matching edit to `[tool.importlinter]` in the same commit:

1. New top-level package → add it to the layer matching its role (consumer / data / leaf).
2. Top-level package removed → remove its entry.
3. New peer direction (A now imports B where they were independent) → split A and B into separate layer rows (B below A), or add a `forbidden` contract:

   [[tool.importlinter.contracts]]
   name = "B does not import A"
   type = "forbidden"
   source_modules = ["<root>.<B>"]
   forbidden_modules = ["<root>.<A>"]

4. Peer direction reversed or removed → update the layers contract.
5. Package changes role (leaf → consumer, etc.) → move to the appropriate layer row.

### Instruction to Claude or any agent

When making any architectural change under the source tree — adding a package, moving a module between packages, establishing a new peer import — update `[tool.importlinter]` in `pyproject.toml` in the same commit. The contract is source-of-truth for the dependency graph. If contract and code disagree, `lint-imports` fails and pre-commit rejects the commit.

### Verification

After editing the contract, run `lint-imports`. Output should be `Contracts: N kept, 0 broken.` If broken: either the code doesn't match the claimed architecture (fix the code) or the contract is stale (fix the contract).

### Template updates

`../templates/classic/` is the canonical source. When the templates evolve (new pinned versions, new custom checks), consumer projects pull changes in by manually re-copying. `diff -u ../templates/classic/pre-commit-config.yaml .pre-commit-config.yaml` shows drift; merge intentionally.
