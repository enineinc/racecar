"""check_racecar_overrides: a repo must not fork racecar (no [tool.racecar], canon racecar.mk)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import check_racecar_overrides  # noqa: E402

CANONICAL = check_racecar_overrides.CANONICAL_RACECAR_MK


# ---------------------------------------------------------------------------
# the [tool.racecar] table assertion (pure)
# ---------------------------------------------------------------------------


def test_no_pyproject_is_not_an_override(tmp_path):
    assert check_racecar_overrides.overrides_table(tmp_path) is False


def test_overrides_table_is_detected(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.racecar.overrides]\nline-length = 100\n", encoding="utf-8"
    )
    assert check_racecar_overrides.overrides_table(tmp_path) is True


def test_bare_tool_racecar_table_is_detected(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.racecar]\nx = "y"\n', encoding="utf-8"
    )
    assert check_racecar_overrides.overrides_table(tmp_path) is True


def test_unrelated_tool_table_is_clean(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.black]\n", encoding="utf-8")
    assert check_racecar_overrides.overrides_table(tmp_path) is False


# ---------------------------------------------------------------------------
# the racecar.mk byte-identity assertion (pure)
# ---------------------------------------------------------------------------


def test_absent_racecar_mk_is_a_noop(tmp_path):
    assert check_racecar_overrides.racecar_mk_drift(tmp_path) == []


def test_canonical_racecar_mk_has_no_drift(tmp_path):
    (tmp_path / "racecar.mk").write_text(
        CANONICAL.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert check_racecar_overrides.racecar_mk_drift(tmp_path) == []


def test_hand_edited_racecar_mk_drifts(tmp_path):
    (tmp_path / "racecar.mk").write_text(
        CANONICAL.read_text(encoding="utf-8") + "\nHAND_EDIT := oops\n",
        encoding="utf-8",
    )
    assert check_racecar_overrides.racecar_mk_drift(tmp_path)


# ---------------------------------------------------------------------------
# the full gate
# ---------------------------------------------------------------------------


def test_clean_repo_passes(tmp_path):
    assert check_racecar_overrides.main(["--root", str(tmp_path)]) == 0


def test_override_table_fails(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.racecar.overrides]\nx = 1\n", encoding="utf-8"
    )
    assert check_racecar_overrides.main(["--root", str(tmp_path)]) == 1


def test_edited_racecar_mk_fails(tmp_path):
    (tmp_path / "racecar.mk").write_text(
        CANONICAL.read_text(encoding="utf-8") + "\nHAND_EDIT := oops\n",
        encoding="utf-8",
    )
    assert check_racecar_overrides.main(["--root", str(tmp_path)]) == 1


def test_racecar_own_repo_is_a_noop():
    # racecar vendors neither a root racecar.mk nor a [tool.racecar] table.
    assert check_racecar_overrides.main(["--root", str(REPO_ROOT)]) == 0
