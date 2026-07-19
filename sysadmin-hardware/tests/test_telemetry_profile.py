"""Tests for the sysadmin-hardware telemetry mechanism and its profiler.

Two units under test:

1. ``lib/_telemetry.py`` — the runtime probe. Off unless ``RACECAR_USAGE_TELEMETRY``
   is set; when on, appends one JSON record per ``record()`` block with the
   documented fields; records the exit status; never alters control flow.
2. ``scripts/telemetry_profile.py`` — the aggregator. Percentiles, per-command
   grouping, the CLI (table / --json / missing-path exit code).

Run with:
    pytest sysadmin-hardware/tests/test_telemetry_profile.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

LENS = Path(__file__).resolve().parents[1]
PROBE_PATH = LENS / "lib" / "_telemetry.py"
PROFILE_PATH = LENS / "scripts" / "telemetry_profile.py"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


telemetry = _load("_telemetry_under_test", PROBE_PATH)
profiler = _load("telemetry_profile_under_test", PROFILE_PATH)


# --------------------------------------------------------------------------
# Probe
# --------------------------------------------------------------------------


def test_disabled_by_default(monkeypatch, tmp_path):
    """With the switch off, record() writes nothing."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "0")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    with telemetry.record(argv=["run", "--all"]):
        pass
    assert not (tmp_path / "usage.jsonl").exists()


def test_enabled_writes_one_record(monkeypatch, tmp_path):
    """With the switch on, one JSON line lands with the documented fields."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "1")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    with telemetry.record(argv=["run", "--all", "--workers", "8"]):
        pass
    lines = (tmp_path / "usage.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    for field in (
        "schema",
        "ts_start",
        "ts_end",
        "command",
        "argv",
        "wall_s",
        "cpu_user_s",
        "cpu_sys_s",
        "cpu_total_s",
        "peak_rss_mb",
        "exit_status",
        "workers",
        "cpu_count",
        "pid",
    ):
        assert field in rec, field
    assert rec["schema"] == telemetry.SCHEMA_VERSION
    assert rec["subcommand"] == "run"
    assert rec["workers"] == 8
    assert rec["exit_status"] == 0
    assert rec["peak_rss_mb"] > 0


def test_records_systemexit_code_and_reraises(monkeypatch, tmp_path):
    """A SystemExit inside the block is recorded and still propagates."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "1")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    with pytest.raises(SystemExit):
        with telemetry.record(argv=["run"]):
            raise SystemExit(2)
    rec = json.loads(
        (tmp_path / "usage.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert rec["exit_status"] == 2


def test_records_exception_as_status_one(monkeypatch, tmp_path):
    """A non-SystemExit exception is recorded as status 1 and re-raised."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "1")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        with telemetry.record(argv=["run"]):
            raise ValueError("boom")
    rec = json.loads(
        (tmp_path / "usage.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert rec["exit_status"] == 1


def test_probe_failure_never_breaks_the_command(monkeypatch, tmp_path):
    """If the log dir cannot be created, the wrapped block still completes."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "1")
    # Point the dir at a path under a regular file, so mkdir raises; the probe
    # must swallow it rather than propagate into the command.
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(blocker / "sub"))
    ran = []
    with telemetry.record(argv=["run"]):
        ran.append(True)
    assert ran == [True]


def test_run_wrapper_invokes_main(monkeypatch, tmp_path):
    """run(main) executes main(), records once, and exits with main()'s return code."""
    monkeypatch.setenv("RACECAR_USAGE_TELEMETRY", "1")
    monkeypatch.setenv("RACECAR_TELEMETRY_DIR", str(tmp_path))
    called = []
    # run() is sys.exit(main()) with measurement, so it raises SystemExit with the code.
    with pytest.raises(SystemExit) as excinfo:
        telemetry.run(lambda: called.append(True) or 0, argv=["status"])
    assert excinfo.value.code == 0
    assert called == [True]
    assert (tmp_path / "usage.jsonl").exists()


def test_worker_flag_parsing():
    """--workers / --jobs / -j and the =VALUE spelling all parse."""
    assert telemetry._workers(["run", "--workers", "12"]) == 12
    assert telemetry._workers(["run", "--workers=6"]) == 6
    assert telemetry._workers(["build", "-j", "4"]) == 4
    assert telemetry._workers(["run", "--all"]) is None


def test_exit_code_normalization():
    """SystemExit codes normalize: None -> 0, int passthrough, str -> 1."""
    assert telemetry._exit_code(None) == 0
    assert telemetry._exit_code(3) == 3
    assert telemetry._exit_code("fatal") == 1


# --------------------------------------------------------------------------
# Aggregator
# --------------------------------------------------------------------------


def test_percentile_interpolation():
    """Linear-interpolated percentiles on a known series."""
    values = [1.0, 2.0, 3.0, 4.0]
    assert profiler.percentile(values, 50) == 2.5
    assert profiler.percentile([5.0], 95) == 5.0
    assert profiler.percentile([], 50) == 0.0


def test_profile_groups_by_command():
    """Records fold into one row per command with count and percentiles."""
    records = [
        {
            "command": "python -m gfem.radiant run",
            "wall_s": 10,
            "peak_rss_mb": 2000,
            "cpu_total_s": 40,
            "workers": 8,
            "cpu_count": 4,
            "exit_status": 0,
        },
        {
            "command": "python -m gfem.radiant run",
            "wall_s": 20,
            "peak_rss_mb": 4000,
            "cpu_total_s": 80,
            "workers": 8,
            "cpu_count": 4,
            "exit_status": 2,
        },
        {
            "command": "python -m gfem.data sync",
            "wall_s": 5,
            "peak_rss_mb": 200,
            "cpu_total_s": 2,
            "workers": None,
            "cpu_count": 4,
            "exit_status": 0,
        },
    ]
    rows = profiler.profile(records)
    assert len(rows) == 2
    # Sorted by p95 RSS desc: the radiant run leads (the RAM floor).
    top = rows[0]
    assert top["command"] == "python -m gfem.radiant run"
    assert top["count"] == 2
    assert top["workers_max"] == 8
    assert top["failures"] == 1
    assert top["peak_rss_mb_max"] == 4000.0


def test_cli_table_and_json(tmp_path, capsys):
    """The CLI renders a table by default and JSON under --json."""
    log = tmp_path / "usage.jsonl"
    log.write_text(
        json.dumps(
            {
                "command": "python -m x run",
                "wall_s": 1,
                "peak_rss_mb": 100,
                "cpu_total_s": 1,
                "workers": 2,
                "cpu_count": 4,
                "exit_status": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert profiler.main([str(log)]) == 0
    assert "peak command" in capsys.readouterr().out

    assert profiler.main([str(log), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["command"] == "python -m x run"


def test_cli_missing_path_exits_2(tmp_path):
    """A missing log path is a clean, distinct exit code (2), not a crash."""
    assert profiler.main([str(tmp_path / "nope.jsonl")]) == 2


def test_profiler_runs_as_subprocess(tmp_path):
    """Smoke test: the script runs end to end as `python telemetry_profile.py`."""
    log = tmp_path / "usage.jsonl"
    log.write_text(
        json.dumps(
            {
                "command": "python -m x run",
                "wall_s": 1,
                "peak_rss_mb": 100,
                "cpu_total_s": 1,
                "exit_status": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(PROFILE_PATH), str(log)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "python -m x run" in result.stdout
