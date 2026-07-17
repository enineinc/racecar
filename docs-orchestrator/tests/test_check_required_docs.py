"""Tests for docs-orchestrator/scripts/check_required_docs.py.

Builds a fake repo under tmp_path with a `.git` marker and varying doc sets,
asserting the script's exit code and the expected message on stdout.

Run with:
    pytest docs-orchestrator/tests/test_check_required_docs.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_required_docs.py"


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _full_repo(tmp_path: Path) -> Path:
    """A repo satisfying every repo-root requirement. Basename drives the brief name."""
    repo = tmp_path / "widgets"
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "README.md").write_text(
        "---\npnode: []\n---\n\n# widgets\n", encoding="utf-8"
    )
    (repo / "CLAUDE.md").write_text(
        "# widgets\n\n## Orientation\n\nhi.\n", encoding="utf-8"
    )
    brief = repo / "docs" / "summary" / "WIDGETS.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# brief\n", encoding="utf-8")
    return repo


def test_full_repo_passes(tmp_path: Path) -> None:
    """All three repo-root docs present with frontmatter -> OK, exit 0."""
    repo = _full_repo(tmp_path)
    result = _run(repo)
    assert result.returncode == 0, result.stdout
    assert "check_required_docs: OK" in result.stdout


def test_missing_readme(tmp_path: Path) -> None:
    """A missing README is an error."""
    repo = _full_repo(tmp_path)
    (repo / "README.md").unlink()
    result = _run(repo)
    assert result.returncode == 1
    assert "missing: README.md" in result.stdout


def test_readme_without_frontmatter(tmp_path: Path) -> None:
    """A README with no frontmatter block fails on the pnode edge."""
    repo = _full_repo(tmp_path)
    (repo / "README.md").write_text("# widgets\n\nno frontmatter.\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1
    assert "no YAML frontmatter" in result.stdout


def test_readme_frontmatter_missing_pnode(tmp_path: Path) -> None:
    """Frontmatter present but no pnode key is an error."""
    repo = _full_repo(tmp_path)
    (repo / "README.md").write_text("---\nsummary: x\n---\n\n# w\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1
    assert "missing the `pnode` key" in result.stdout


def test_content_blind_absent_is_info_not_error(tmp_path: Path) -> None:
    """A README without a content_blind policy is advisory, not a failure."""
    repo = _full_repo(tmp_path)
    result = _run(repo)
    assert result.returncode == 0
    assert "declares no `content_blind` policy" in result.stdout


def test_missing_brief(tmp_path: Path) -> None:
    """A missing llm-summary brief is an error by default."""
    repo = _full_repo(tmp_path)
    (repo / "docs" / "summary" / "WIDGETS.md").unlink()
    result = _run(repo)
    assert result.returncode == 1
    assert "docs/summary/WIDGETS.md" in result.stdout


def test_brief_opt_out(tmp_path: Path) -> None:
    """A repo can opt out of the brief via pyproject config."""
    repo = _full_repo(tmp_path)
    (repo / "docs" / "summary" / "WIDGETS.md").unlink()
    (repo / "pyproject.toml").write_text(
        "[tool.racecar.required-docs]\nbrief = false\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0
    assert "brief opted out" in result.stdout


def test_claude_without_h2(tmp_path: Path) -> None:
    """A CLAUDE.md with no H2 heading is an error."""
    repo = _full_repo(tmp_path)
    (repo / "CLAUDE.md").write_text("# widgets\n\nno h2.\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1
    assert "no H2 heading: CLAUDE.md" in result.stdout
