"""Tests for scripts/fleet_profile.py — the per-checker fleet reducer.

Covers the checker grouping (dead / noisy / fire-rate), fleet-size counting from the file
tree, and the CLI table / JSON / missing-path behaviors.

Run with:
    pytest scripts/tests/test_fleet_profile.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
import fleet_profile as fp  # noqa: E402


def _rec(repo: str, version: str, checkers: dict) -> dict:
    return {"schema": 1, "repo_id": repo, "run_id": repo + version,
            "racecar_version": version, "label": "check", "checkers": checkers}


def test_profile_groups_by_checker() -> None:
    records = [
        _rec("r1", "v1", {"check_a": {"ok": False, "findings": 2},
                          "check_dead": {"ok": True, "findings": 0}}),
        _rec("r2", "v1", {"check_a": {"ok": False, "findings": 4},
                          "check_dead": {"ok": True, "findings": 0}}),
    ]
    rows = {r["checker"]: r for r in fp.profile(records)}
    assert rows["check_a"]["repos_seen"] == 2
    assert rows["check_a"]["runs"] == 2
    assert rows["check_a"]["fires"] == 2
    assert rows["check_a"]["fire_rate"] == 1.0
    assert rows["check_a"]["total_findings"] == 6
    assert rows["check_a"]["dead"] is False
    assert rows["check_dead"]["dead"] is True
    assert rows["check_dead"]["fire_rate"] == 0.0


def test_dead_checkers_sort_first() -> None:
    records = [_rec("r1", "v1", {"noisy": {"ok": False, "findings": 1},
                                 "dead": {"ok": True, "findings": 0}})]
    rows = fp.profile(records)
    assert rows[0]["checker"] == "dead"  # dead-first


def test_by_version_trend_is_tracked() -> None:
    records = [
        _rec("r1", "v1", {"c": {"ok": False, "findings": 5}}),
        _rec("r1", "v2", {"c": {"ok": True, "findings": 0}}),
    ]
    row = fp.profile(records)[0]
    assert row["by_version"]["v1"]["findings"] == 5
    assert row["by_version"]["v2"]["findings"] == 0


def test_fleet_size_counts_repos_and_writers(tmp_path: Path) -> None:
    for repo, writer in [("repoA", "w1"), ("repoA", "w2"), ("repoB", "w1")]:
        f = tmp_path / repo / f"{writer}.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(_rec(repo, "v1", {"c": {"ok": True, "findings": 0}})) + "\n",
                     encoding="utf-8")
    repos, writers = fp.fleet_size(tmp_path)
    assert repos == 2  # repoA, repoB
    assert writers == 2  # distinct stems w1, w2


def test_cli_table_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "repoA" / "w1.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps(_rec("repoA", "v1", {"c": {"ok": False, "findings": 3}})) + "\n",
                 encoding="utf-8")
    # --k 1: a single-repo fixture is below the default k=5 cohort and would be suppressed.
    assert fp.main([str(tmp_path), "--k", "1"]) == 0
    assert "fleet:" in capsys.readouterr().out

    assert fp.main([str(tmp_path), "--json", "--k", "1"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["checker"] == "c"


def test_k_anonymity_suppresses_below_cohort() -> None:
    records = [_rec("r1", "v1", {"c": {"ok": False, "findings": 1}}),
               _rec("r2", "v1", {"c": {"ok": False, "findings": 1}})]  # 'c' in 2 distinct repos
    rows = fp.profile(records)
    shown, suppressed = fp.apply_k_anonymity(rows, k=3)
    assert shown == [] and suppressed == 1        # below cohort: withheld but counted
    shown, suppressed = fp.apply_k_anonymity(rows, k=2)
    assert len(shown) == 1 and suppressed == 0     # exactly at cohort: shown
    shown, suppressed = fp.apply_k_anonymity(rows, k=1)
    assert len(shown) == 1 and suppressed == 0     # k<=1: full local view


def test_cli_default_k_suppresses_single_repo(capsys: pytest.CaptureFixture[str],
                                              tmp_path: Path) -> None:
    f = tmp_path / "repoA" / "w1.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps(_rec("repoA", "v1", {"c": {"ok": False, "findings": 3}})) + "\n",
                 encoding="utf-8")
    assert fp.main([str(tmp_path)]) == 0  # default k=5, one repo -> all suppressed
    out = capsys.readouterr().out
    assert "suppressed" in out and "--k 1" in out  # honest, not silent


def test_cli_missing_path_exits_2(tmp_path: Path) -> None:
    assert fp.main([str(tmp_path / "nope")]) == 2
