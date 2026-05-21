"""Tests for doc-coherence/scripts/check_docs.py.

Builds a fake repo under tmp_path with a `.git` marker (so the script's
`_find_repo_root` walks to the right place) and seeds each known drift
mode: broken link, missing anchor, stale §N citation, vocabulary drift.
Each test asserts the script exits non-zero and the expected message
appears in stderr.

A clean fixture is checked separately to make sure the script does not
false-positive on a healthy repo.

Run with:
    pytest doc-coherence/tests/test_check_docs.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_docs.py"


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _seed_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_clean_repo_exits_zero(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    (repo / "README.md").write_text(
        "# Root\n\nSee [docs](docs/INDEX.md#section-one).\n", encoding="utf-8"
    )
    (repo / "docs").mkdir()
    (repo / "docs" / "INDEX.md").write_text(
        "# Index\n\n## Section One\n\nbody.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert "check_docs: OK" in result.stdout


def test_broken_link_is_caught(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    (repo / "README.md").write_text(
        "# Root\n\nSee [docs](docs/MISSING.md).\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "broken link" in result.stderr
    assert "docs/MISSING.md" in result.stderr


def test_missing_anchor_is_caught(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    (repo / "README.md").write_text(
        "# Root\n\nSee [docs](docs/INDEX.md#does-not-exist).\n", encoding="utf-8"
    )
    (repo / "docs").mkdir()
    (repo / "docs" / "INDEX.md").write_text(
        "# Index\n\n## Section One\n\nbody.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "missing anchor" in result.stderr
    assert "does-not-exist" in result.stderr


def test_stale_section_citation_is_caught(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    # Literals built from parts so this very test file does not itself trip
    # check_docs when run against the racecar repo: the section-citation
    # regex requires a real `§` (U+00A7) char in the source text.
    sect = "§"
    (repo / "RULES.md").write_text(
        "# Rules\n\n## 1. First\n\nbody.\n## 2. Second\n\nbody.\n",
        encoding="utf-8",
    )
    (repo / "Makefile").write_text(
        f"# Enforce per RULES.md {sect}3.\nall:\n\techo hi\n",
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "RULES.md" in result.stderr
    assert ("3" in result.stderr) and ("stale" in result.stderr or sect in result.stderr)


def test_vocabulary_drift_is_caught(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    (repo / "A.md").write_text(
        "# A\n\nSeverity values are literal: **Blocker / Major / Minor / Nit**.\n",
        encoding="utf-8",
    )
    (repo / "B.md").write_text(
        "# B\n\nSeverity values are literal: **Blocker / Major / Minor**.\n",
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "vocabulary drift" in result.stderr
    assert "Severity" in result.stderr


def test_vocabulary_singleton_does_not_error(tmp_path: Path) -> None:
    """A class declared in only one README is fine — the rule is identity, not existence."""
    repo = _seed_repo(tmp_path)
    (repo / "ONLY.md").write_text(
        "# Only\n\nSeverity values are literal: **Blocker / Major / Minor / Nit**.\n",
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 0, result.stderr


def test_vocabulary_in_fenced_code_is_ignored(tmp_path: Path) -> None:
    """Fenced code blocks are literals; drift inside them must not trigger the check."""
    repo = _seed_repo(tmp_path)
    (repo / "A.md").write_text(
        "# A\n\nSeverity values are literal: **Blocker / Major / Minor / Nit**.\n",
        encoding="utf-8",
    )
    (repo / "B.md").write_text(
        "# B\n\n```\nSeverity values are literal: **Different**.\n```\n",
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 0, result.stderr
