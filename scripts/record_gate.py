#!/usr/bin/env python3
"""record_gate.py — DEVELOPER telemetry: append one gate-outcome record per run.

This is developer telemetry, deliberately kept separate from the *usage* telemetry
that `sysadmin-hardware/lib/_telemetry.py` collects. Usage telemetry is ambient — it
measures what a command costs when a user runs it (resources), behind
`RACECAR_USAGE_TELEMETRY`, stored in `.telemetry/usage.jsonl`. This measures the
maintainer's own signal — whether the gate is trending green — recorded when *you* run
the gate, behind its own switch `RACECAR_BUILD_TELEMETRY`, stored in
`.telemetry/build.jsonl`. Both are on by default (opt-out) and configured under
`[tool.racecar.telemetry]`; the two never share a switch or a file.

A transparent wrapper: ``record_gate.py <label> [--] <command...>`` runs the command,
streams its output through, records the outcome keyed to the current git commit, and
exits with the command's own exit code — so it can stand in for the raw command
anywhere (``record_gate.py check make check``).

Why it exists. The deterministic checkers answer "what is true now"; none answer "which
way is it moving," because trajectory requires a record of the past. Accumulated over
time this ledger is exactly that — the DRIFT trajectory ([`shared/DRIFT.md`](../shared/DRIFT.md)):
which checkers fire, how finding counts move commit-to-commit, whether the gate trends
green. It is the backward-only signal the static checks structurally cannot show.

On by default, opt-out: it records unless ``RACECAR_BUILD_TELEMETRY`` is set falsy, or
``[tool.racecar.telemetry].build = false`` in pyproject.toml (env wins) — disabled, it is
a pure passthrough. One JSON object per run, appended to
``$RACECAR_TELEMETRY_DIR/build.jsonl`` (default ``.telemetry/build.jsonl``, gitignored):

    {schema, ts, git_sha, git_dirty, branch, label, command, ok, exit_code, wall_s,
     total_findings, checkers: {<name>: {ok, findings}}}

``ok`` / ``exit_code`` are authoritative. ``checkers`` / ``total_findings`` are
best-effort, parsed from racecar's checker summary convention (``<name>: OK`` /
``<name>: N errors``); a gate whose output does not follow it still records its exit.

Usage:
    RACECAR_BUILD_TELEMETRY=1 python scripts/record_gate.py check -- make check
    RACECAR_BUILD_TELEMETRY=1 python scripts/record_gate.py arch  -- make arch
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
_TRUTHY = frozenset({"1", "true", "yes", "on"})
# A racecar checker summary line: `<name>: OK` (pass) or `<name>: N errors` / a message.
_SUMMARY_RE = re.compile(r"^(?P<name>[a-z][a-z0-9_]*): (?P<rest>\S.*)$")
_ERRORS_RE = re.compile(r"\b(\d+)\s+errors?\b")


_config_cache: dict[str, object] | None = None  # pylint: disable=invalid-name


def _config() -> dict[str, object]:
    """`[tool.racecar.telemetry]` from the nearest pyproject.toml (memoized), or `{}`.

    The config home for the switch and the log dir; read once, walking up from the CWD.
    Any failure (no pyproject, no `tomllib`, malformed TOML) degrades to `{}` — the
    on-by-default, `.telemetry` defaults. Config must never break the gate.
    """
    global _config_cache  # pylint: disable=global-statement
    if _config_cache is not None:
        return _config_cache
    resolved: dict[str, object] = {}
    try:
        import tomllib  # pylint: disable=import-outside-toplevel  # stdlib 3.11+
    except ImportError:
        _config_cache = resolved
        return resolved
    for base in (Path.cwd(), *Path.cwd().parents):
        pyproject = base / "pyproject.toml"
        if pyproject.is_file():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                section = data.get("tool", {}).get("racecar", {}).get("telemetry", {})
                if isinstance(section, dict):
                    resolved = section
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            break
    _config_cache = resolved
    return resolved


def _switch(env_name: str, cfg_key: str) -> bool:
    """Resolve a switch: env override (truthy on / else off) > pyproject > on by default."""
    raw = os.environ.get(env_name, "").strip().lower()
    if raw:
        return raw in _TRUTHY
    cfg = _config()
    if cfg_key in cfg:
        return bool(cfg[cfg_key])
    return True


def _enabled() -> bool:
    """Whether the gate ledger records — on by default; opt out via env or pyproject."""
    return _switch("RACECAR_BUILD_TELEMETRY", "build")


def _log_path() -> Path:
    root = (
        os.environ.get("RACECAR_TELEMETRY_DIR", "").strip()
        or str(_config().get("dir", "")).strip()
        or ".telemetry"
    )
    return Path(root) / "build.jsonl"


def _git(args: list[str]) -> str | None:
    """Stripped stdout of `git <args>`, or None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=2, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _git_context() -> dict[str, object]:
    sha = _git(["rev-parse", "--short", "HEAD"])
    if sha is None:
        return {"git_sha": None, "git_dirty": None, "branch": None}
    status = _git(["status", "--porcelain"])
    return {
        "git_sha": sha,
        "git_dirty": bool(status) if status is not None else None,
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
    }


def run_streamed(command: list[str]) -> tuple[int, list[str], float]:
    """Run `command`, echo its merged output live, and return (exit, lines, wall_s)."""
    start = time.monotonic()
    try:
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        print(f"record_gate: cannot run {command!r}: {exc}", file=sys.stderr)
        return 127, [], time.monotonic() - start
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        lines.append(line)
    proc.wait()
    return proc.returncode, lines, round(time.monotonic() - start, 3)


def parse_checkers(lines: list[str]) -> tuple[dict[str, dict[str, object]], int]:
    """Best-effort per-checker outcomes from summary lines, and the total finding count.

    A `<name>: OK …` line is a pass (0 findings); a `<name>: N errors` line contributes
    N; any other non-OK summary counts as at least one finding. Later lines win, so a
    checker's final summary is what lands (checkers print progress then a verdict).
    """
    checkers: dict[str, dict[str, object]] = {}
    for raw in lines:
        match = _SUMMARY_RE.match(raw.strip())
        if not match:
            continue
        name, rest = match.group("name"), match.group("rest")
        if rest.startswith("OK"):
            checkers[name] = {"ok": True, "findings": 0}
            continue
        counted = _ERRORS_RE.search(rest)
        # Only treat a line as a verdict when it counts errors or is a known status;
        # this avoids miscounting an informational `name: note` line as a failure.
        if counted:
            checkers[name] = {"ok": False, "findings": int(counted.group(1))}
    total = sum(int(entry["findings"]) for entry in checkers.values())
    return checkers, total


def record(label: str, command: list[str]) -> int:
    """Run the gate, write one ledger record (when enabled), return the gate's exit."""
    exit_code, lines, wall_s = run_streamed(command)
    if not _enabled():
        return exit_code
    checkers, total = parse_checkers(lines)
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **_git_context(),
        "label": label,
        "command": command,
        "ok": exit_code == 0,
        "exit_code": exit_code,
        "wall_s": wall_s,
        "total_findings": total,
        "checkers": checkers,
    }
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    except OSError as exc:  # a ledger failure must never fail the gate
        print(f"record_gate: could not write ledger: {exc}", file=sys.stderr)
    return exit_code


def main(argv: list[str]) -> int:
    """Parse `<label> [--] <command...>`, run it recorded, return its exit code."""
    if not argv:
        print("usage: record_gate.py <label> [--] <command...>", file=sys.stderr)
        return 2
    label, command = argv[0], argv[1:]
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("record_gate: no command given", file=sys.stderr)
        return 2
    return record(label, command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
