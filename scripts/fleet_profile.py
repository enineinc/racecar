#!/usr/bin/env python3
"""fleet_profile.py — reduce the harvested build-telemetry fleet to a per-checker signal.

`harvest_build_telemetry.py` accumulates anonymized gate outcomes from across the fleet into
`.telemetry/fleet/<repo_id>/<writer_id>.jsonl`. This reduces that aggregate to one row per
racecar checker — the signal that tells racecar which of its own rules earn their keep:

  * **dead** checkers (never fire fleet-wide) — kill candidates: cost with no catch.
  * **noisy** checkers (high fire-rate) — over-broad candidates: worth scoping tighter.
  * **trend by canon version** — did a racecar release move findings? (the `--json` `by_version`).

It is the fleet counterpart to `sysadmin-hardware/scripts/telemetry_profile.py` (which profiles
the *usage* log per command); this profiles the *build* aggregate per checker. Person wall:
`writers_seen` is a count derived from distinct filenames only — no row is ever keyed to a
writer, and no record carries one.

**k-anonymity.** A checker row appears only when at least `--k` *distinct repos* contributed it
(default 5, the anonymity set is the company-wall unit `repo_id`). Below that cohort a stat
could point back at a specific repo — since `repo_id` is pseudonymous, not anonymous — so it is
suppressed and only *counted* in the summary (never silently dropped). Pass `--k 1` for the
aggregator's own full local view; a higher `--k` for a report meant to be shared. This is the
same defense gstack applies at its community-pulse read boundary.

Usage:
    python3 scripts/fleet_profile.py [PATH] [--json] [--k N]

PATH is the fleet root (a directory tree of per-writer JSONL) or a single JSONL file;
default `.telemetry/fleet` under the racecar checkout.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

_RACECAR_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _RACECAR_ROOT / ".telemetry" / "fleet"
_NOISY_TOP = 5
_DEFAULT_K = 5  # k-anonymity: min distinct repos for a checker to appear (gstack uses 5)


def default_path() -> Path:
    """The default fleet aggregate root: `.telemetry/fleet` under the racecar checkout."""
    return _DEFAULT_PATH


def _jsonl_files(path: Path) -> list[Path]:
    """The JSONL files under `path`: the file itself, or every `*.jsonl` in the tree."""
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.jsonl"))
    return []


def load_records(path: Path) -> list[dict[str, Any]]:
    """Parse every fleet JSONL under `path`, skipping blank and malformed lines."""
    records: list[dict[str, Any]] = []
    for file in _jsonl_files(path):
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("checkers"), dict):
                records.append(obj)
    return records


def fleet_size(path: Path) -> tuple[int, int]:
    """(distinct repos, distinct writers): repos from subdir names, writers from file stems."""
    files = _jsonl_files(path)
    writers = {f.stem for f in files}
    repos = {f.parent.name for f in files} if path.is_dir() else set()
    return len(repos), len(writers)


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile; 0.0 for an empty list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100.0
    low, high = math.floor(k), math.ceil(k)
    if low == high:
        return float(ordered[int(k)])
    return ordered[low] * (high - k) + ordered[high] * (k - low)


def profile(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce records to one row per checker, dead-first then fire-rate descending."""
    acc: dict[str, dict[str, Any]] = {}
    for record in records:
        rid = record.get("repo_id")
        version = record.get("racecar_version")
        for name, outcome in record["checkers"].items():
            if not isinstance(outcome, dict):
                continue
            findings = int(outcome.get("findings", 0) or 0)
            fired = findings > 0 or outcome.get("ok") is False
            row = acc.setdefault(
                name,
                {
                    "checker": name,
                    "repos": set(),
                    "runs": 0,
                    "fires": 0,
                    "total_findings": 0,
                    "_findings": [],
                    "by_version": {},
                },
            )
            row["repos"].add(rid)
            row["runs"] += 1
            row["fires"] += 1 if fired else 0
            row["total_findings"] += findings
            row["_findings"].append(findings)
            ver = row["by_version"].setdefault(str(version), {"runs": 0, "findings": 0})
            ver["runs"] += 1
            ver["findings"] += findings

    rows: list[dict[str, Any]] = []
    for row in acc.values():
        runs = row["runs"]
        fires = row["fires"]
        rows.append(
            {
                "checker": row["checker"],
                "repos_seen": len(row["repos"]),
                "runs": runs,
                "fires": fires,
                "fire_rate": round(fires / runs, 3) if runs else 0.0,
                "total_findings": row["total_findings"],
                "findings_p95": round(percentile(row["_findings"], 95), 1),
                "dead": fires == 0,
                "by_version": row["by_version"],
            }
        )
    rows.sort(key=lambda r: (not r["dead"], -r["fire_rate"], -r["total_findings"]))
    return rows


