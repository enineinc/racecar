#!/usr/bin/env python3
"""instrument_telemetry.py — mechanically wire the usage-telemetry probe into a repo's CLIs.

Build telemetry rides the `make` gate, which sync owns; usage telemetry instruments the
package's own `python -m <pkg>` entrypoints, which sync cannot. This closes that gap so
`racecar-upgrade` starts usage collection too — deterministically, with no LLM judgment.

Two mechanical operations per racecar-compliant CLI (the §3 `main()` contract in
`arch-coherence/CLI.md`):

  1. Deliver the probe: copy racecar's `sysadmin-hardware/lib/_telemetry.py` to the top
     package as `<pkg>/_telemetry.py` (runtime code the CLI imports; canon, kept fresh).
  2. Wrap each `__main__.py` run-guard, parsed with `ast`. A single bare-`main()` dispatch —
     `main()`, `sys.exit(main())`, or `raise SystemExit(main())` (any callable name, read from
     the AST) — becomes `run(<name>)`, which is `sys.exit(main())` with measurement (see
     `_telemetry.run`), so the swap is behavior-preserving:

         if __name__ == "__main__":
             from <pkg>._telemetry import run
             run(main)

     Any other non-trivial guard body is wrapped whole in `with record():` — behavior-preserving
     for ANY body, since `record()` only measures and re-raises (it changes no control flow):

         if __name__ == "__main__":
             from <pkg>._telemetry import record
             with record():
                 <original body, re-indented>

     The splice replaces only the guard-body lines; the rest of the file is untouched byte-for-
     byte, and every generated file is `ast`-parsed before it is written — a transform that would
     not be valid Python is surfaced, not written. Idempotent: a guard already calling `run()` or
     `record()` is skipped, and a trivial (`pass`-only) guard has nothing to measure.

The only things not edited: a trivial guard (nothing to measure), a `__main__.py` not inside a
package (can't `from <pkg>._telemetry import`), and the rare transform that fails the ast check —
all REPORTED. The probe is delivered by AST comparison, so a re-run never fights the adopter's
formatter (a probe differing only in black line-length is left in place).

Usage:
    python3 scripts/instrument_telemetry.py --dest <repo>            # deliver + wrap
    python3 scripts/instrument_telemetry.py --dest <repo> --check    # report only, no writes
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_RACECAR_ROOT = Path(__file__).resolve().parents[1]
_PROBE_SRC = _RACECAR_ROOT / "sysadmin-hardware" / "lib" / "_telemetry.py"
_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "build", "dist",
    "__pycache__", ".tox", ".mypy_cache", ".pytest_cache",
}


def find_main_modules(repo: Path) -> list[Path]:
    """Every `__main__.py` under `repo`, excluding vendored / build / hidden trees."""
    out: list[Path] = []
    for path in repo.rglob("__main__.py"):
        parts = path.relative_to(repo).parts
        if any(p in _SKIP_DIRS or p.startswith(".") for p in parts):
            continue
        out.append(path)
    return sorted(out)


def top_package(main_py: Path) -> tuple[Path, str] | None:
    """(top-package dir, dotted top name) for a `__main__.py`, or None if not in a package.

    Walks up while the parent is still a package (has `__init__.py`), so a submodule entrypoint
    still resolves to the importable top package the probe lives in.
    """
    pkg_dir = main_py.parent
    if not (pkg_dir / "__init__.py").exists():
        return None  # __main__.py not in a package — cannot `from <pkg>._telemetry import run`
    top = pkg_dir
    while (top.parent / "__init__.py").exists():
        top = top.parent
    return top, top.name


def _is_name(node: ast.AST, name: str | None = None) -> bool:
    return isinstance(node, ast.Name) and (name is None or node.id == name)


def _bare_call_name(node: ast.AST) -> str | None:
    """If `node` is a no-arg call of a bare name (`main()`), return that name, else None."""
    if isinstance(node, ast.Call) and _is_name(node.func) and not node.args and not node.keywords:
        return node.func.id  # type: ignore[attr-defined]
    return None


def _dispatch_callable(stmt: ast.stmt) -> str | None:
    """The dispatched callable's name if `stmt` is a compliant single dispatch, else None.

    Recognizes `main()`, `sys.exit(main())` / `exit(main())`, and `raise SystemExit(main())`,
    for any callable name (read from the AST) taking no arguments.
    """
    if isinstance(stmt, ast.Expr):
        inner = _bare_call_name(stmt.value)
        if inner:
            return inner  # main()
        if isinstance(stmt.value, ast.Call) and len(stmt.value.args) == 1:
            func = stmt.value.func
            attr_exit = isinstance(func, ast.Attribute) and func.attr == "exit"
            if attr_exit or _is_name(func, "exit"):
                return _bare_call_name(stmt.value.args[0])  # sys.exit(main())
    if isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) \
            and _is_name(stmt.exc.func, "SystemExit") and len(stmt.exc.args) == 1:
        return _bare_call_name(stmt.exc.args[0])  # raise SystemExit(main())
    return None


def _is_main_guard(test: ast.expr) -> bool:
    """True if `test` is the comparison `__name__ == "__main__"`."""
    if not (isinstance(test, ast.Compare) and _is_name(test.left, "__name__")):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    comps = test.comparators
    return (
        len(comps) == 1
        and isinstance(comps[0], ast.Constant)
        and comps[0].value == "__main__"
    )


def _guard(tree: ast.Module) -> ast.If | None:
    """The `if __name__ == "__main__":` node, or None."""
    for node in tree.body:
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            return node
    return None


def _body_calls(body: list[ast.stmt], name: str) -> bool:
    """True if a top-level statement in `body` calls `name` — `name(...)` or `with name(...)`."""
    for stmt in body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) \
                and _is_name(stmt.value.func, name):
            return True
        if isinstance(stmt, ast.With):
            for item in stmt.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and _is_name(ctx.func, name):
                    return True
    return False


def _is_trivial(body: list[ast.stmt]) -> bool:
    """True if the guard body is only `pass` / a bare string or `...` — nothing to measure."""
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        return False
    return True


def analyze(source: str) -> tuple[str, str | None, tuple[int, int] | None, int]:
    """Classify a `__main__.py`: (status, callable, (body_start, body_end), indent).

    status ∈ {run, record, already, trivial, no-guard}:
      * run      — a single bare `main()` dispatch; wrap as `run(<name>)`.
      * record   — any other non-trivial guard body; wrap the whole body in `with record():`,
                   which is behavior-preserving for ANY body (record() only measures + re-raises).
      * already  — the guard already imports and calls run()/record().
      * trivial  — the body is only `pass` / a docstring; nothing to measure.
      * no-guard — no `if __name__ == "__main__":` block (also the fallback on a syntax error).
    Only `run` and `record` are edited, and every edit is ast-verified before it is written.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ("no-guard", None, None, 0)
    guard = _guard(tree)
    if guard is None:
        return ("no-guard", None, None, 0)
    body = guard.body
    if "._telemetry import" in source and (
        _body_calls(body, "run") or _body_calls(body, "record")
    ):
        return ("already", None, None, 0)
    if _is_trivial(body):
        return ("trivial", None, None, 0)
    start, end = body[0].lineno, body[-1].end_lineno or body[-1].lineno
    indent = body[0].col_offset
    if len(body) == 1:
        name = _dispatch_callable(body[0])
        if name:
            return ("run", name, (start, end), indent)
    return ("record", None, (start, end), indent)


