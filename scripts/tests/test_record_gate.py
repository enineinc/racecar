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


def _run(tmp: Path, *, enabled: bool) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["RACECAR_BUILD_TELEMETRY"] = "1" if enabled else "0"  # explicit (on by default)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "check", "--", sys.executable, "-c", _FAKE],
        cwd=tmp,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


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


def test_passthrough_when_disabled(tmp_path: Path) -> None:
    result = _run(tmp_path, enabled=False)
    assert result.returncode == 1  # still runs the command and passes its exit code
    assert "check_docs: OK" in result.stdout  # output streamed through
    assert not (tmp_path / ".telemetry").exists()  # but nothing recorded
