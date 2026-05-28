# Python — Engineering Hygiene

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Python-specific engineering hygiene — naming, formatting, testing, linting workflow, and the Definition of Done. For Python architectural coherence (module structure, imports, enforcement), see [`../arch-coherence/PYTHON.md`](../arch-coherence/PYTHON.md); for the CLI contract specifically, see [`../arch-coherence/CLI.md`](../arch-coherence/CLI.md). For Django-specific hygiene, see [`DJANGO.md`](DJANGO.md).

Sections are ordered as a DAG — most independent first, most dependent last.

## 1. Mindset

How you work, not what you write. Items here guide judgment and process; they are not testable rules and are not enforced by the Definition of Done (§6).

- **Incremental execution.** Start with a minimal, working setup before adding complexity. Prove the concept first.
- **Fail fast.** Use explicit exception handling. Avoid silent failures or broad catch-all blocks.

## 2. Naming

What things are called. Independent of structure and tooling. "Names describe function, not format" is the scope-honesty rule expressed at the code level — the same rule appears at the review level in [`README.md`](README.md) (check 1 — scope honesty of names) and at the prose level in [`../doc-coherence/README.md`](../doc-coherence/README.md#the-five-document-checks) (check 2 — scope honesty of labels).

- **Names describe function, not format.** A business module that parses or writes data is named `data.py`, not `yaml.py` — file format is auto-detected from extension, not assumed. (Tooling config files like `pyproject.toml` or `pre-commit-config.yaml` name the tool or format by convention; this rule is about code modules.)
- **Names describe a specific concept.** Module names must not be `utils`, `helpers`, `common`, `misc`, or `shared` when a specific concept applies — a module of date-parsing functions is `dates`, not `utils`.
- **Function names describe full behavior.** A function named `validate` that also mutates is really `validate_and_normalize`, or two functions. Names must not understate side effects.
- **Non-private functions do not start with `_`.** The underscore prefix is reserved for genuinely private methods (class name-mangling, module internals not used outside the file). If a function is called from another module, it is not private.
- **Type hints on all public signatures.** Every non-private function, method, and class attribute crossing a module boundary has complete type annotations. Prefer `pathlib.Path` over `os.path`.

## 3. Formatting

Tool-enforced style. Independent of architecture. Two variants; pick one per project.

**Ruff variant** (recommended for new projects):
- **Formatter is canonical.** `ruff format` is enforced (black-compatible output). No manual style overrides.
- **Import ordering.** `ruff check` enforces stdlib → third-party → local via the `I` rule in the template's selected set. See [templates/ruff/pyproject.toml](../templates/ruff/pyproject.toml) for the full rule selection.

**Classic variant:**
- **Formatter is canonical.** `black` formatting is enforced.
- **Import ordering.** `isort` groups: stdlib → third-party → local.

Both variants:
- **Strings.** Use f-strings. No `%` or `.format()`.

## 4. Testing

- `pytest` or `unittest` for all tests.

## 5. Linting & Verification

Final gate. Depends on everything above being correct. The linters configured here also enforce the architectural rules described in [`../arch-coherence/PYTHON.md` §4 Enforcement](../arch-coherence/PYTHON.md#4-enforcement); this section covers the workflow hygiene around running them and triaging output.

- **Full-codebase scope.** Lint the entire project. Partial-set linting is not acceptable.
- **Linter returns clean output.**
  - Ruff variant: `ruff check` returns clean. Django projects additionally require `pylint --load-plugins pylint_django` — see [`DJANGO.md` §3](DJANGO.md#3-linting).
  - Classic variant: `pylint` returns clean.
- **No inline suppressions.** Neither `# noqa` (ruff/flake8), `# ruff: noqa`, `# pylint: disable=` (classic), nor `# fmt: off` / `# fmt: on` are acceptable. If the linter or formatter flags a problem, fix the code, not the suppression.

When clearing existing pylint findings on a dirty codebase, the order of attack matters. Two phases:

### Machine phase (unsupervised)

Auto-fix `I` → `C` → mechanical-`W` (`unused-import`, `unused-variable`). Rerun pylint between passes.

### Collaborative phase (machine proposes, human ratifies)

`R` first — refactor findings (`too-many-branches`, `too-many-locals`, `duplicate-code`) reshape the code, so chasing `E`/`F` in pre-refactor structure wastes work or lands the fix in the wrong place. Then `E`, `F`, and judgment-heavy `W` (`broad-except`, `logging-fstring-interpolation`, `protected-access`) — these need intent the machine can draft but not ratify alone.

**Ruff variant.** Same machine-vs-collaborative split, but the cut runs along whether the fix is mechanical or design-shaped — ruff has no five-letter category taxonomy to anchor on.

## 6. Definition of Done

After modifying code, verify:

1. **Format + safe fixes.**
   - Ruff variant: `ruff check --fix src/` then `ruff format src/`.
   - Classic variant: `isort src/` then `black src/`.
2. **Lint clean.**
   - Ruff variant: `ruff check src/` passes. Django projects additionally require `pylint --load-plugins pylint_django` — see [`DJANGO.md` §3](DJANGO.md#3-linting).
   - Classic variant: `pylint src/` passes.
3. Test suite passes with 0 regressions.
4. No `print()` statements in business logic. `print()` is permitted only in CLI entry files (`__main__.py`) via `_print_commands()` (Patterns 1 & 2) or `argparse` output (Pattern 3) — see [`../arch-coherence/CLI.md`](../arch-coherence/CLI.md). No temporary `TODO`s remain.
