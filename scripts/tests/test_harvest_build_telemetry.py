"""Tests for scripts/harvest_build_telemetry.py — the anonymized fleet harvest.

Covers the two walls (company: no repo identity crosses; person: no writer id in-record),
machine-independent `repo_id`, per-writer file layout, and idempotent re-harvest.

Run with:
    pytest scripts/tests/test_harvest_build_telemetry.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
import harvest_build_telemetry as harvest  # noqa: E402

_RAW = {
    "schema": 2,
    "ts": "2026-07-19T10:00:00Z",
    "git_sha": "deadbeef",
    "git_dirty": False,
    "branch": "secret-feature-branch",
    "racecar_version": "8a4513b",
    "label": "check",
    "command": ["make", "check"],
    "ok": False,
    "exit_code": 1,
    "wall_s": 12.3,
    "total_findings": 3,
    "checkers": {"check_docs": {"ok": True, "findings": 0},
                 "check_required_docs": {"ok": False, "findings": 3}},
}


def _git(tmp: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(tmp), *args], check=True,
                   capture_output=True, text=True)


def _make_target(tmp: Path, records: list[dict]) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    _git(tmp, "init", "-q")
    _git(tmp, "-c", "user.email=a@b.c", "-c", "user.name=x",
         "commit", "-q", "--allow-empty", "-m", "root")
    ledger = tmp / ".telemetry" / "build.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )
    return tmp


def test_anonymize_strips_identity_and_keeps_signal() -> None:
    rec = harvest.anonymize(_RAW, "repo123")
    assert set(rec) == {"schema", "repo_id", "run_id", "racecar_version", "label", "checkers"}
    # Company wall: no identifying field survives.
    for leaked in ("git_sha", "branch", "command", "writer_id", "ts", "wall_s",
                   "git_dirty", "exit_code"):
        assert leaked not in rec
    # Structural signal preserved.
    assert rec["repo_id"] == "repo123"
    assert rec["checkers"] == _RAW["checkers"]
    assert rec["racecar_version"] == "8a4513b"


def test_repo_id_is_machine_independent(tmp_path: Path) -> None:
    """A clone of the same repo (same root commit) yields the same repo_id."""
    origin = _make_target(tmp_path / "origin", [_RAW])
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True,
                   capture_output=True, text=True)
    assert harvest.repo_id(origin) == harvest.repo_id(clone)


def test_harvest_writes_anonymized_per_writer_file(tmp_path: Path) -> None:
    target = _make_target(tmp_path / "t", [_RAW])
    dest = tmp_path / "fleet"
    report = harvest.harvest_target(target, dest, wid="w123", dry_run=False)
    assert report["new"] == 1 and report["dup"] == 0 and report["missing"] is False
    out = dest / report["repo_id"] / "w123.jsonl"
    assert out.is_file()
    rec = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert rec["repo_id"] == report["repo_id"]
    assert "git_sha" not in rec  # anonymized on the way in


def test_reharvest_is_idempotent(tmp_path: Path) -> None:
    target = _make_target(tmp_path / "t", [_RAW, {**_RAW, "ts": "2026-07-19T11:00:00Z"}])
    dest = tmp_path / "fleet"
    first = harvest.harvest_target(target, dest, wid="w", dry_run=False)
    second = harvest.harvest_target(target, dest, wid="w", dry_run=False)
    assert first["new"] == 2
    assert second["new"] == 0 and second["dup"] == 2
    out = dest / first["repo_id"] / "w.jsonl"
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2  # not doubled


def test_missing_ledger_skips(tmp_path: Path) -> None:
    target = tmp_path / "bare"
    target.mkdir()
    _git(target, "init", "-q")
    dest = tmp_path / "fleet"
    report = harvest.harvest_target(target, dest, wid="w", dry_run=False)
    assert report["missing"] is True and report["new"] == 0
    assert not dest.exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = _make_target(tmp_path / "t", [_RAW])
    dest = tmp_path / "fleet"
    report = harvest.harvest_target(target, dest, wid="w", dry_run=True)
    assert report["new"] == 1
    assert not dest.exists()


def test_writer_id_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "cfg" / "writer-id"
    monkeypatch.setattr(harvest, "_WRITER_ID_PATH", path)
    first = harvest.writer_id()
    assert path.is_file()
    assert harvest.writer_id() == first  # stable across calls
    assert len(first) == 12