def apply_k_anonymity(rows: list[dict[str, Any]], k: int) -> tuple[list[dict[str, Any]], int]:
    """Keep only checker rows backed by >= k distinct repos; return (shown, suppressed_count).

    The anonymity set is `repo_id` (the company-wall unit). Below k repos a stat could point
    back at one repo, so it is withheld — but counted, never silently dropped. `k <= 1` keeps
    everything (the aggregator's own full local view).
    """
    if k <= 1:
        return rows, 0
    shown = [r for r in rows if r["repos_seen"] >= k]
    return shown, len(rows) - len(shown)


def _row_cells(row: dict[str, Any]) -> list[str]:
    return [
        row["checker"],
        str(row["repos_seen"]),
        str(row["runs"]),
        str(row["fires"]),
        f"{row['fire_rate']:.2f}",
        str(row["total_findings"]),
        f"{row['findings_p95']:.0f}",
        "dead" if row["dead"] else "",
    ]


def render_table(
    rows: list[dict[str, Any]], repos: int, writers: int, k: int, suppressed: int
) -> str:
    """Render the per-checker rows as a fixed-width table with a fleet summary."""
    knote = f" (k>={k})" if k > 1 else ""
    if not rows:
        tail = (
            f"fleet_profile: {suppressed} checker(s) below the k={k} cohort, suppressed; "
            f"run with --k 1 for the full local view."
            if suppressed
            else "fleet_profile: no records yet."
        )
        return tail

    headers = ["checker", "repos", "runs", "fires", "rate", "finds", "p95", ""]
    cells = [_row_cells(r) for r in rows]
    widths = [
        max(len(headers[i]), max((len(c[i]) for c in cells), default=0))
        for i in range(len(headers))
    ]
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    out.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for cell in cells:
        out.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(cell)))

    dead = [r["checker"] for r in rows if r["dead"]]
    noisy = [r["checker"] for r in rows if not r["dead"]][:_NOISY_TOP]
    out.append("")
    out.append(
        f"fleet: {repos} repos x {writers} writers, {len(rows)} checkers shown{knote}"
    )
    if suppressed:
        out.append(f"suppressed: {suppressed} checker(s) below k={k} (use --k 1 to see them)")
    out.append(f"dead (kill candidates): {', '.join(dead) if dead else 'none'}")
    out.append(f"noisiest: {', '.join(noisy) if noisy else 'none'}")
    return "\n".join(out)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse `[PATH] [--json]`."""
    parser = argparse.ArgumentParser(
        description="Reduce the harvested build-telemetry fleet to a per-checker profile."
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=None,
        help="Fleet root (dir tree) or a single JSONL file (default: .telemetry/fleet).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the profile as JSON instead of a text table.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=_DEFAULT_K,
        help=(
            "k-anonymity: minimum distinct repos for a checker to appear "
            f"(default {_DEFAULT_K}; use 1 for the full local view)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load the aggregate at PATH, reduce it, and print the table (or JSON); 2 if absent."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    path = args.path or default_path()
    if not path.exists():
        print(f"fleet_profile: no aggregate at {path}", file=sys.stderr)
        return 2

    rows, suppressed = apply_k_anonymity(profile(load_records(path)), args.k)
    if args.json:
        # stdout stays a clean, k-safe rows array (pipeable); the drop count goes to stderr.
        print(json.dumps(rows, indent=2))
        if suppressed:
            print(
                f"fleet_profile: {suppressed} checker(s) below k={args.k}, suppressed",
                file=sys.stderr,
            )
    else:
        repos, writers = fleet_size(path)
        print(render_table(rows, repos, writers, args.k, suppressed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
