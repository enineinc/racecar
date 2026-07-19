"""Tests for scripts/record_gate.py — the developer-telemetry gate ledger.

Verifies the outcome record (keyed to the run, findings parsed), the off-by-default
passthrough behind its own `RACECAR_BUILD_TELEMETRY` switch, and exit-code transparency.

Run with:
    pytest scripts/tests/test_record_gate.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "record_gate.py"

# A stand-in gate: prints racecar-style checker summaries, then fails.
_FAKE = (
    "print('check_docs: OK'); "
    "print('check_doc_graph: OK (50 docs)'); "
    "print('check_required_docs: 3 errors'); "
    "import sys; sys.exit(1)"
)


def _run(
    tmp: Path, *, enabled: bool | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("RACECAR_BUILD_TELEMETRY", None)
    if enabled is not None:
        env["RACECAR_BUILD_TELEMETRY"] = "1" if enabled else "0"  # explicit (on by default)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "check", "--", sys.executable, "-c", _FAKE],
        cwd=tmp,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _git_init(tmp: Path) -> None:
    for args in (["init", "-q"], ["-c", "user.email=a@b.c", "-c", "user.name=x",
                                  "commit", "-q", "--allow-empty", "-m", "root"]):
        subprocess.run(["git", "-C", str(tmp), *args], check=True,
                       capture_output=True, text=True)


def test_records_outcome_when_enabled(tmp_path: Path) -> None:
    result = _run(tmp_path, enabled=True)
    assert result.returncode == 1  # the gate's exit code passes through
    ledger = (tmp_path / ".telemetry" / "build.jsonl").read_text(encoding="utf-8")
    rec = json.loads(ledger.splitlines()[-1])
    assert rec["label"] == "check"
    assert rec["ok"] is False and rec["exit_code"] == 1
    assert rec["total_findings"] == 3
    assert rec["checkers"]["check_required_docs"] == {"ok": False, "findings": 3}
    assert rec["checkers"]["check_docs"]["ok"] is True
    assert rec["git_sha"] is None  # tmp_path is not a git tree
    assert rec["pushed"] is False  # collected now, sent later (transport deferred)
    assert isinstance(rec["id"], str) and rec["id"]  # stable key the future push flips on


def test_passthrough_when_disabled(tmp_path: Path) -> None:
    result = _run(tmp_path, enabled=False)
    assert result.returncode == 1  # still runs the command and passes its exit code
    assert "check_docs: OK" in result.stdout  # output streamed through
    assert not (tmp_path / ".telemetry").exists()  # but nothing recorded


def test_schema_2_and_racecar_version_stamp(tmp_path: Path) -> None:
    """The record is schema 2 and carries the canon stamp in force (scripts/.racecar-version)."""
    _git_init(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / ".racecar-version").write_text("abc1234\n", encoding="utf-8")
    result = _run(tmp_path, enabled=True)
    rec = json.loads(
        (tmp_path / ".telemetry" / "build.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )
    assert rec["schema"] == 2
    assert rec["racecar_version"] == "abc1234"
    assert rec["git_sha"] is not None  # now a real git tree


def test_ledger_dir_self_ignores(tmp_path: Path) -> None:
    """Writing the ledger drops `.telemetry/.gitignore` (`*`), so it is never committable."""
    _run(tmp_path, enabled=True)
    marker = tmp_path / ".telemetry" / ".gitignore"
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8").strip().endswith("*")


def test_settings_toml_opts_out_without_env(tmp_path: Path) -> None:
    """`.telemetry/settings.toml` (the toggle's home) opts out with no env var set."""
    (tmp_path / ".telemetry").mkdir()
    (tmp_path / ".telemetry" / "settings.toml").write_text(
        "[telemetry]\nbuild = false\n", encoding="utf-8"
    )
    result = _run(tmp_path, enabled=None)  # no RACECAR_BUILD_TELEMETRY in env
    assert result.returncode == 1  # gate still runs
    assert not (tmp_path / ".telemetry" / "build.jsonl").exists()  # settings tier opted out
