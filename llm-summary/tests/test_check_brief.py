"""Tests for llm-summary/scripts/check_brief.py.

Two flavors:

1. Smoke test against the repo's own brief at ``docs/summary/RACECAR.md`` —
   the brief that exists in this checkout must validate clean. Catches
   regressions where a schema tweak in the script outpaces the brief.

2. Targeted fixtures under tmp_path — a minimal valid brief that passes,
   then mutated copies that flip one frontmatter field each to assert
   the relevant validator fires.

The script discovers the brief either by argv[1] or by walking up to find
``.git`` then resolving ``docs/summary/$REPO.md``. Tests pass the path
explicitly to avoid relying on CWD.

Run with:
    pytest llm-summary/tests/test_check_brief.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_brief.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_BRIEF = REPO_ROOT / "docs" / "summary" / "RACECAR.md"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(not REAL_BRIEF.is_file(), reason="repo brief not present")
def test_real_brief_validates_clean() -> None:
    """The checked-in brief must validate against the current schema."""
    result = _run(str(REAL_BRIEF))
    assert result.returncode == 0, (
        f"docs/summary/RACECAR.md failed check_brief:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


_MINIMAL_FRONTMATTER = """\
---
generator:
  name: racecar-llm-summary
  version: "0.2.0"
target:
  repo: testrepo
  sha: abc1234
  date: 2026-01-01
bundle:
  - TESTREPO.md

entities:
  - name: Thing
    case: none
    purpose: A placeholder entity for tests.
---
"""


def _write_brief(
    tmp_path: Path,
    frontmatter: str = _MINIMAL_FRONTMATTER,
    preamble: str = "",
) -> Path:
    bundle = tmp_path / "docs" / "testrepo"
    bundle.mkdir(parents=True)
    brief = bundle / "TESTREPO.md"
    body = (
        "# Brief\n\n"
        + (f"{preamble}\n\n" if preamble else "")
        + "## §1. Purpose\n\nbody.\n\n"
        "## §2. Architecture\n\nbody.\n\n"
        "## §3. Live access\n\nbody.\n\n"
        "## Confidence\n\n"
        "**Least confident**\n\n- one\n- two\n- three\n\n"
        "**Not in this brief**\n\n- nothing\n"
    )
    brief.write_text(frontmatter + body, encoding="utf-8")
    return brief


def test_missing_frontmatter_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "docs" / "testrepo"
    bundle.mkdir(parents=True)
    brief = bundle / "TESTREPO.md"
    brief.write_text("# No frontmatter here\n", encoding="utf-8")
    result = _run(str(brief))
    assert result.returncode == 1
    assert "frontmatter" in (result.stdout + result.stderr).lower()


def test_wrong_generator_name_is_caught(tmp_path: Path) -> None:
    frontmatter = _MINIMAL_FRONTMATTER.replace(
        "name: racecar-llm-summary", "name: something-else"
    )
    brief = _write_brief(tmp_path, frontmatter)
    result = _run(str(brief))
    assert result.returncode == 1
    assert "generator.name" in (result.stdout + result.stderr)


def test_invalid_semver_is_caught(tmp_path: Path) -> None:
    frontmatter = _MINIMAL_FRONTMATTER.replace('version: "0.2.0"', 'version: "v0.2"')
    brief = _write_brief(tmp_path, frontmatter)
    result = _run(str(brief))
    assert result.returncode == 1
    assert "version" in (result.stdout + result.stderr).lower()


def test_preamble_sha_mismatch_is_caught(tmp_path: Path) -> None:
    """A snapshot SHA in the preamble that disagrees with target.sha fails."""
    # _MINIMAL_FRONTMATTER pins target.sha: abc1234.
    brief = _write_brief(tmp_path, preamble="A snapshot of testrepo at `deadbee`.")
    result = _run(str(brief))
    assert result.returncode == 1
    out = result.stdout + result.stderr
    assert "snapshot SHA" in out
    assert "deadbee" in out


def test_preamble_matching_sha_not_flagged(tmp_path: Path) -> None:
    """A preamble SHA equal to target.sha raises no spine/body finding."""
    brief = _write_brief(tmp_path, preamble="A snapshot of testrepo at `abc1234`.")
    result = _run(str(brief))
    assert "snapshot SHA" not in (result.stdout + result.stderr)
