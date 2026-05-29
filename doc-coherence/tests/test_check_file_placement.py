"""Tests for doc-coherence/scripts/check_file_placement.py.

Run with:
    pytest doc-coherence/tests/test_check_file_placement.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_file_placement.py"


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True, check=False)


def _seed(tmp_path: Path, *rel_files: str) -> Path:
    (tmp_path / ".git").mkdir()
    for rel in rel_files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x\n", encoding="utf-8")
    return tmp_path


def test_clean_repo_passes(tmp_path: Path) -> None:
    repo = _seed(
        tmp_path,
        "README.md", "CLAUDE.md", "PLAN.md", "TODO.md", "CHANGELOG.md",
        "docs/DESIGN.md",
        "src/pkg/README.md", "src/pkg/CLAUDE.md", "src/pkg/docs/SYSTEM.md",
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_stray_root_doc_fails(tmp_path: Path) -> None:
    repo = _seed(tmp_path, "README.md", "ARCHITECTURE.md")
    result = _run(repo)
    assert result.returncode == 1
    assert "ARCHITECTURE.md" in result.stdout


def test_stray_subdir_doc_fails(tmp_path: Path) -> None:
    repo = _seed(tmp_path, "src/pkg/README.md", "src/pkg/NOTES.md")
    result = _run(repo)
    assert result.returncode == 1
    assert "src/pkg/NOTES.md" in result.stdout


def test_claude_without_readme_fails(tmp_path: Path) -> None:
    repo = _seed(tmp_path, "src/pkg/CLAUDE.md")
    result = _run(repo)
    assert result.returncode == 1
    assert "without a sibling README.md" in result.stdout


def test_docs_dir_allows_any_markdown(tmp_path: Path) -> None:
    repo = _seed(tmp_path, "README.md", "docs/ANYTHING.md", "docs/sub/MORE.md")
    assert _run(repo).returncode == 0
