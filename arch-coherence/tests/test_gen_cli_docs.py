"""Tests for scripts/gen_cli_docs.py — the CLI-tree doc projector.

Each test builds a minimal `toolkit/{greet,farewell}` package tree in a tmp repo
(a pattern-1 discovery root over two pattern-3 leaves), copies the delivered pair
of scripts — `gen_cli_docs.py` beside the `check_cli_commands.py` it imports —
into the repo's `scripts/`, and drives the generator via subprocess exactly as an
adopter would (`python scripts/gen_cli_docs.py …` from the repo root).

The generator is a projection: it invents no structure of its own, so the tests
assert the delivered behaviour (pages appear where the module tree says, each is a
doc-graph citizen, `--check` is a faithful staleness gate, a moved command's stale
page is caught) rather than exact prose.

Run with:
    pytest arch-coherence/tests/test_gen_cli_docs.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
GEN = SCRIPTS / "gen_cli_docs.py"
AUDIT = SCRIPTS / "check_cli_commands.py"

_ROOT_MAIN = '''\
"""toolkit — a demo CLI that composes its subcommands.

This lead paragraph becomes the root page description.
"""
import sys


def commands():
    return [("greet", "Greet someone by name"), ("farewell", "Say a farewell")]


def _print_commands():
    print("python -m toolkit\\n")
    for name, desc in commands():
        print(f"  python -m toolkit.{name}   {desc}")
    print("\\nAppend --help to any command for its options.")


if __name__ == "__main__":
    _print_commands()
    sys.exit(0)
'''

_LEAF_MAIN = '''\
"""toolkit.{name} — {desc}."""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m toolkit.{name}", description="{desc}."
    )
    p.add_argument("--loud", action="store_true", help="say it loudly")
    p.parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def _build_repo(root: Path) -> None:
    """Write a bootable `src/toolkit` package tree and copy in the delivered scripts."""
    pkg = root / "src" / "toolkit"
    for name, desc in [
        ("greet", "Greet someone by name"),
        ("farewell", "Say a farewell"),
    ]:
        leaf = pkg / name
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "__init__.py").write_text("")
        (leaf / "__main__.py").write_text(_LEAF_MAIN.format(name=name, desc=desc))
    (pkg / "__init__.py").write_text('"""toolkit demo library."""\n')
    (pkg / "__main__.py").write_text(_ROOT_MAIN)

    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "check_cli_commands.py").write_text(AUDIT.read_text(encoding="utf-8"))
    (scripts / "gen_cli_docs.py").write_text(GEN.read_text(encoding="utf-8"))

    (root / "README.md").write_text("# toolkit\n\nA demo repo.\n")


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/gen_cli_docs.py", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )


def test_write_projects_the_tree(tmp_path: Path) -> None:
    """--write emits one page per node, mirroring the module path, plus the README block."""
    _build_repo(tmp_path)
    proc = _run(tmp_path, "--write")
    assert proc.returncode == 0, proc.stderr

    root_page = tmp_path / "docs" / "cli" / "README.md"
    greet_page = tmp_path / "docs" / "cli" / "greet" / "README.md"
    farewell_page = tmp_path / "docs" / "cli" / "farewell" / "README.md"
    assert root_page.is_file() and greet_page.is_file() and farewell_page.is_file()

    root_text = root_page.read_text(encoding="utf-8")
    # The page is keyed by the invocation and carries the audit's role label.
    assert "command: python -m toolkit" in root_text
    # Root package name is discovered, not hard-coded.
    assert "`python -m toolkit…` CLI tree" in root_text
    # Discovery node → a linked subcommand table, not a --help block.
    assert "## Subcommands" in root_text
    assert "[`python -m toolkit.greet`](greet/README.md)" in root_text

    greet_text = greet_page.read_text(encoding="utf-8")
    # Leaf node → its captured argparse usage.
    assert "## Usage" in greet_text
    assert "--loud" in greet_text


def test_pages_are_doc_graph_citizens(tmp_path: Path) -> None:
    """Every page names its parent once; the root falls back to the storefront."""
    _build_repo(tmp_path)
    assert _run(tmp_path, "--write").returncode == 0

    root_text = (tmp_path / "docs" / "cli" / "README.md").read_text(encoding="utf-8")
    child_text = (tmp_path / "docs" / "cli" / "greet" / "README.md").read_text(
        encoding="utf-8"
    )
    # No docs/ARCHITECTURE.md or docs/README.md here → the repo storefront.
    assert "pnode: [../../README.md]" in root_text
    assert "pnode: [../README.md]" in child_text


def test_readme_cli_block_added(tmp_path: Path) -> None:
    """--write refreshes the marker-delimited ## CLI block in the repo README."""
    _build_repo(tmp_path)
    assert _run(tmp_path, "--write").returncode == 0
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "<!-- BEGIN cli-tree (generated) -->" in readme
    assert "## CLI" in readme
    assert "<!-- END cli-tree -->" in readme
    # The hand-authored prose above the block is preserved.
    assert "A demo repo." in readme


def test_check_is_clean_and_idempotent(tmp_path: Path) -> None:
    """After --write, --check passes and a second --write is a no-op."""
    _build_repo(tmp_path)
    assert _run(tmp_path, "--write").returncode == 0
    assert _run(tmp_path, "--check").returncode == 0
    again = _run(tmp_path, "--write")
    assert again.returncode == 0
    assert "already current" in again.stdout


def test_check_catches_a_moved_command(tmp_path: Path) -> None:
    """A command whose surface changed but whose page did not is caught by --check."""
    _build_repo(tmp_path)
    assert _run(tmp_path, "--write").returncode == 0
    # Change the leaf's argparse surface without regenerating its page.
    leaf_main = tmp_path / "src" / "toolkit" / "greet" / "__main__.py"
    leaf_main.write_text(
        leaf_main.read_text(encoding="utf-8").replace("--loud", "--shout")
    )
    proc = _run(tmp_path, "--check")
    assert proc.returncode == 1
    assert "STALE" in proc.stderr


def test_orphan_page_is_removed(tmp_path: Path) -> None:
    """A page the tree no longer projects is deleted on --write."""
    _build_repo(tmp_path)
    assert _run(tmp_path, "--write").returncode == 0
    stray = tmp_path / "docs" / "cli" / "ghost" / "README.md"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("# stale page for a command that no longer exists\n")
    assert _run(tmp_path, "--check").returncode == 1
    assert _run(tmp_path, "--write").returncode == 0
    assert not stray.exists()
