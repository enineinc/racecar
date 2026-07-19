"""Tests for sysadmin-hardware/lib/_telemetry.py — the CLI telemetry probe.

Covers the schema-2 additions — the mark() work-scale hook and the run-time
`provenance` block — plus the standing guarantees the probe must never break:
off by default, no control-flow change, safe when unwrapped.

Run with:
    pytest sysadmin-hardware/tests/test_telemetry.py
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

# pylint: disable=wrong-import-position,import-error
import _telemetry as tel  # noqa: E402


@pytest.fixture
def telem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Telemetry enabled, logging into an isolated tmp dir."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "1")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    return tmp_path


def _last_record(root: Path) -> dict:
    lines = (root / "usage.jsonl").read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1])


def test_mark_accumulates_into_work(telem: Path) -> None:
    """mark() numeric counters accumulate across calls into the record's `work`."""
    with tel.record(argv=["build"]):
        tel.mark(rows=1000, bytes=2048)
        tel.mark(rows=500)
    rec = _last_record(telem)
    assert rec["schema"] == 2
    assert rec["work"] == {"rows": 1500, "bytes": 2048}


def test_provenance_populated_in_a_git_tree(telem: Path) -> None:
    """The run-time provenance block carries git SHA/dirty, python, host, env hash."""
    with tel.record(argv=["x"]):
        pass
    prov = _last_record(telem)["provenance"]
    assert set(prov) == {
        "git_sha",
        "git_dirty",
        "python",
        "host",
        "venv",
        "env_fingerprint",
    }
    # The suite runs inside the racecar checkout — a git tree — so SHA resolves.
    assert prov["git_sha"]
    assert isinstance(prov["git_dirty"], bool)
    assert prov["python"] == platform.python_version()
    assert prov["env_fingerprint"]


def test_active_registry_cleared_after_the_block(telem: Path) -> None:
    """The in-flight probe is exposed during the block and cleared after."""
    with tel.record(argv=["x"]):
        assert tel._ACTIVE is not None
    assert tel._ACTIVE is None


def test_mark_is_a_noop_with_no_active_run(telem: Path) -> None:
    """Outside a record() block, mark() must not raise and must record nothing."""
    tel.mark(rows=1)
    assert not (telem / "usage.jsonl").exists()


def test_disabled_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the switch off, record()+mark() are a no-op — no log accretes."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "0")  # explicit opt-out (on by default)
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    with tel.record(argv=["x"]):
        tel.mark(rows=5)
    assert not (tmp_path / "usage.jsonl").exists()


def test_exit_code_propagates_through_record(telem: Path) -> None:
    """record() never swallows control flow: a SystemExit re-raises, code recorded."""
    with pytest.raises(SystemExit) as excinfo:
        with tel.record(argv=["x"]):
            raise SystemExit(3)
    assert excinfo.value.code == 3
    assert _last_record(telem)["exit_status"] == 3


def test_argv_secrets_are_redacted(telem: Path) -> None:
    """Secret-shaped argv tokens are masked before the record is written."""
    argv = [
        "deploy",
        "--token",
        "ghp_abcdefghij0123456789ABCDEFghijklmnop",
        "--password=hunter2secret",
        "s3://user:supersecret@bucket/key",
        "eyJhbGciOi.eyJzdWIiOi.SflKxwRJSM",
        "/safe/path/to/file.txt",
    ]
    with tel.record(argv=argv):
        pass
    rec = _last_record(telem)
    joined = " ".join(rec["argv"])
    assert "ghp_abcdefghij" not in joined
    assert "hunter2secret" not in joined
    assert "supersecret" not in joined
    assert "SflKxwRJSM" not in joined  # JWT masked
    assert "<redacted>" in joined
    assert "/safe/path/to/file.txt" in rec["argv"]  # ordinary arg untouched
    # The verb still groups correctly; no secret leaked into subcommand/command.
    assert rec["subcommand"] == "deploy"
    assert "ghp_" not in rec["command"]


def test_switch_is_on_by_default() -> None:
    """With no env override and no pyproject key for it, a telemetry switch defaults on."""
    assert tel._switch("RACECAR_NONEXISTENT_TELEMETRY_XYZ", "nonexistent_key_xyz") is True
