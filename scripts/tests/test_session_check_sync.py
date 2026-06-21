"""Tests for hooks/session_check_sync.py — the synced-script staleness detector.

It byte-compares an adopter repo's synced check scripts against racecar canon and
reports any that drifted. These tests build a real adopter (via sync_scripts) under
tmp_path and assert in-sync -> silent, drifted -> flagged, non-adopter -> ignored.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC = REPO_ROOT / "scripts" / "sync_scripts.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        "session_check_sync", REPO_ROOT / "hooks" / "session_check_sync.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed_adopter(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    subprocess.run(
        [sys.executable, str(SYNC), "--dest", str(tmp_path)],
        capture_output=True, text=True, check=True,
    )
    return tmp_path


def test_in_sync_repo_is_silent(tmp_path: Path) -> None:
    h = _load_hook()
    repo = _seed_adopter(tmp_path)
    assert h.is_adopter(repo)
    stale, missing, _ = h.sync_status(repo)
    assert stale == [] and missing == []


def test_stale_script_is_flagged(tmp_path: Path) -> None:
    h = _load_hook()
    repo = _seed_adopter(tmp_path)
    target = repo / "scripts" / "check_packaging.py"
    target.write_text(target.read_text() + "\n# local drift\n", encoding="utf-8")
    stale, missing, _ = h.sync_status(repo)
    assert "check_packaging.py" in stale
    assert missing == []


def test_missing_script_is_flagged(tmp_path: Path) -> None:
    h = _load_hook()
    repo = _seed_adopter(tmp_path)
    (repo / "scripts" / "check_docs.py").unlink()
    stale, missing, _ = h.sync_status(repo)
    assert "check_docs.py" in missing


def test_stamp_records_ref(tmp_path: Path) -> None:
    h = _load_hook()
    repo = _seed_adopter(tmp_path)
    _, _, stamp_ref = h.sync_status(repo)
    assert stamp_ref == h.canon_ref()


def test_non_adopter_is_ignored(tmp_path: Path) -> None:
    h = _load_hook()
    (tmp_path / ".git").mkdir()
    assert not h.is_adopter(tmp_path)


# --- main() status output: noop / upgrade / na, source-filtered ----------------


def _run_hook(repo: Path, source: str = "startup") -> str:
    import json
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "hooks" / "session_check_sync.py")],
        cwd=str(repo), input=json.dumps({"source": source}),
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_noop_status_when_in_sync(tmp_path: Path) -> None:
    out = _run_hook(_seed_adopter(tmp_path))
    assert "noop |" in out and "in sync with racecar:" in out


def test_upgrade_status_when_stale(tmp_path: Path) -> None:
    repo = _seed_adopter(tmp_path)
    t = repo / "scripts" / "check_packaging.py"
    t.write_text(t.read_text() + "\n# drift\n", encoding="utf-8")
    out = _run_hook(repo)
    assert "upgrade |" in out and "out-of-sync" in out and "check_packaging.py" in out


def test_silent_on_compact(tmp_path: Path) -> None:
    # mid-session context events do not re-emit the status
    assert _run_hook(_seed_adopter(tmp_path), source="compact") == ""


def test_na_non_adopter_is_silent(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    assert _run_hook(tmp_path) == ""
