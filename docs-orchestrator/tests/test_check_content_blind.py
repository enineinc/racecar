"""Tests for docs-orchestrator/scripts/check_content_blind.py.

Builds a fake git repo under tmp_path (git is used so the script's
`git ls-files` publish query has real output), declares a content-blind policy
in README frontmatter, and asserts the prose figure rule fires or is a no-op.

Run with:
    pytest docs-orchestrator/tests/test_check_content_blind.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_content_blind.py"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    return repo


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _readme(content_blind: bool, extra: str = "") -> str:
    flag = "true" if content_blind else "false"
    return f"---\npnode: []\ncontent_blind: {flag}\n{extra}---\n\n# repo\n"


def test_noop_when_opted_out(tmp_path: Path) -> None:
    """content_blind: false => no-op, exit 0, even with a figure in prose."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(False), encoding="utf-8")
    (repo / "doc.md").write_text(
        "# d\n\nThe fee is 0.0625 of 22,000.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0
    assert "nothing to enforce" in result.stdout


def test_noop_when_absent(tmp_path: Path) -> None:
    """No content_blind key => off by default; a prose figure does not fail."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("---\npnode: []\n---\n\n# repo\n", encoding="utf-8")
    (repo / "doc.md").write_text(
        "# d\n\nThe fee is 0.0625 of the 22,000 notional.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0
    assert "nothing to enforce" in result.stdout


def test_fires_on_prose_figure(tmp_path: Path) -> None:
    """A deal-shaped figure in markdown prose fails when opted in."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    (repo / "doc.md").write_text(
        "# d\n\nThe fee is 0.0625 of the 22,000 notional.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "0.0625" in result.stdout
    assert "22,000" in result.stdout


def test_structural_constants_pass(tmp_path: Path) -> None:
    """Calendar / arithmetic constants are structural and do not fire."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    (repo / "doc.md").write_text(
        "# d\n\nThere are 365 days and 12 months; a year like 2028 is fine.\n",
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_date_keys_pass(tmp_path: Path) -> None:
    """Compact date keys — YYYYMM paper ids and YYYYMMDD — are calendar values, not figures."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    (repo / "doc.md").write_text(
        "# d\n\nPaper 202511 was revised on 20251103; see the 2025-11 cohort.\n",
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_fenced_code_is_not_prose(tmp_path: Path) -> None:
    """A figure inside a fenced code block is a config example, not prose."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    (repo / "doc.md").write_text(
        "# d\n\n```\nstrike: 0.0625\nnotional: 22000\n```\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_exempt_path_is_skipped(tmp_path: Path) -> None:
    """A path in content_blind_exempt is not scanned."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(
        _readme(True, extra="content_blind_exempt:\n  - doc.md\n"), encoding="utf-8"
    )
    (repo / "doc.md").write_text(
        "# d\n\nThe fee is 0.0625 of 22,000.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_py_docstring_figure_fires(tmp_path: Path) -> None:
    """A figure in a python docstring fails; a figure in code does not."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    (repo / "mod.py").write_text(
        '"""The balance runs off to 24,000 by year five."""\n\nRATE = 0.0625\n',
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "24,000" in result.stdout
    # RATE = 0.0625 is code, not prose, so it must not be reported.
    assert "mod.py" in result.stdout
    assert "RATE" not in result.stdout


def test_extra_structural_allowlist(tmp_path: Path) -> None:
    """content_blind_structural extends the built-in structural set."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(
        _readme(True, extra="content_blind_structural:\n  - 22000.0\n"),
        encoding="utf-8",
    )
    (repo / "doc.md").write_text("# d\n\nThe count is 22000 units.\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_guard_does_not_flag_itself(tmp_path: Path) -> None:
    """The guard's own file is self-exempt (it quotes the shapes it forbids)."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    # A verbatim copy of the guard, as it lands in an adopter's scripts/.
    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "check_content_blind.py").write_text(
        SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    # Run the in-repo copy so __file__ matches the scanned path.
    result = subprocess.run(
        [sys.executable, str(scripts / "check_content_blind.py")],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_delivered_files_are_exempt(tmp_path: Path) -> None:
    """A racecar-delivered file (listed in scripts/racecar-manifest.txt) is not scanned,
    but a repo-owned file with the same figure still fires (Q3)."""
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text(_readme(True), encoding="utf-8")
    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "racecar-manifest.txt").write_text(
        "# racecar-delivered files\nscripts/check_x.py\n", encoding="utf-8"
    )
    # A delivered script whose comment quotes a figure-shape must NOT fire...
    (scripts / "check_x.py").write_text(
        '"""Example threshold 22,000 in a delivered tool."""\nX = 1\n', encoding="utf-8"
    )
    # ...while a repo-owned doc carrying the same figure still does.
    (repo / "doc.md").write_text("# d\n\nThe fee is 22,000.\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1, result.stdout
    assert "scripts/check_x.py" not in result.stdout
    assert "doc.md" in result.stdout