def _reindent(lines: list[str], amount: int) -> list[str]:
    """Add `amount` spaces to each non-blank line; leave blank lines blank."""
    pad = " " * amount
    return [line if line.strip() == "" else pad + line for line in lines]


def wrap_run(source: str, top_name: str, callable_name: str,
             span: tuple[int, int], indent: int) -> str:
    """Splice a single-`main()` guard body to `run(<name>)` + import, rest verbatim."""
    start, end = span
    lines = source.splitlines(keepends=True)
    pad = " " * indent
    new_body = f"{pad}from {top_name}._telemetry import run\n{pad}run({callable_name})\n"
    return "".join(lines[: start - 1]) + new_body + "".join(lines[end:])


def wrap_record(source: str, top_name: str, span: tuple[int, int], indent: int) -> str:
    """Wrap a general guard body in `with record():` (body re-indented), rest verbatim."""
    start, end = span
    lines = source.splitlines(keepends=True)
    pad = " " * indent
    reindented = _reindent(lines[start - 1: end], 4)
    new_body = (
        f"{pad}from {top_name}._telemetry import record\n{pad}with record():\n"
        + "".join(reindented)
    )
    return "".join(lines[: start - 1]) + new_body + "".join(lines[end:])


def deliver_probe(top_dir: Path, check: bool) -> bool:
    """Copy the canon probe to `<top>/_telemetry.py` unless it is already semantically identical.

    Compares by AST, not bytes, so a re-run does not fight the adopter's formatter (black line-
    length): a probe differing only in formatting is left in place; only a real canon code change
    re-delivers. Returns True if it (would) change.
    """
    dest = top_dir / "_telemetry.py"
    canon = _PROBE_SRC.read_text(encoding="utf-8")
    if dest.exists():
        try:
            same = ast.dump(ast.parse(dest.read_text(encoding="utf-8"))) == ast.dump(
                ast.parse(canon)
            )
        except SyntaxError:
            same = False
        if same:
            return False
    if not check:
        dest.write_text(canon, encoding="utf-8")
    return True


