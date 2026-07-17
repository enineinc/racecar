---
summary: The telemetry mechanism — a cheap stdlib probe that records one resource-usage line per `python -m <pkg>` CLI run, its record schema, enable switch, storage path, and the one-line adoption a governed repo adds.
pnode: [README.md]
---

# CLI telemetry

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Telemetry is the empirical half of hardware sizing: to size a box for a repo you
need to know what its commands actually cost. This mechanism records one
resource-usage line per CLI invocation, uniformly across every subcommand, with
no per-command opt-in and no change to what the command does or prints. It is
stdlib only (`resource`, `time`, `os`), dependency-light, and off unless you
switch it on.

## What it captures

One JSON object per `python -m <pkg> <subcommand>` run: the command string and
argv, start and end timestamps, wall-clock, peak RSS, CPU time (user, sys,
total), cores actually used (mean parallelism, CPU-seconds per wall-second),
exit status, worker count when the command exposes `--workers` / `--jobs` / `-j`,
the host CPU count, best-effort disk-IO block counts, and the pid and platform.
Every field is a point value that helps triangulate a hardware choice. `cores_used`
is the one that says how many vCPUs a run truly used, independent of the worker
count it was launched with, so a run that asked for 16 workers but exercised 3
cores tells you not to pay for 16.

## The hook point

racecar CLIs dispatch through one `main()` per `__main__.py` (the §3 contract in
[`../arch-coherence/CLI.md`](../arch-coherence/CLI.md)). Wrapping that single call
covers every subcommand of that module at once. The probe attaches there and
nowhere else: it reads the running package name from the `__main__` module and
the subcommand from argv, so it needs no argument and no knowledge of the command.

Because each `python -m <pkg>.<sub>` is its own process, there is no single
shared entrypoint in code; the wrap goes at each `__main__.py`'s run guard, one
line each, all delegating to the one probe module. This is the same shape as the
optional [`../arch-coherence/lib/_cli.py`](../arch-coherence/lib/_cli.py) renderer:
one home for the logic, a thin call at each node. The rejected alternative, a
global `sitecustomize` / `runpy` hook that captures every `python -m` in the
environment, is too magic and too broad: it would record unrelated invocations
and hide the instrumentation from the code that carries it.

## The one-line adoption

Copy [`lib/_telemetry.py`](lib/_telemetry.py) into the package source root as
`<pkg>/_telemetry.py` (it is runtime code the CLI imports, so it lives in the
tree, not in `~/.claude`). Then wrap each `__main__.py` run guard:

```python
if __name__ == "__main__":
    from <pkg>._telemetry import run
    run(main)
```

`run(main)` executes `main()` inside `record()`, the context manager that does
the measurement. Use `record()` directly when an entrypoint does work around
`main()`. The wrap never changes behavior: the command's exit code and any
exception propagate unchanged, and a failure inside the probe is swallowed
(surfaced on stderr only under `RACECAR_TELEMETRY_DEBUG`).

## Enable switch, and why it is off by default

Nothing is written unless `RACECAR_TELEMETRY` is truthy (`1`/`true`/`yes`/`on`)
in the environment. Off by default is the choice most consistent with racecar's
principles:

1. **Dotenv at entrypoints.** A governed repo reads env only at the CLI
   entrypoint; the switch belongs in that one `.env`, turned on deliberately, not
   baked into the library.
2. **No surprise writes, happy path untouched.** When off, `record()` costs one
   env lookup and writes nothing. Measurement is opt-in, so a fresh clone never
   accretes a log the owner did not ask for.
3. **Ownership.** Turning measurement on is the owner's call (R-05); the probe
   enables it, it does not impose it.

## Storage and privacy

Append-only JSONL at `$RACECAR_TELEMETRY_DIR/usage.jsonl`, default
`./.telemetry/usage.jsonl` relative to the process CWD, which for a
`python -m <pkg>` run is the repo root. Add `.telemetry/` to `.gitignore`: the
log is local machine-and-workload data, never committed. Each line is a single
sub-`PIPE_BUF` write under `O_APPEND`, so concurrent processes never interleave.

Privacy boundary: the record stores argv verbatim, which can contain filesystem
paths (`--data-root`, `--spec-root`, dates). It does not, and must not, carry
secrets: racecar CLIs take credentials from the environment (dotenv at
entrypoints), never as arguments, so argv is safe to log. The log stays on the
machine that produced it; the aggregator reads it locally.

## Reading it back

[`scripts/telemetry_profile.py`](scripts/telemetry_profile.py) loads the JSONL
and reduces it to one row per command: invocation count, worker count, and the
p50 / p95 / max of cores-used, wall-clock, peak RSS, and CPU time, sorted by p95
peak RSS descending so the memory-binding command leads. That top row is the
peak command the [`HARDWARE.md`](HARDWARE.md) lens sizes for.

```
python3 scripts/telemetry_profile.py [PATH] [--json]
```

## Record schema

One object per line. Schema version 1.

| Field | Type | Meaning |
|---|---|---|
| `schema` | int | Schema version (currently 1). |
| `ts_start`, `ts_end` | str | ISO-8601 UTC timestamps (`...Z`). |
| `command` | str | `python -m <module> <subcommand>`, reconstructed. |
| `module` | str or null | Dotted package of the entrypoint (e.g. `gfem.radiant`). |
| `subcommand` | str or null | First positional argv token (the argparse verb). |
| `argv` | list of str | The argument vector, verbatim (paths yes, secrets no). |
| `wall_s` | float | Wall-clock seconds. |
| `cpu_user_s`, `cpu_sys_s`, `cpu_total_s` | float | CPU seconds (self + children), user / sys / total. |
| `cores_used` | float | Mean parallelism: `cpu_total_s / wall_s`. ~1 serial, ~N means N cores busy. |
| `peak_rss_mb` | float | Peak resident set (self and children high-water mark), MB. |
| `io_read_blocks`, `io_write_blocks` | int | Best-effort disk-IO block deltas from `rusage` (often 0 on macOS). |
| `workers` | int or null | Concurrency from `--workers` / `--jobs` / `-j`, if present. |
| `cpu_count` | int or null | `os.cpu_count()` on the host. |
| `exit_status` | int | 0 clean, the `SystemExit` code on `sys.exit`, 1 on any other exception. |
| `pid` | int | Process id. |
| `platform` | str | `sys.platform` (RSS units differ: bytes on darwin, KiB on linux, normalized here). |

POSIX only: the probe needs `resource` and degrades to a no-op where it is
absent (e.g. Windows).
