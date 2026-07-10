"""Tests for doc-coherence/scripts/check_doc_graph.py.

Builds a fake repo under tmp_path with a `.git` marker (so the script's
`find_root` resolves there) and seeds each graph rule's failure mode:
missing pnode, a nonexistent pnode target, a pnode cycle, and an
`Accessed via` link that disagrees with pnode. A clean DAG fixture confirms
the checker does not false-positive.

Run with:
    pytest doc-coherence/tests/test_check_doc_graph.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_doc_graph.py"


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _doc(path: Path, pnode: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\npnode: {pnode}\n---\n\n# Doc\n\n{body}\n", encoding="utf-8")


def _clean_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    _doc(tmp_path / "README.md", "[]")
    _doc(tmp_path / "shared" / "CHILD.md", "[../README.md]")
    return tmp_path


def test_clean_dag_passes(tmp_path: Path) -> None:
    result = _run(_clean_repo(tmp_path))
    assert result.returncode == 0, result.stdout
    assert "OK" in result.stdout


def test_missing_pnode(tmp_path: Path) -> None:
    repo = _clean_repo(tmp_path)
    (repo / "LOOSE.md").write_text("# No frontmatter\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1
    assert "missing" in result.stdout


def test_nonexistent_target(tmp_path: Path) -> None:
    repo = _clean_repo(tmp_path)
    _doc(repo / "shared" / "BAD.md", "[../NOPE.md]")
    result = _run(repo)
    assert result.returncode == 1
    assert "does not exist" in result.stdout


def test_cycle(tmp_path: Path) -> None:
    repo = _clean_repo(tmp_path)
    _doc(repo / "A.md", "[B.md]")
    _doc(repo / "B.md", "[A.md]")
    result = _run(repo)
    assert result.returncode == 1
    assert "cycle" in result.stdout


def test_accessed_via_mismatch(tmp_path: Path) -> None:
    repo = _clean_repo(tmp_path)
    _doc(
        repo / "shared" / "VIA.md",
        "[../README.md]",
        body="Accessed via [`A.md`](../A.md).",
    )
    _doc(repo / "A.md", "[README.md]")
    result = _run(repo)
    assert result.returncode == 1
    assert "Accessed via" in result.stdout


def test_hidden_dirs_are_out_of_scope(tmp_path: Path) -> None:
    """Markdown inside a dot-prefixed tree (.pytest_cache, .mypy_cache, .venv) is a
    generated/vendored artifact, not a project doc: it must not be pulled into the
    graph and must not fire a 'missing pnode' finding. Matches check_docs /
    check_file_placement, which both skip hidden paths."""
    repo = _clean_repo(tmp_path)
    cache_readme = repo / ".pytest_cache" / "README.md"
    cache_readme.parent.mkdir(parents=True)
    cache_readme.write_text("# pytest cache\n\nGenerated. No frontmatter.\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stdout
    assert ".pytest_cache" not in result.stdout
