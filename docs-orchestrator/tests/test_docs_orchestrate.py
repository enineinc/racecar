"""Tests for docs-orchestrator/scripts/docs_orchestrate.py.

The orchestrator composes the racecar checkers. These tests assert it lists its
pipeline, resolves and runs the composed checkers against a seeded repo, and
returns a consolidated exit code.

Run with:
    pytest docs-orchestrator/tests/test_docs_orchestrate.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docs_orchestrate.py"


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_list_prints_pipeline(tmp_path: Path) -> None:
    """--list prints the four stages and their composed checkers."""
    result = _run(tmp_path, "--list")
    assert result.returncode == 0
    for stage in ("manifest", "content-blind", "coherence", "brief"):
        assert stage in result.stdout
    assert "check_required_docs.py" in result.stdout
    assert "check_content_blind.py" in result.stdout


def test_manifest_gate_fails_on_missing_root_docs(tmp_path: Path) -> None:
    """A bare repo (no README/CLAUDE) fails the manifest gate, so the run fails."""
    (tmp_path / ".git").mkdir()
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "gate(s) failed" in result.stdout
    # It composed check_required_docs, which reported the missing root docs.
    assert "missing: README.md" in result.stdout


def test_content_blind_stage_runs(tmp_path: Path) -> None:
    """The content-blind checker is resolved and run as its own stage."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text(
        "---\npnode: []\n---\n\n# r\n", encoding="utf-8"
    )
    result = _run(tmp_path)
    assert "=== stage: content-blind ===" in result.stdout
    assert "check_content_blind" in result.stdout
