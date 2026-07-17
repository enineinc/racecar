#!/usr/bin/env python3
"""Aggregate the telemetry JSONL into a per-command resource profile.

Reads the append-only log written by the `_telemetry` probe (see
`sysadmin-hardware/TELEMETRY.md`) and reduces it to one row per command:
invocation count, and the p50 / p95 / max of wall-clock, peak RSS, and CPU
time, plus the largest worker count and CPU-count observed. This is the
empirical half of the racecar-sysadmin-hardware lens: the measured shape a
hardware proposal reasons from, so "size for the peak command" is a number,
not a guess.

Deterministic, stdlib only, no model calls. Rows are sorted by p95 peak RSS
descending, so the memory-binding command (the one that sets the RAM floor)
leads the table.

Usage:
    python3 telemetry_profile.py [PATH] [--json]

PATH defaults to `$RACECAR_TELEMETRY_DIR/usage.jsonl`, else
`./.telemetry/usage.jsonl`. Exit 0 on a clean read (including an empty log),
2 when PATH does not exist.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_DIR_ENV = "RACECAR_TELEMETRY_DIR"
_DEFAULT_DIR = ".telemetry"
_JSONL_NAME = "usage.jsonl"

# Metrics reduced to p50/p95/max, keyed by the record field they read.
_DISTRIBUTIONS = (
    ("wall_s", "wall(s)"),
    ("peak_rss_mb", "rss(MB)"),
    ("cpu_total_s", "cpu(s)"),
    ("cores_used", "cores"),
)


def default_path() -> Path:
    """The log path the probe writes to, honoring `$RACECAR_TELEMETRY_DIR`."""
    root = os.environ.get(_DIR_ENV, "").strip() or _DEFAULT_DIR
    return Path(root) / _JSONL_NAME


def load_records(path: Path) -> list[dict[str, Any]]:
    """Parse the JSONL log, skipping blank and malformed lines."""
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "command" in obj:
                records.append(obj)
    return records


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated q-percentile (0..100) of `values`. Empty -> 0.0."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (q / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def _numbers(records: list[dict[str, Any]], field: str) -> list[float]:
    out: list[float] = []
    for record in records:
        value = record.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out.append(float(value))
    return out


def _max_int(records: list[dict[str, Any]], field: str) -> int | None:
    seen = [
        int(r[field])
        for r in records
        if isinstance(r.get(field), int) and not isinstance(r.get(field), bool)
    ]
    return max(seen) if seen else None


def profile(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce records to one profile row per command, sorted by p95 RSS desc."""
    by_command: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_command.setdefault(str(record["command"]), []).append(record)

    rows: list[dict[str, Any]] = []
    for command, group in by_command.items():
        row: dict[str, Any] = {
            "command": command,
            "count": len(group),
            "workers_max": _max_int(group, "workers"),
            "cpu_count": _max_int(group, "cpu_count"),
            "failures": sum(1 for r in group if r.get("exit_status") not in (0, None)),
        }
        for field, _label in _DISTRIBUTIONS:
            nums = _numbers(group, field)
            row[f"{field}_p50"] = round(percentile(nums, 50), 2)
            row[f"{field}_p95"] = round(percentile(nums, 95), 2)
            row[f"{field}_max"] = round(max(nums), 2) if nums else 0.0
        rows.append(row)

    rows.sort(key=lambda r: r["peak_rss_mb_p95"], reverse=True)
    return rows


def render_table(rows: list[dict[str, Any]]) -> str:
    """Render the profile rows as a fixed-width text table."""
    if not rows:
        return "telemetry_profile: no records yet."

    headers = [
        "command",
        "n",
        "wkr",
        "cores p50/p95",
        "wall p50/p95",
        "rss p50/p95/max",
        "cpu p50/p95",
    ]
    lines = [_row_cells(r) for r in rows]
    widths = [
        max(len(headers[i]), max((len(line[i]) for line in lines), default=0))
        for i in range(len(headers))
    ]
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    out.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for line in lines:
        out.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(line)))

    top = rows[0]
    out.append("")
    out.append(
        f"peak command (RAM floor): {top['command']} "
        f"-> p95 {top['peak_rss_mb_p95']} MB, max {top['peak_rss_mb_max']} MB "
        f"at up to {top['workers_max']} workers, "
        f"cores actually used p95 {top['cores_used_p95']} (of {top['cpu_count']} available)."
    )
    return "\n".join(out)


def _row_cells(row: dict[str, Any]) -> list[str]:
    workers = "-" if row["workers_max"] is None else str(row["workers_max"])
    return [
        row["command"],
        str(row["count"]),
        workers,
        f"{row['cores_used_p50']}/{row['cores_used_p95']}",
        f"{row['wall_s_p50']}/{row['wall_s_p95']}",
        f"{row['peak_rss_mb_p50']}/{row['peak_rss_mb_p95']}/{row['peak_rss_mb_max']}",
        f"{row['cpu_total_s_p50']}/{row['cpu_total_s_p95']}",
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the profiler."""
    parser = argparse.ArgumentParser(
        description="Aggregate telemetry JSONL into a per-command resource profile."
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=None,
        help="JSONL log path (default: $RACECAR_TELEMETRY_DIR or ./.telemetry, /usage.jsonl)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the profile as JSON instead of a text table.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load the telemetry log, build the profile, and print it; return an exit code."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    path = args.path or default_path()
    if not path.exists():
        print(
            f"telemetry_profile: no log at {path} "
            "(set RACECAR_TELEMETRY=1 and run some commands first)",
            file=sys.stderr,
        )
        return 2

    rows = profile(load_records(path))
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(render_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
