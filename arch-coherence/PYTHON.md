# Python — Architectural Coherence

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

The Python-specific expression of architectural coherence. For the language-agnostic axioms this section derives from, see [`README.md`](README.md). For Python engineering hygiene — naming, formatting, testing, linting workflow, Definition of Done — see [`../eng-review/PYTHON.md`](../eng-review/PYTHON.md). For Django-specific coherence, see [`DJANGO.md`](DJANGO.md).

Sections are ordered as a DAG — most independent first, most dependent last.

## 1. Module Structure

How code is organized into files and packages. Every package has two specialty files — `__init__.py` and `__main__.py` — with opposite roles on the dependency graph. This section owns the Python-specific shape of the direction axiom in [check 2 Direction](README.md#2-direction).

**`__init__.py` — the package's face to the outside.** It declares what the package IS when imported. It is for orchestration and re-exports only; business logic lives in named modules. If `__init__.py` has more than a few re-export lines, move the logic to a named module and re-export. `__init__.py` may import upward — only to the environment layer (see [the environment-layer exception](README.md#environment-layer-exception)). When a child package needs inherited state, its `__init__.py` imports from the environment layer and re-exports into its own namespace.

**`__main__.py` — the execution entry point.** It imports outward, reaching down into the package's own subtree to dispatch work. Its dependencies go inward-subtree only; never upward to a parent package (env-layer carve-out excepted). For the full `__main__.py` + `commands()` pattern that makes this structural, see §3.

**Other `.py` modules never import upward directly.** Business-logic modules stay within their own subtree, import from peers in the allowed direction (see [check 2 Direction](README.md#2-direction)), or read inherited state through their own package's `__init__.py` — not from the root directly. This is the rule `check_upward_imports.py` enforces; see §4.

## 2. Imports

How modules connect to each other. Depends on module structure being sound.

**Direction.** Imports flow outward or downward only. This is an architectural rule — see [check 2 Direction](README.md#2-direction) for the axiom and rationale. This section covers the file-level enforcement.

**Top-level only.** All imports live at the top of the file. No exceptions. Lazy imports — imports inside functions, methods, or conditional blocks — are never acceptable. They are a band-aid over a structural problem. If moving an import to the top of the file breaks something, that breakage is the real bug. Diagnose it: extract shared code into a third module, restructure the dependency graph, or flag it for discussion. Do not bury it inside a function and move on.

**Circular dependencies.** A lazy import is usually a symptom of a circular dependency that was papered over instead of resolved. The fix is structural. See [check 1 Acyclicity](README.md#1-acyclicity-root-axiom).

## 3. CLI

Builds on §1 Module Structure (package layout) and §2 Imports (outward-downward direction). The CLI pattern is the top layer of the dependency graph — entry points import downward, never from peers or ancestors.

Recursive outward-only discovery. Every package that contains runnable commands must provide a `__main__.py` that (a) exposes a `commands()` function and (b) prints that list when invoked with no arguments.

### Core Principles

**Packages are the preferred CLI entries; runnable modules are also valid.** A package CLI entry is a directory with a `__main__.py`. A `.py` module with an `if __name__ == "__main__":` block is also a valid entry (`python -m fubar.foo.alpha.data`). Prefer a package once the CLI grows past one file or needs its own sub-commands; keep a module for simple single-file tools.

**Unidirectional relationship.** The dependency graph is parent → child only. Parents know about their children (by registering their names). Children never reference parents. This is the CLI-layer expression of the direction axiom in [check 2 Direction](README.md#2-direction).

**Knowledge isolation.** Each `__main__.py` only declares what it directly contains — names of its immediate sub-packages (depth + 1). It does not enumerate grandchildren.

**The command contract.** Every `__main__.py` exports `commands() -> list[tuple[str, str]]` — a list of `(sub_package_name, description)` pairs. Leaves return `[]`. Names are relative; the print layer constructs full paths using `__package__`.

**Side-effect isolation.** `commands()` is a pure data function. No I/O, no network, no heavy processing. Printing the listing is confined to the `_print_commands()` helper (Patterns 1 and 2). Leaf CLIs (Pattern 3) delegate all output to `argparse`. No other CLI functions should call `print()` directly.

### Implementation Blueprint

Sample tree used throughout. Directories with `__main__.py` are CLI entry points. A `.py` module with an `if __name__ == "__main__":` guard is also a valid entry point. The `.py` files shown in this tree are utility modules — no main guard, imported by the neighboring `__main__.py`.

```
src/fubar/
  __init__.py
  __main__.py          ← CLI entry: python -m fubar   (root aggregator)
  foo/
    __init__.py
    __main__.py        ← CLI entry: python -m fubar.foo   (intermediate with own CLI)
    alpha/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.foo.alpha   (leaf CLI)
      data.py          ← utility module (imported by alpha's __main__; NOT a CLI entry)
  baz/
    __init__.py
    __main__.py        ← CLI entry: python -m fubar.baz   (intermediate, discovery only)
    alpha/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.baz.alpha
      data.py          ← utility module
    bravo/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.baz.bravo
      calculator.py    ← utility module
```

There are three patterns. Each `__main__.py` matches exactly one.

---

#### Pattern 1 — Pure discovery (root or intermediate without own CLI)

Lists sub-packages. No CLI of its own. Always prints the listing and exits.

Used by `fubar/__main__.py` (root) and `fubar/baz/__main__.py` (intermediate with no own CLI).

```python
"""CLI entry: python -m fubar"""

import sys


def commands() -> list[tuple[str, str]]:
    return [
        ("foo", "Foo sub-package: [one-line description]"),
        ("baz", "Baz sub-package: [one-line description]"),
    ]


def _print_commands() -> None:
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\nAppend --help to any command for its options.")


if __name__ == "__main__":
    _print_commands()
    sys.exit(0)
```

---

#### Pattern 2 — Discovery plus own CLI (intermediate that both aggregates and runs)

Lists sub-packages. Has its own argparse CLI. No-args prints the listing; args runs the CLI.

Used by `fubar/foo/__main__.py`.

```python
"""CLI entry: python -m fubar.foo"""

import argparse
import sys


def commands() -> list[tuple[str, str]]:
    return [
        ("alpha", "Alpha sub-package: [one-line description]"),
    ]


def _print_commands() -> None:
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\nAppend --help to any command for its options.")


def main() -> None:
    if not sys.argv[1:]:
        _print_commands()
        return
    parser = argparse.ArgumentParser(description="foo CLI")
    # argument definitions
    args = parser.parse_args()
    run(args)


def run(args: argparse.Namespace) -> None:
    raise NotImplementedError("replace with project-specific dispatch")


if __name__ == "__main__":
    main()
```

Note: `_print_commands()` must exist in every Pattern 1 and Pattern 2 `__main__.py`. The outward-downward rule ([check 2 Direction](README.md#2-direction)) forbids inheriting it from above; there is no guaranteed leaf below to reuse it from. The function is therefore explicit at every node — a direct expression of the architecture, not a duplication to be reconciled.

---

#### Pattern 3 — Leaf CLI (package with no sub-packages)

No sub-packages to discover. `commands()` returns `[]`. The `__main__.py` IS the CLI — argparse handles everything including `--help`.

Used by `fubar/foo/alpha/__main__.py`, `fubar/baz/alpha/__main__.py`, `fubar/baz/bravo/__main__.py`.

```python
"""CLI entry: python -m fubar.foo.alpha"""

import argparse


def commands() -> list[tuple[str, str]]:
    return []  # leaf — no sub-packages


def main() -> None:
    parser = argparse.ArgumentParser(description="alpha CLI")
    # argument definitions
    args = parser.parse_args()
    run(args)


def run(args: argparse.Namespace) -> None:
    raise NotImplementedError("replace with project-specific dispatch")


if __name__ == "__main__":
    main()
```

---

### Expected CLI Behaviour

```
python -m fubar
  python -m fubar.foo   Foo sub-package: [one-line description]
  python -m fubar.baz   Baz sub-package: [one-line description]

python -m fubar.foo
  python -m fubar.foo.alpha   Alpha sub-package: [one-line description]

python -m fubar.baz
  python -m fubar.baz.alpha   Alpha sub-package: [one-line description]
  python -m fubar.baz.bravo   Bravo sub-package: [one-line description]

python -m fubar.foo.alpha           # runs alpha's argparse CLI (shows help if needed)
python -m fubar.foo --flag value    # runs foo's own CLI
python -m fubar.foo.alpha.data      # runs data.py if it has `if __name__ == "__main__":`; no-op if not
```

### Rules

| Rule | Rationale |
|------|-----------|
| Packages are the preferred CLI entry; runnable `.py` modules with `if __name__ == "__main__":` are also valid | Packages scale to sub-commands; modules stay simple for single-file tools |
| No inward references in `__main__.py` — no `from ..` | Prevents upward references that would couple children to parents (see [check 2 Direction](README.md#2-direction)) and mask circular deps (see [check 1 Acyclicity](README.md#1-acyclicity-root-axiom)) |
| `commands()` returns relative names, not full paths | `__package__` constructs the path; names stay readable |
| `commands()` lists immediate children — sub-packages or runnable modules | Either is a valid invocation target via `python -m {parent}.{child}` |
| Parents register child names explicitly — no dynamic discovery | Explicit registration; no invisible capabilities |
| Depth + 1 only — never enumerate grandchildren | Each layer owns its own listing |
| Leaves return `commands() == []` | Keeps the contract uniform across all `__main__.py` files |
| Packages with their own CLI run it when args are given | No-args = listing; args = action |
| Printing confined to `_print_commands()` (Patterns 1 & 2) or `argparse` (Pattern 3) | Side-effect isolation; keeps listing logic testable without capturing stdout from arbitrary call sites |

### Registration

New sub-packages must be manually added to the parent's `commands()` list. This is intentional. Dynamic discovery hides what the system can do. Explicit registration makes capabilities visible and auditable.

When a new `__main__.py` is added, update the parent's `commands()` before merging. The registration contract is mechanized by `scripts/check_cli_commands.py`; see §4.

## 4. Enforcement

Enforcement here is local confirmation the owner can rely on, not a CI gate that replaces owner judgment — see [OWNERSHIP.md](../shared/OWNERSHIP.md).

Five tools enforce the coherence rules:

- `import-linter` checks acyclicity and direction ([`README.md`](README.md) checks 1–2).
- `scripts/check_upward_imports.py` enforces §1 (no upward imports from business modules to the root package), file-by-file.
- `scripts/check_cli_commands.py` enforces §3 (the `__main__.py` + `commands()` CLI contract) by walking the CLI tree, confirming every `python -m <pkg>` lists its registered children, and surfacing orphan `__main__.py` files that no parent registers.
- `scripts/check_string_relations.py` enforces [DJANGO.md §2](DJANGO.md#2-orm-relations) (no cross-module string ORM relations); skipped automatically when the consumer repo has no `manage.py`.
- `scripts/check_docs.py` enforces the [doc-coherence](../doc-coherence/README.md) mechanical pre-pass.

`check_upward_imports.py`, `check_docs.py`, and `check_string_relations.py` are wired into `pre-commit` and run on every commit via `.pre-commit-config.yaml`. `check_cli_commands.py` is a full-tree audit — it shells out `python -m <pkg>` for every node, which is too expensive for a per-commit hook — so it runs via `make arch PKG=<path>`, in CI, or on-demand. The per-project contract (layers, forbidden edges) lives in `pyproject.toml` under `[tool.importlinter]`.

For linter configuration and workflow (formatter-as-canonical, no inline suppressions, full-codebase scope), see [`../eng-review/PYTHON.md` §5 Linting & Verification](../eng-review/PYTHON.md#5-linting-verification).

Templates live in [`../templates/`](../templates/). To adopt on a new project:

1. Pick a variant under `../templates/`:
   - `ruff/` (recommended for new projects — ruff for lint, black for format)
   - `classic/` (black + isort + pylint)
2. Copy all blocks from the chosen variant's `pyproject.toml` into your project's `pyproject.toml` (merge into an existing file if present). Skip blocks that don't apply (e.g. `[tool.mypy]` if you don't type-check).
3. Copy the chosen variant's `pre-commit-config.yaml` to your project root as `.pre-commit-config.yaml` (add the leading dot on copy).
4. Copy the chosen variant's `Makefile` to your project root.
5. Copy the check scripts into your project's `scripts/` directory (shared across both variants):
   - `arch-coherence/scripts/check_upward_imports.py`
   - `arch-coherence/scripts/check_cli_commands.py`
   - `arch-coherence/scripts/check_string_relations.py` (Django projects; skipped at runtime otherwise)
   - `doc-coherence/scripts/check_docs.py`
6. Replace `<root>` with your top-level package name, and fill the layer rows with your own packages.
7. Install and enable:
   - Ruff variant: `pip install pre-commit ruff black mypy import-linter pytest && pre-commit install`
   - Classic variant: `pip install pre-commit black isort pylint mypy import-linter pytest && pre-commit install`

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

4. Peer direction reversed or removed → update layers or the forbidden contract.
5. Package changes role (leaf → consumer, etc.) → move to the appropriate layer row.

### Instruction to Claude or any agent

When making any architectural change under the source tree — adding a package, moving a module between packages, establishing a new peer import — update `[tool.importlinter]` in `pyproject.toml` in the same commit. The contract is source-of-truth for the dependency graph. If contract and code disagree, `lint-imports` fails and pre-commit rejects the commit.

### Verification

After editing the contract, run `lint-imports`. Output should be `Contracts: N kept, 0 broken.` If broken: either the code doesn't match the claimed architecture (fix the code) or the contract is stale (fix the contract).

### Template updates

`../templates/` is the canonical source. When the templates evolve (new pinned versions, new custom checks), consumer projects pull changes in by manually re-copying. `diff -u ../templates/<variant>/pre-commit-config.yaml .pre-commit-config.yaml` (where `<variant>` is `ruff` or `classic`) shows drift; merge intentionally.
