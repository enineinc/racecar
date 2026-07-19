#!/usr/bin/env python3
"""harvest_build_telemetry.py — pull each target's build ledger up into racecar, anonymized.

Build telemetry (`scripts/record_gate.py` -> `<repo>/.telemetry/build.jsonl`) measures
*racecar itself*: which of racecar's checkers fire, how finding counts move, whether the gate
trends green. Its subject is racecar's standards, so it only earns its keep once it flows
**back** to racecar. This is that flow: read each target's ledger, minimize + anonymize it,
and append it to racecar's fleet aggregate under a per-writer file. `fleet_profile.py` then
reduces the aggregate to dead / noisy checkers and findings-trend-by-canon-version.

Two walls bound what crosses:
  * Company wall — repo identity never leaves the target. `repo_id` is the hashed git
    root-commit SHA (identical on every clone/machine, so one repo is one id everywhere), and
    `git_sha` / `branch` / `command` are dropped. `repo_id` is *pseudonymous* (the root-commit
    SHA is computable by anyone with the repo), so the aggregate is treated as confidential.
  * Person wall — aggregating gate outcomes across developers must never become individual
    surveillance. `writer_id` (an opaque per-machine salt) names the *file* only; it is never
    written into a record. The shared record carries no timestamp and no per-commit trail, so
    it cannot profile when or how often a person works.

The output record is the minimized, share-ready artifact — anonymized at source, so a later
push to a shared telemetry repo is a file copy with no second transform and no path where raw
identity ships:

    {schema, repo_id, run_id, racecar_version, label, checkers: {<name>: {ok, findings}}}

`run_id` = hash(repo_id, original ts, label) is an opaque dedup/count token; it reveals no
time and links to no commit. Harvest is idempotent: re-running never double-counts (dedup on
`run_id`), and a second clone of the same repo lands on the same `repo_id`.

Usage:
    python3 scripts/harvest_build_telemetry.py <target-repo>...
    python3 scripts/harvest_build_telemetry.py ~/dev/foo ~/dev/bar --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FLEET_SCHEMA = 1
_RACECAR_ROOT = Path(__file__).resolve().parents[1]
_WRITER_ID_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    / "racecar"
    / "writer-id"
)


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _git(target: Path, args: list[str]) -> str | None:
    """Stripped stdout of `git -C <target> <args>`, or None on any failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(target), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def repo_id(target: Path) -> str:
    """A machine-independent, opaque id for the repo: hashed git root-commit SHA(s).

    The root commit is identical in every clone on every machine, so the same repo maps to the
    same id everywhere — unlike a path hash, which would split one repo across machines. A repo
    with a merged history can have several root commits; they are sorted so the id is stable.
    Falls back to a hashed absolute path only when the target is not a git tree.
    """
    roots = _git(target, ["rev-list", "--max-parents=0", "HEAD"])
    if roots:
        return _sha12("".join(sorted(roots.split())))
    return _sha12("path:" + str(target.resolve()))


def writer_id() -> str:
    """This machine's opaque, stable writer id — a random salt, created once, reused.

    Names the per-writer file so two writers never share one (conflict-free git merge later)
    and lets the reducer count distinct writers. It is never a username or hostname, and never
    appears inside a record — so it cannot be used to profile a person.
    """
    try:
        existing = _WRITER_ID_PATH.read_text(encoding="utf-8").strip()
        if existing:
            return existing[:12]
    except OSError:
        pass
    fresh = os.urandom(16).hex()[:12]
    try:
        _WRITER_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
        _WRITER_ID_PATH.write_text(fresh + "\n", encoding="utf-8")
    except OSError:
        pass  # a non-persisted id still works for this run; harmless
    return fresh


def anonymize(record: dict, rid: str) -> dict:
    """Reduce one raw build record to the minimized, anonymized, share-ready fleet record.

    Company wall + minimization floor in one pure function (so a future push can anonymize at
    source with the same call). Keeps only the checker signal, the canon version, and the gate
    label; drops every identifying or profiling field.
    """
    run_id = _sha12(f"{rid}:{record.get('ts')}:{record.get('label')}")
    checkers = record.get("checkers")
    return {
        "schema": FLEET_SCHEMA,
        "repo_id": rid,
        "run_id": run_id,
        "racecar_version": record.get("racecar_version"),
        "label": record.get("label"),
        "checkers": checkers if isinstance(checkers, dict) else {},
    }


def _read_jsonl(path: Path) -> list[dict]:
    """Parse a JSONL file into dict records, skipping blank and malformed lines."""
    records: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return records
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _existing_run_ids(path: Path) -> set[str]:
    return {r["run_id"] for r in _read_jsonl(path) if isinstance(r.get("run_id"), str)}


def harvest_target(target: Path, dest_root: Path, wid: str, dry_run: bool) -> dict:
    """Harvest one target's ledger into `<dest_root>/<repo_id>/<writer_id>.jsonl`.

    Returns a small report dict: {target, repo_id, new, dup, missing}.
    """
    rid = repo_id(target)
    report = {"target": str(target), "repo_id": rid, "new": 0, "dup": 0, "missing": False}
    ledger = target / ".telemetry" / "build.jsonl"
    if not ledger.is_file():
        report["missing"] = True
        return report

    out_path = dest_root / rid / f"{wid}.jsonl"
    seen = _existing_run_ids(out_path)
    fresh: list[dict] = []
    for raw in _read_jsonl(ledger):
        record = anonymize(raw, rid)
        if record["run_id"] in seen:
            report["dup"] += 1
            continue
        seen.add(record["run_id"])
        fresh.append(record)

    report["new"] = len(fresh)
    if fresh and not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as handle:
            for record in fresh:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse `<target>... [--dest DIR] [--dry-run]`."""
    parser = argparse.ArgumentParser(
        description="Harvest targets' build telemetry into racecar's anonymized fleet aggregate."
    )
    parser.add_argument("targets", nargs="+", type=Path, help="Target repo paths to harvest.")
    parser.add_argument(
        "--dest",
        type=Path,
        default=_RACECAR_ROOT / ".telemetry" / "fleet",
        help="Fleet aggregate root (default: racecar's .telemetry/fleet).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be harvested without writing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Harvest every named target into the fleet aggregate; report per-target and total."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    wid = writer_id()
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    total_new = 0
    for target in args.targets:
        report = harvest_target(target, args.dest, wid, args.dry_run)
        if report["missing"]:
            print(f"harvest: {target}: no build ledger, skipped")
            continue
        total_new += report["new"]
        verb = "would harvest" if args.dry_run else "harvested"
        print(
            f"harvest: {target}: {verb} {report['new']} new, "
            f"{report['dup']} dup (repo {report['repo_id']})"
        )
    tail = " (dry run)" if args.dry_run else ""
    print(f"harvest: {total_new} new records at {stamp}{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