def instrument(repo: Path, check: bool) -> dict[str, list[str]]:
    """Deliver the probe and wrap each entrypoint's guard; return a report by outcome."""
    report: dict[str, list[str]] = {
        "wrapped": [], "already": [], "trivial": [], "surfaced": [],
        "no-package": [], "delivered": [],
    }
    for main_py in find_main_modules(repo):
        rel = str(main_py.relative_to(repo))
        top = top_package(main_py)
        if top is None:
            report["no-package"].append(rel)
            continue
        top_dir, top_name = top
        if deliver_probe(top_dir, check):
            report["delivered"].append(str((top_dir / "_telemetry.py").relative_to(repo)))
        source = main_py.read_text(encoding="utf-8")
        status, name, span, indent = analyze(source)
        if status == "already":
            report["already"].append(rel)
        elif status in ("trivial", "no-guard"):
            report["trivial"].append(rel)
        elif status in ("run", "record"):
            assert span is not None
            wrapped = (
                wrap_run(source, top_name, name, span, indent)
                if status == "run"
                else wrap_record(source, top_name, span, indent)
            )
            try:
                ast.parse(wrapped)  # only write a transform that is valid Python
            except SyntaxError:
                report["surfaced"].append(rel)
                continue
            if not check:
                main_py.write_text(wrapped, encoding="utf-8")
            report["wrapped"].append(rel)
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse `--dest <repo> [--check]`."""
    parser = argparse.ArgumentParser(
        description="Mechanically instrument a repo's compliant CLIs for usage telemetry."
    )
    parser.add_argument("--dest", type=Path, required=True, help="Target repo to instrument.")
    parser.add_argument(
        "--check", action="store_true",
        help="Report only; write nothing. Exit 1 if any compliant entrypoint is un-instrumented.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Instrument (or --check) the repo; print a report; exit code fits the mode."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    repo = args.dest.resolve()
    if not repo.is_dir():
        print(f"instrument_telemetry: no such repo: {repo}", file=sys.stderr)
        return 2
    report = instrument(repo, args.check)
    verb = "would wrap" if args.check else "wrapped"
    for rel in report["delivered"]:
        print(f"instrument_telemetry: {'would deliver' if args.check else 'delivered'} {rel}")
    for rel in report["wrapped"]:
        print(f"instrument_telemetry: {verb} {rel}")
    for rel in report["already"]:
        print(f"instrument_telemetry: already instrumented {rel}")
    for rel in report["surfaced"]:
        print(f"instrument_telemetry: SURFACED (manual) {rel} — the record() wrap did not produce "
              f"valid Python; wrap it by hand (see sysadmin-hardware/TELEMETRY.md)")
    for rel in report["no-package"]:
        print(f"instrument_telemetry: skipped {rel} — __main__.py is not inside a package")
    n = len(report["wrapped"])
    print(f"instrument_telemetry: {n} entrypoint(s) {verb}, {len(report['already'])} already, "
          f"{len(report['trivial'])} trivial, {len(report['surfaced'])} to do by hand.")
    if args.check and report["wrapped"]:
        return 1  # un-instrumented entrypoints exist
    return 0


if __name__ == "__main__":
    sys.exit(main())
