"""Tests for scripts/check_cli_commands.py.

Each test builds a `fubar/{foo,bar}/{alpha,bravo}/{date,time}` tree in a tmp dir,
including two tier-3 ORPHAN packages `fubar.foo.date` and `fubar.bar.date` that
exist on disk but are omitted from their parents' `commands()`.

The test constructs the expected audit tree (the exact nested dict the script's
`audit_cli_tree` should return) from the same spec it used to build the tree on
disk, then invokes the script via subprocess with `--json` and asserts the
returned JSON equals the expected structure verbatim.

Run with:
    pytest arch-coherence/tests/test_check_cli_commands.py
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_cli_commands.py"


# ---------- templates ---------------------------------------------------- #

_PRINT_COMMANDS = '''\
def _print_commands():
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\\nAppend --help to any command for its options.")

'''

_PRINT_COMMANDS_WRONG_DESC = '''\
def _print_commands():
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   WRONG {desc}")
    print("\\nAppend --help to any command for its options.")

'''

_MAIN_P2 = '''\
def parser():
    p = argparse.ArgumentParser()
    p.add_argument("--flag", default="")
    return p


def main():
    if not sys.argv[1:]:
        _print_commands()
        return
    parser().parse_args()

'''

_MAIN_P3 = '''\
def parser():
    p = argparse.ArgumentParser()
    p.add_argument("--flag", default="")
    return p


def main():
    parser().parse_args()

'''


# ---------- spec --------------------------------------------------------- #


@dataclass
class NodeSpec:
    pkg: str
    pattern: int                               # 1, 2, or 3
    commands: list[tuple[str, str]]            # what commands() returns
    fault: str = "correct"
    # Actual direct children written to disk, in the order the orphan scan
    # will discover them (alphabetical).
    disk_children: list[str] = field(default_factory=list)


FAULTS = ["correct", "no_main_py", "missing_commands_fn", "desc_mismatch"]


# ---------- builder ------------------------------------------------------ #


def _imports(pattern: int) -> str:
    if pattern == 1:
        return "import sys\n\n"
    if pattern == 2:
        return "import argparse\nimport sys\n\n"
    return "import argparse\n\n"


def _guard(pattern: int) -> str:
    if pattern == 1:
        return 'if __name__ == "__main__":\n    _print_commands()\n    sys.exit(0)\n'
    return 'if __name__ == "__main__":\n    main()\n'


def _render_main_py(spec: NodeSpec) -> str:
    parts: list[str] = [_imports(spec.pattern)]
    if spec.fault != "missing_commands_fn":
        parts.append(f"def commands(): return {spec.commands!r}\n\n")
    if spec.pattern in (1, 2):
        parts.append(_PRINT_COMMANDS_WRONG_DESC if spec.fault == "desc_mismatch" else _PRINT_COMMANDS)
    if spec.pattern == 2:
        parts.append(_MAIN_P2)
    if spec.pattern == 3:
        parts.append(_MAIN_P3)
    parts.append(_guard(spec.pattern))
    return "".join(parts)


def _write_pkg(base: Path, spec: NodeSpec) -> None:
    pkg_dir = base / Path(*spec.pkg.split("."))
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("")
    if spec.fault == "no_main_py":
        return
    (pkg_dir / "__main__.py").write_text(_render_main_py(spec))


# ---------- tree construction ------------------------------------------- #


def _pattern_name(pattern: int) -> str:
    return f"pattern-{pattern}"


def _build_tree(base: Path, seed: int, faults_pool: list[str] | None = None) -> dict[str, NodeSpec]:
    rng = random.Random(seed)
    pool = faults_pool if faults_pool is not None else FAULTS
    specs: dict[str, NodeSpec] = {}

    # Tier 1 root — Pattern 1, always correct.
    specs["fubar"] = NodeSpec(
        pkg="fubar",
        pattern=1,
        commands=[("foo", "Foo branch"), ("bar", "Bar branch")],
        disk_children=["bar", "foo"],  # alphabetical, as the scan returns
    )

    # Tier 2 — Pattern 1, always correct. `alpha` and `bravo` are registered;
    # `date` is the deliberate orphan on disk.
    for t2 in ("foo", "bar"):
        specs[f"fubar.{t2}"] = NodeSpec(
            pkg=f"fubar.{t2}",
            pattern=1,
            commands=[("alpha", "Alpha"), ("bravo", "Bravo")],
            disk_children=["alpha", "bravo", "date"],
        )

    # Tier 3 registered — random fault, random Pattern 1 or 2.
    for t2 in ("foo", "bar"):
        for t3 in ("alpha", "bravo"):
            specs[f"fubar.{t2}.{t3}"] = NodeSpec(
                pkg=f"fubar.{t2}.{t3}",
                pattern=rng.choice([1, 2]),
                commands=[("date", "Date leaf"), ("time", "Time leaf")],
                fault=rng.choice(pool),
                disk_children=["date", "time"],
            )

    # Tier 3 ORPHANS — `fubar.foo.date` and `fubar.bar.date`. Correct Pattern 3
    # leaves so the orphan flag from the parent is the only issue they produce.
    for t2 in ("foo", "bar"):
        specs[f"fubar.{t2}.date"] = NodeSpec(
            pkg=f"fubar.{t2}.date",
            pattern=3,
            commands=[],
        )

    # Tier 4 leaves — random fault, Pattern 3.
    for t2 in ("foo", "bar"):
        for t3 in ("alpha", "bravo"):
            for t4 in ("date", "time"):
                specs[f"fubar.{t2}.{t3}.{t4}"] = NodeSpec(
                    pkg=f"fubar.{t2}.{t3}.{t4}",
                    pattern=3,
                    commands=[],
                    fault=rng.choice(pool),
                )

    for spec in specs.values():
        _write_pkg(base, spec)
    return specs


# ---------- expected audit tree ----------------------------------------- #


def _empty_node(pkg: str, *, orphan: bool) -> dict:
    # Mirrors check_cli_commands._make_node + _enrich applied with no
    # parent description. The enriched fields (command, role, description,
    # args, subcommands) are present on every node post-enrichment; absence
    # would not match the actual output.
    return {
        "pkg": pkg,
        "kind": "missing",
        "pattern": "unknown",
        "commands": None,
        "subcommands": None,
        "orphan": orphan,
        "violations": [],
        "children": [],
        "command": f"python -m {pkg}",
        "role": "unknown",
        "description": None,
        "args": None,
    }


_PATTERN_LABEL = {
    "pattern-1": "Pattern 1 (pure discovery)",
    "pattern-2": "Pattern 2 (discovery + own CLI)",
    "pattern-3": "Pattern 3 (leaf)",
}

_BRIEF_PATTERN = {
    "pattern-1": "pure-discovery",
    "pattern-2": "discovery+cli",
    "pattern-3": "leaf",
    "unknown": "unknown",
}


def _expected_node(
    spec: NodeSpec,
    specs: dict[str, NodeSpec],
    orphan: bool,
    parent_descriptions: dict[str, str] | None = None,
) -> dict:
    """Compute the expected audit dict for one node from the spec graph."""
    leaf_name = spec.pkg.rsplit(".", 1)[-1]
    parent_desc = (
        parent_descriptions.get(leaf_name) if parent_descriptions is not None else None
    )

    if spec.fault == "no_main_py":
        node = _empty_node(spec.pkg, orphan=orphan)
        node["description"] = parent_desc
        node["violations"].append("no __main__.py (not importable as `python -m ...`)")
        # Broken-state descent: every direct sub-package on disk is audited.
        for name in sorted(spec.disk_children):
            child_spec = specs.get(f"{spec.pkg}.{name}")
            if child_spec is not None:
                node["children"].append(_expected_node(child_spec, specs, orphan=False))
        return node

    node = _empty_node(spec.pkg, orphan=orphan)
    node["kind"] = "package"
    node["description"] = parent_desc

    if spec.fault == "missing_commands_fn":
        node["violations"].append("missing `commands()` function in __main__.py")
        for name in sorted(spec.disk_children):
            child_spec = specs.get(f"{spec.pkg}.{name}")
            if child_spec is not None:
                node["children"].append(_expected_node(child_spec, specs, orphan=False))
        return node

    node["commands"] = [[n, d] for n, d in spec.commands]
    node["pattern"] = _pattern_name(spec.pattern)
    node["role"] = _BRIEF_PATTERN[_pattern_name(spec.pattern)]
    # Pattern 1 has no main()/no parser() → args stays None.
    # Patterns 2 and 3 in the fixture expose `parser()` returning a parser
    # with one `--flag` arg (default=""). The audit introspects it and
    # populates `args` with that single entry.
    if spec.pattern in (2, 3):
        node["args"] = [
            {"dest": "flag", "flags": ["--flag"], "default": ""}
        ]

    # At this point we know: correct or desc_mismatch. Both have commands(),
    # both have the right pattern-identifying symbols.

    if spec.fault == "desc_mismatch":
        for name, desc in spec.commands:
            printed_desc = f"WRONG {desc}"
            node["violations"].append(
                f"description mismatch for `{spec.pkg}.{name}`: "
                f"commands()={desc!r}, printed={printed_desc!r}"
            )

    # Registered children recursion. Pass own commands() as the
    # parent_descriptions so children get their description field populated.
    own_descriptions = {n: d for n, d in spec.commands}
    registered = set()
    for name, _desc in spec.commands:
        registered.add(name)
        child_spec = specs[f"{spec.pkg}.{name}"]
        node["children"].append(
            _expected_node(child_spec, specs, orphan=False, parent_descriptions=own_descriptions)
        )

    # Orphan scan: any disk_child with a __main__.py (fault != no_main_py) and
    # not registered. Alphabetical order. Orphan children have no description
    # in the parent's commands() (that's what makes them orphan).
    orphan_names = sorted(
        name
        for name in spec.disk_children
        if name not in registered
        and specs.get(f"{spec.pkg}.{name}")
        and specs[f"{spec.pkg}.{name}"].fault != "no_main_py"
    )
    for name in orphan_names:
        child_pkg = f"{spec.pkg}.{name}"
        child_spec = specs[child_pkg]
        node["violations"].append(
            f"§3 orphan sub-package CLI: `{child_pkg}` has __main__.py "
            f"but is not in parent's commands()"
        )
        node["children"].append(
            _expected_node(child_spec, specs, orphan=True, parent_descriptions=None)
        )

    return node


def _expected_tree(specs: dict[str, NodeSpec]) -> dict:
    # Top-level root has no parent → description stays None.
    return _expected_node(specs["fubar"], specs, orphan=False, parent_descriptions=None)


# ---------- runner ------------------------------------------------------ #


def _run_json(base: Path) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONPATH": str(base)}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "fubar"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        pytest.fail(f"script exited {result.returncode}; stderr:\n{result.stderr}")
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"script did not emit valid JSON: {exc}\nstdout:\n{result.stdout}")


# ---------- tests ------------------------------------------------------- #


@pytest.mark.parametrize("seed", [0, 1, 2, 7, 42])
def test_audit_tree_matches_spec(tmp_path: Path, seed: int) -> None:
    """The audit tree from the script must equal the expected tree computed
    from the same spec, verbatim."""
    specs = _build_tree(tmp_path, seed)
    expected = _expected_tree(specs)
    rc, actual = _run_json(tmp_path)

    assert actual == expected, _diff_message(expected, actual)
    has_violations = bool(list(_flatten_violations(expected)))
    assert (rc == 1) == has_violations, f"exit code {rc} disagrees with has_violations={has_violations}"


def test_orphans_are_tier_3_foo_date_and_bar_date(tmp_path: Path) -> None:
    """Force everything else correct and confirm `fubar.foo.date` / `fubar.bar.date`
    appear in the tree as orphan children and the parent carries the orphan
    violation. Also confirm the parent's no-args listing does NOT show them."""
    specs = _build_tree(tmp_path, seed=0, faults_pool=["correct"])
    expected = _expected_tree(specs)
    rc, actual = _run_json(tmp_path)

    assert actual == expected

    foo = next(c for c in actual["children"] if c["pkg"] == "fubar.foo")
    bar = next(c for c in actual["children"] if c["pkg"] == "fubar.bar")
    for parent, parent_spec in [(foo, specs["fubar.foo"]), (bar, specs["fubar.bar"])]:
        orphan_children = [c for c in parent["children"] if c["orphan"]]
        assert [c["pkg"] for c in orphan_children] == [f"{parent['pkg']}.date"]
        assert any("orphan sub-package CLI" in v for v in parent["violations"])

    # And from the other direction: `python -m fubar.foo` no-args must not list `date`.
    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    for parent_pkg in ("fubar.foo", "fubar.bar"):
        proc = subprocess.run(
            [sys.executable, "-m", parent_pkg],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert f"python -m {parent_pkg}.date" not in proc.stdout, proc.stdout

    assert rc == 1  # orphan presence → non-zero exit


def test_broken_root_still_descends(tmp_path: Path) -> None:
    """A root without __main__.py must still surface CLI entries hiding below —
    they're all orphans (nothing registers them). Mirrors the `gfem` case
    where the user hit a silent `FAIL (1)` with no subtree shown."""
    # Build a valid tree, then delete the root's __main__.py to break it.
    specs = _build_tree(tmp_path, seed=0, faults_pool=["correct"])
    (tmp_path / "fubar" / "__main__.py").unlink()

    rc, actual = _run_json(tmp_path)

    # Root reports the missing __main__.py.
    assert actual["pkg"] == "fubar"
    assert any("no __main__.py" in v for v in actual["violations"])

    # Root still has the tier-2 sub-packages as children — hidden CLI entries
    # below are visible now, not silently dropped.
    child_pkgs = [c["pkg"] for c in actual["children"]]
    assert "fubar.foo" in child_pkgs
    assert "fubar.bar" in child_pkgs

    # And their tier-3 descendants (including the orphans) still audit correctly.
    foo = next(c for c in actual["children"] if c["pkg"] == "fubar.foo")
    foo_child_pkgs = [c["pkg"] for c in foo["children"]]
    assert "fubar.foo.alpha" in foo_child_pkgs
    assert "fubar.foo.bravo" in foo_child_pkgs
    assert "fubar.foo.date" in foo_child_pkgs  # the orphan

    assert rc == 1  # root is broken → non-zero exit


def test_silent_omission_of_parser_factory(tmp_path: Path) -> None:
    """A Pattern 3 leaf that constructs argparse.ArgumentParser inline in
    main() — without exposing a parser() factory — is a silent omission of
    the parser-factory contract. The AST scan must catch it."""
    pkg = tmp_path / "fubar"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(
        "import argparse\n"
        "def commands(): return []\n"
        "def main():\n"
        "    p = argparse.ArgumentParser()\n"
        "    p.add_argument('--flag', default='')\n"
        "    p.parse_args()\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    rc, actual = _run_json(tmp_path)
    assert rc == 1, "audit should exit non-zero when a silent omission is detected"
    violations = actual["violations"]
    assert any(
        "no `parser()` factory is exposed" in v for v in violations
    ), f"expected parser-factory omission violation; got {violations!r}"


def test_silent_omission_of_subcommands(tmp_path: Path) -> None:
    """A Pattern 3 leaf that uses add_subparsers() without declaring
    subcommands() is also a silent omission — distinct from the parser()
    factory omission; both can fire independently."""
    pkg = tmp_path / "fubar"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(
        "import argparse\n"
        "def commands(): return []\n"
        "def parser():\n"
        "    p = argparse.ArgumentParser()\n"
        "    sub = p.add_subparsers(dest='action', required=True)\n"
        "    sub.add_parser('sync', help='sync stuff')\n"
        "    sub.add_parser('status', help='status stuff')\n"
        "    return p\n"
        "def main():\n"
        "    parser().parse_args()\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    rc, actual = _run_json(tmp_path)
    assert rc == 1, "audit should exit non-zero when subcommands() is omitted"
    violations = actual["violations"]
    assert any(
        "no `subcommands()` declared" in v for v in violations
    ), f"expected subcommands omission violation; got {violations!r}"


def test_importable_api(tmp_path: Path) -> None:
    """audit_cli_tree is the library entry point; import and call it directly."""
    specs = _build_tree(tmp_path, seed=3, faults_pool=["correct"])
    expected = _expected_tree(specs)

    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    probe = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(SCRIPT.parent)!r})\n"
        "from check_cli_commands import audit_cli_tree\n"
        "print(json.dumps(audit_cli_tree('fubar')))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected


# ---------- diagnostics ------------------------------------------------- #


def _flatten_violations(node: dict):
    for msg in node["violations"]:
        yield (node["pkg"], msg)
    for child in node["children"]:
        yield from _flatten_violations(child)


def _diff_message(expected: dict, actual: dict) -> str:
    """Produce a readable diff between two audit dicts."""
    exp_v = list(_flatten_violations(expected))
    act_v = list(_flatten_violations(actual))
    exp_only = set(exp_v) - set(act_v)
    act_only = set(act_v) - set(exp_v)
    lines = ["audit tree did not match expected."]
    if exp_only:
        lines.append("  expected but missing:")
        for p, m in sorted(exp_only):
            lines.append(f"    {p}: {m}")
    if act_only:
        lines.append("  reported but not expected:")
        for p, m in sorted(act_only):
            lines.append(f"    {p}: {m}")
    if not exp_only and not act_only:
        lines.append("  violations match; structural difference (order, keys, children).")
        lines.append(f"  expected: {json.dumps(expected, indent=2)[:1500]}")
        lines.append(f"  actual:   {json.dumps(actual, indent=2)[:1500]}")
    return "\n".join(lines)
