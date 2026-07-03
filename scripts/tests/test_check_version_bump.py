"""check_version_bump: a bumpable commit type must bump the version home."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import check_version_bump  # noqa: E402


# ---------------------------------------------------------------------------
# type parsing and the type -> bump mapping (pure)
# ---------------------------------------------------------------------------


def test_parse_type_plain():
    assert check_version_bump.parse_type("feat: add thing") == ("feat", False)


def test_parse_type_with_scope():
    assert check_version_bump.parse_type("fix(api): patch it") == ("fix", False)


def test_parse_type_bang_is_breaking():
    assert check_version_bump.parse_type("feat!: drop flag") == ("feat", True)


def test_parse_type_breaking_footer():
    msg = "chore: cleanup\n\nBREAKING CHANGE: removed the old path"
    assert check_version_bump.parse_type(msg) == ("chore", True)


def test_parse_type_non_conventional_is_none():
    assert check_version_bump.parse_type("Merge branch 'x'") == (None, False)


def test_bump_for_mapping():
    assert check_version_bump.bump_for("feat", False) == "minor"
    assert check_version_bump.bump_for("fix", False) == "patch"
    assert check_version_bump.bump_for("perf", False) == "patch"
    assert check_version_bump.bump_for("docs", False) == "none"
    assert check_version_bump.bump_for("chore", False) == "none"
    assert check_version_bump.bump_for(None, True) == "major"
    assert check_version_bump.bump_for("chore", True) == "major"


# ---------------------------------------------------------------------------
# version-home resolution (pure)
# ---------------------------------------------------------------------------


def test_version_home_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    assert check_version_bump.version_home(tmp_path) == ("pyproject.toml", "1.2.3")


def test_version_home_version_file_when_no_project_table(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.black]\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("0.4.0\n", encoding="utf-8")
    assert check_version_bump.version_home(tmp_path) == ("VERSION", "0.4.0")


def test_version_home_none_when_neither(tmp_path):
    assert check_version_bump.version_home(tmp_path) is None


# ---------------------------------------------------------------------------
# the full gate against a real git repo
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo_with_version(tmp_path: Path, version: str) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    _git(tmp_path, "add", "VERSION")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def _run(repo: Path, message: str) -> int:
    msg = repo / "COMMIT_EDITMSG"
    msg.write_text(message + "\n", encoding="utf-8")
    return check_version_bump.main([str(msg), "--root", str(repo)])


def test_feat_without_bump_fails(tmp_path):
    repo = _repo_with_version(tmp_path, "0.1.0")
    assert _run(repo, "feat: add thing") == 1


def test_docs_without_bump_passes(tmp_path):
    repo = _repo_with_version(tmp_path, "0.1.0")
    assert _run(repo, "docs: tweak wording") == 0


def test_feat_with_staged_bump_passes(tmp_path):
    repo = _repo_with_version(tmp_path, "0.1.0")
    (repo / "VERSION").write_text("0.2.0\n", encoding="utf-8")
    _git(repo, "add", "VERSION")
    assert _run(repo, "feat: add thing") == 0


def test_breaking_without_bump_fails(tmp_path):
    repo = _repo_with_version(tmp_path, "0.1.0")
    assert _run(repo, "refactor!: drop a flag") == 1


def test_no_version_home_is_config_error(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "README")
    _git(tmp_path, "commit", "-m", "init")
    assert _run(tmp_path, "feat: add thing") == 2
