#!/usr/bin/env python3
"""Enforce arch-coherence/DJANGO.md §2: no cross-module string references in ORM relations.

Reads `[tool.importlinter].root_packages` from the library pyproject (located
via `detect_shape`: `pypkg/src/pyproject.toml` for the pypkg+djapp shape, the
root pyproject for a standalone djapp) and walks each named package. The package
directories are located by globbing the project tree, so a root under `pypkg/src`,
under `djapp/`, or at the repo root is found wherever it lives, never assumed from
the shape. It flags any `ForeignKey`, `OneToOneField`, or `ManyToManyField` call
whose target is a cross-module string literal. Three
forms are exempted because they cross no module boundary and so cannot hide
a cycle:

  - `settings.AUTH_USER_MODEL` (an attribute access, not a string).
  - `"self"` — required for self-references inside a class body.
  - An unqualified string whose name matches a class defined at module
    top-level in the same file (a forward reference; reorder the classes
    if you want the symbol form, but it is architecturally inert).

Files under any `migrations/` directory are skipped: Django generates them
mechanically and `app_label.model` strings are how migrations serialize
relationships — they are not hand-written architectural choices.

Each violation is classified against Django's `INSTALLED_APPS`:

  - LIVE — the file's containing app is in `INSTALLED_APPS`. Annotated with
    the file's DAG layer (from `[tool.importlinter].contracts` of type
    `layers`) and, where resolvable, the target app's layer plus an UPWARD
    flag if the target sits above the file in the DAG.
  - NOOP — the file's containing app is NOT in `INSTALLED_APPS`. Django will
    not load these models; the violation is dead code, but listed so the
    reader can decide between deletion and registration.

`INSTALLED_APPS` is obtained via `python manage.py shell` (boots Django so
dynamic settings resolve correctly). For tests or constrained environments,
set `STRING_RELATIONS_INSTALLED_APPS` to a comma-separated override list.

String references defeat the import graph: two models can reference each
other without either import appearing, papering over a cycle that the
arch-coherence acyclicity axiom makes a Blocker. The DAG annotation makes
the worst variant — upward layer crossings — explicit.

Usage:
    python scripts/check_dj_model_ref_as_string.py

Exits 0 if clean, 1 if any violation is found, 2 on configuration error.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from check_packaging import detect_shape

RELATION_FIELDS = frozenset({"ForeignKey", "OneToOneField", "ManyToManyField"})

_INSTALLED_APPS_SCRIPT = (
    "import json,sys;"
    "from django.conf import settings;"
    "sys.stdout.write('__INSTALLED_APPS__='+json.dumps(list(settings.INSTALLED_APPS)))"
)


def _load_pyproject(pyproject: Path | None) -> dict:
    # The importlinter config (root_packages, layers) lives in the LIBRARY pyproject,
    # located via detect_shape: pypkg/src/pyproject.toml for pypkg+djapp, the root
    # pyproject for a standalone djapp. The djapp pyproject is deps-only and never
    # carries [tool.importlinter] (PACKAGING.md §"Pyproject rules").
    if pyproject is None or not pyproject.is_file():
        print("check_dj_model_ref_as_string: pyproject.toml not found", file=sys.stderr)
        sys.exit(2)
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))


def _root_packages(data: dict) -> list[str]:
    try:
        roots = data["tool"]["importlinter"]["root_packages"]
    except KeyError:
        print(
            "check_dj_model_ref_as_string: [tool.importlinter].root_packages "
            "missing from pyproject.toml",
            file=sys.stderr,
        )
        sys.exit(2)
    if not isinstance(roots, list) or not all(isinstance(r, str) for r in roots):
        print(
            "check_dj_model_ref_as_string: [tool.importlinter].root_packages "
            "must be a list of strings",
            file=sys.stderr,
        )
        sys.exit(2)
    return roots


def _dag_layers(data: dict) -> list[str]:
    """Return layers from the first `[tool.importlinter.contracts]` of type `layers`."""
    contracts = data.get("tool", {}).get("importlinter", {}).get("contracts", [])
    for contract in contracts:
        if contract.get("type") == "layers":
            layers = contract.get("layers", [])
            if isinstance(layers, list) and all(isinstance(x, str) for x in layers):
                return layers
    return []


def _installed_apps(manage_py: Path | None) -> list[str]:
    override = os.environ.get("STRING_RELATIONS_INSTALLED_APPS")
    if override is not None:
        return [s.strip() for s in override.split(",") if s.strip()]
    if manage_py is None:
        print(
            "check_dj_model_ref_as_string: not a Django project (no manage.py) — skipping"
        )
        sys.exit(0)
    result = subprocess.run(
        [sys.executable, manage_py.name, "shell", "-c", _INSTALLED_APPS_SCRIPT],
        cwd=manage_py.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"check_dj_model_ref_as_string: manage.py shell failed "
            f"(exit {result.returncode}):\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(2)
    for line in result.stdout.splitlines():
        if line.startswith("__INSTALLED_APPS__="):
            return json.loads(line[len("__INSTALLED_APPS__=") :])
    print(
        "check_dj_model_ref_as_string: could not parse INSTALLED_APPS from manage.py output",
        file=sys.stderr,
    )
    sys.exit(2)


def _longest_prefix(dotted: str, candidates: list[str]) -> str | None:
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in candidates:
            return candidate
    return None


def _resolve_target_app(target: str, installed: list[str]) -> str | None:
    """Match `'app_label.Model'` against INSTALLED_APPS by last-component label."""
    if "." not in target:
        return None
    app_label = target.split(".", 1)[0]
    for entry in installed:
        if entry.split(".")[-1] == app_label:
            return entry
    return None


def _file_to_dotted(path: Path) -> str:
    return ".".join(path.with_suffix("").parts)


def _target_node(call: ast.Call) -> ast.expr | None:
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "to":
            return kw.value
    return None


def _violations(path: Path) -> list[tuple[int, str, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    same_file_classes = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in RELATION_FIELDS:
            continue
        target = _target_node(node)
        if not (isinstance(target, ast.Constant) and isinstance(target.value, str)):
            continue
        value = target.value
        if value == "self":
            continue
        if "." not in value and value in same_file_classes:
            continue
        found.append((node.lineno, func.attr, value))
    return found


def _annotate(
    file_dotted: str,
    target: str,
    installed: list[str],
    layers: list[str],
) -> list[str]:
    notes: list[str] = []
    file_layer = _longest_prefix(file_dotted, layers)
    if file_layer:
        notes.append(f"file layer: {file_layer}")
    target_app = _resolve_target_app(target, installed)
    if target_app is None:
        if "." in target:
            notes.append(
                f"target app label '{target.split('.', 1)[0]}' not in INSTALLED_APPS"
            )
    else:
        target_layer = _longest_prefix(target_app, layers)
        if target_layer and file_layer:
            if layers.index(target_layer) < layers.index(file_layer):
                notes.append(f"target layer: {target_layer} (UPWARD DAG cross)")
            else:
                notes.append(f"target layer: {target_layer}")
        elif target_layer:
            notes.append(f"target layer: {target_layer}")
    return notes


_SKIP_DIRS = frozenset(
    {"venv", "node_modules", "__pycache__", "migrations", "build", "dist", "site-packages"}
)


def _package_index(project_root: Path) -> dict[str, list[Path]]:
    """Map every directory name in the project to where it occurs on disk, one pruned
    walk. Virtualenvs, caches, build output, migrations, and dotted dirs are skipped.

    Package locations are GLOBBED rather than derived from the shape: `root_packages`
    can sit under any source root (`pypkg/src` for a library package, `djapp/` for a
    Django app, the repo root for a standalone djapp), so the directories are found
    wherever they are instead of assuming a fixed per-shape layout.
    """
    index: dict[str, list[Path]] = {}
    for dirpath, dirnames, _filenames in os.walk(project_root):
        dirnames[:] = [
            d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
        ]
        here = Path(dirpath)
        index.setdefault(here.name, []).append(here)
    return index


def _find_package_dir(
    name: str, index: dict[str, list[Path]], project_root: Path
) -> Path | None:
    """Return the on-disk directory for top-level package `name`, or None. When the
    name occurs more than once, the shallowest path wins: the source-root-level
    package, not a same-named nested subpackage."""
    matches = index.get(name, [])
    if not matches:
        return None
    return min(matches, key=lambda p: len(p.relative_to(project_root).parts))


def main() -> int:
    """Run the check and return a process exit code (0 clean, nonzero on findings)."""
    # detect_shape supplies the two things that are genuinely shape-determined: where
    # the importlinter contract lives (the library pyproject) and where Django boots
    # (manage.py). The package directories named in root_packages are not assumed from
    # the shape; they are globbed from the tree (`_package_index`), so a root sitting
    # under pypkg/src, under djapp/, or at the repo root is found wherever it actually is.
    shape = detect_shape(Path.cwd())[0]
    installed = _installed_apps(shape.manage_py)
    data = _load_pyproject(shape.library_pyproject)
    roots = _root_packages(data)
    layers = _dag_layers(data)

    live: list[str] = []
    noop: list[str] = []

    cwd = Path.cwd()
    index = _package_index(cwd)
    for root in roots:
        root_dir = _find_package_dir(root, index, cwd)
        if root_dir is None:
            print(
                f"check_dj_model_ref_as_string: root package '{root}' not on disk; skipping",
                file=sys.stderr,
            )
            continue
        src_root = root_dir.parent
        for path in sorted(root_dir.rglob("*.py")):
            if "migrations" in path.parts:
                continue
            file_dotted = _file_to_dotted(path.relative_to(src_root))
            display = path.relative_to(cwd)
            file_app = _longest_prefix(file_dotted, installed)
            for lineno, field_name, target in _violations(path):
                head = f"{display}:{lineno}: {field_name} string reference forbidden: '{target}'"
                if file_app is None:
                    noop.append(head)
                    continue
                notes = _annotate(file_dotted, target, installed, layers)
                live.append(head + (" [" + " · ".join(notes) + "]" if notes else ""))

    if live:
        print("LIVE violations (file's app is in INSTALLED_APPS):")
        for entry in live:
            print(f"  {entry}")
    if noop:
        if live:
            print()
        print(
            "NOOP modules (file's app is NOT in INSTALLED_APPS — "
            "Django will not load these models):"
        )
        for entry in noop:
            print(f"  {entry}")

    return 1 if (live or noop) else 0


if __name__ == "__main__":
    sys.exit(main())
