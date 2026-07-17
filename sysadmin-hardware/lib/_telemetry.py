# sysadmin-hardware/lib/_telemetry.py — OPTIONAL runtime probe. Copy to your
# package's source root as `<pkg>/_telemetry.py` (e.g. src/gfem/_telemetry.py)
# to record a resource-usage line per CLI invocation. It is the empirical input
# the racecar-sysadmin-hardware lens consumes; see sysadmin-hardware/TELEMETRY.md
# for the record schema, the enable switch, and the one-line adoption.
#
# This is runtime code the CLI imports, so it must live in the package tree
# (like the optional arch-coherence/lib/_cli.py renderer), not in ~/.claude
# where a check script lives. Modifying it is a standards-change conversation,
# not a per-project decision. Copy it verbatim.
"""Cheap, stdlib-only resource telemetry for a racecar `python -m <pkg>` CLI.

racecar CLIs dispatch through one `main()` per `__main__.py` (arch-coherence/
CLI.md). Wrapping that single call records the whole command uniformly, without
any subcommand opting in by hand:

    if __name__ == "__main__":
        from <pkg>._telemetry import run
        run(main)

`run(main)` executes `main()` inside `record()`, which times the process,
reads `resource.getrusage`, and appends one JSON object to the telemetry log.
`record()` is also usable directly as a context manager when the entrypoint
does work around `main()`.

Off by default: nothing is written unless `RACECAR_TELEMETRY` is truthy in the
environment (`1`/`true`/`yes`/`on`). This keeps disk untouched on the happy
path and honors racecar's dotenv-at-entrypoints discipline (opt in from the
one place env is read). When enabled, the probe never changes the command's
behavior or output and never raises into the command: any telemetry failure is
swallowed (surfaced on stderr only when `RACECAR_TELEMETRY_DEBUG` is truthy).

Storage: append-only JSONL at `$RACECAR_TELEMETRY_DIR/usage.jsonl`, default
`./.telemetry/usage.jsonl` (relative to the process CWD, which for a
`python -m <pkg>` invocation is the repo root). One object per line; see
TELEMETRY.md for the schema. POSIX only (needs `resource`); a graceful no-op
where that module is absent.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    import resource
except ImportError:  # non-POSIX (e.g. Windows): probe degrades to a no-op.
    resource = None  # type: ignore[assignment]

SCHEMA_VERSION = 1

_ENABLE_ENV = "RACECAR_TELEMETRY"
_DIR_ENV = "RACECAR_TELEMETRY_DIR"
_DEBUG_ENV = "RACECAR_TELEMETRY_DEBUG"
_DEFAULT_DIR = ".telemetry"
_JSONL_NAME = "usage.jsonl"
_TRUTHY = frozenset({"1", "true", "yes", "on"})
# Flags whose value is a worker/concurrency count, if the command exposes one.
_WORKER_FLAGS = ("--workers", "--jobs", "-j")


def enabled() -> bool:
    """True when telemetry is switched on via the `RACECAR_TELEMETRY` env var."""
    return os.environ.get(_ENABLE_ENV, "").strip().lower() in _TRUTHY


def _debug() -> bool:
    return os.environ.get(_DEBUG_ENV, "").strip().lower() in _TRUTHY


def log_path() -> Path:
    """Resolve the JSONL log path: `$RACECAR_TELEMETRY_DIR/usage.jsonl` or the default."""
    root = os.environ.get(_DIR_ENV, "").strip() or _DEFAULT_DIR
    return Path(root) / _JSONL_NAME


def _main_package() -> str | None:
    """The dotted package of the running `python -m <pkg>` entrypoint.

    For `python -m gfem.radiant`, the `__main__` module carries
    `__package__ == "gfem.radiant"`; fall back to its `__spec__.parent`. Returns
    None when the process was not launched as a package module.
    """
    main_mod = sys.modules.get("__main__")
    pkg = getattr(main_mod, "__package__", None)
    if pkg:
        return pkg
    spec = getattr(main_mod, "__spec__", None)
    parent = getattr(spec, "parent", None)
    return parent or None


def _subcommand(argv: Sequence[str]) -> str | None:
    """First positional token in argv (the argparse subcommand), if any."""
    for token in argv:
        if not token.startswith("-"):
            return token
    return None


def _workers(argv: Sequence[str]) -> int | None:
    """Worker/concurrency count parsed from argv, if the command exposes one.

    Handles both `--workers N` and `--workers=N` (and the `-j` / `--jobs`
    spellings). Returns None when no such flag is present or its value is not an
    integer.
    """
    for i, token in enumerate(argv):
        for flag in _WORKER_FLAGS:
            if token == flag and i + 1 < len(argv):
                return _as_int(argv[i + 1])
            if token.startswith(flag + "="):
                return _as_int(token[len(flag) + 1 :])
    return None


def _as_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _peak_rss_bytes(usage_self: Any, usage_children: Any) -> int:
    """Peak resident-set size in bytes across the process and its children.

    `ru_maxrss` is a high-water mark, not a delta: bytes on macOS, kibibytes on
    Linux. Take the larger of the two high-water marks (the process itself, and
    the largest single child) so a thread-pool workload reports the parent peak
    and a process-pool workload reports its heaviest child.
    """
    scale = 1 if sys.platform == "darwin" else 1024
    return max(usage_self.ru_maxrss, usage_children.ru_maxrss) * scale


def _exit_code(code: object) -> int:
    """Normalize a `SystemExit` code to an integer status (None -> 0, str -> 1)."""
    if code is None:
        return 0
    if isinstance(code, bool):
        return int(code)
    if isinstance(code, int):
        return code
    return 1


class _Probe:
    """One in-flight measurement: start marks captured, finish emits the record."""

    def __init__(self, argv: Sequence[str]) -> None:
        self.argv = list(argv)
        self.package = _main_package()
        self.wall_start = time.monotonic()
        self.ts_start = datetime.now(timezone.utc)
        self.rusage_self_start = resource.getrusage(resource.RUSAGE_SELF)
        self.rusage_children_start = resource.getrusage(resource.RUSAGE_CHILDREN)

    def _record(self, status: int) -> dict[str, Any]:
        end_self = resource.getrusage(resource.RUSAGE_SELF)
        end_children = resource.getrusage(resource.RUSAGE_CHILDREN)
        ts_end = datetime.now(timezone.utc)
        wall = time.monotonic() - self.wall_start

        cpu_user = (end_self.ru_utime - self.rusage_self_start.ru_utime) + (
            end_children.ru_utime - self.rusage_children_start.ru_utime
        )
        cpu_sys = (end_self.ru_stime - self.rusage_self_start.ru_stime) + (
            end_children.ru_stime - self.rusage_children_start.ru_stime
        )
        io_read = (end_self.ru_inblock - self.rusage_self_start.ru_inblock) + (
            end_children.ru_inblock - self.rusage_children_start.ru_inblock
        )
        io_write = (end_self.ru_oublock - self.rusage_self_start.ru_oublock) + (
            end_children.ru_oublock - self.rusage_children_start.ru_oublock
        )

        subcommand = _subcommand(self.argv)
        command = f"python -m {self.package}" if self.package else "python -m ?"
        if subcommand:
            command = f"{command} {subcommand}"

        cpu_total = cpu_user + cpu_sys
        # Mean parallelism actually exercised: CPU-seconds burned per wall-second.
        # ~1 is serial; ~N means N cores kept busy on average. The single point
        # value that says how many vCPUs a run truly used, independent of the
        # worker count it was launched with.
        cores_used = round(cpu_total / wall, 2) if wall > 0 else 0.0

        return {
            "schema": SCHEMA_VERSION,
            "ts_start": self.ts_start.isoformat().replace("+00:00", "Z"),
            "ts_end": ts_end.isoformat().replace("+00:00", "Z"),
            "command": command,
            "module": self.package,
            "subcommand": subcommand,
            "argv": self.argv,
            "wall_s": round(wall, 4),
            "cpu_user_s": round(cpu_user, 4),
            "cpu_sys_s": round(cpu_sys, 4),
            "cpu_total_s": round(cpu_total, 4),
            "cores_used": cores_used,
            "peak_rss_mb": round(
                _peak_rss_bytes(end_self, end_children) / 1_048_576, 2
            ),
            "io_read_blocks": max(io_read, 0),
            "io_write_blocks": max(io_write, 0),
            "workers": _workers(self.argv),
            "cpu_count": os.cpu_count(),
            "exit_status": status,
            "pid": os.getpid(),
            "platform": sys.platform,
        }

    def finish(self, status: int) -> None:
        """Emit the resource record for this run to the append-only JSONL log."""
        payload = self._record(status)
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        # A single write() of a sub-PIPE_BUF line under O_APPEND is atomic on
        # POSIX, so concurrent `python -m` processes never interleave lines.
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)


@contextmanager
def record(argv: Sequence[str] | None = None) -> Iterator[None]:
    """Measure the wrapped block and append one telemetry record on exit.

    A no-op (zero added cost beyond an env lookup) unless `RACECAR_TELEMETRY` is
    set and `resource` is importable. Records the exit status: 0 on clean
    return, the `SystemExit` code when the block exits via `sys.exit`, 1 on any
    other exception. The original exit or exception always propagates unchanged;
    telemetry never alters control flow, and a failure inside the probe is
    swallowed (shown on stderr only under `RACECAR_TELEMETRY_DEBUG`).
    """
    if not enabled() or resource is None:
        yield
        return

    try:
        probe: _Probe | None = _Probe(sys.argv[1:] if argv is None else argv)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _warn(exc)
        probe = None

    try:
        yield
    except SystemExit as exc:
        _safe_finish(probe, _exit_code(exc.code))
        raise
    except BaseException:
        _safe_finish(probe, 1)
        raise
    # Reached only on a clean return; the except branches above re-raise.
    _safe_finish(probe, 0)


def run(main: Callable[[], Any], argv: Sequence[str] | None = None) -> None:
    """Run `main()` under `record()`. The one-line adoption at a CLI entrypoint."""
    with record(argv=argv):
        main()


def _safe_finish(probe: _Probe | None, status: int) -> None:
    if probe is None:
        return
    try:
        probe.finish(status)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _warn(exc)


def _warn(exc: BaseException) -> None:
    if _debug():
        sys.stderr.write(f"[racecar-telemetry] suppressed: {exc!r}\n")
