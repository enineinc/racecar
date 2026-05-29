"""Tests for doc-coherence/scripts/check_claude_shape.py.

Run with:
    pytest doc-coherence/tests/test_check_claude_shape.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_claude_shape.py"

FULL = """\
# CLAUDE.md

## Orientation
what this is, first moves.

## Architecture
see docs/ARCHITECTURE.md.

## Conventions
project rules.

## Open work
see TODO.md.
"""


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True, check=False)


def _seed(tmp_path: Path, claude: str | None) -> Path:
    (tmp_path / ".git").mkdir()
    if claude is not None:
        (tmp_path / "CLAUDE.md").write_text(claude, encoding="utf-8")
    return tmp_path


def test_no_claude_is_silent(tmp_path: Path) -> None:
    assert _run(_seed(tmp_path, None)).returncode == 0


def test_full_shape_passes(tmp_path: Path) -> None:
    result = _run(_seed(tmp_path, FULL))
    assert result.returncode == 0, result.stdout


def test_missing_section_fails(tmp_path: Path) -> None:
    without_conventions = FULL.replace("## Conventions\nproject rules.\n\n", "")
    result = _run(_seed(tmp_path, without_conventions))
    assert result.returncode == 1
    assert "Conventions" in result.stdout


def test_longer_heading_still_satisfies(tmp_path: Path) -> None:
    longer = FULL.replace("## Orientation\n", "## Orientation in 60 seconds\n")
    assert _run(_seed(tmp_path, longer)).returncode == 0
