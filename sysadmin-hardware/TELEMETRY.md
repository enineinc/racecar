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

Schema 2 adds two backward-only blocks — information capturable only at run time,
lost afterward, and useful in accumulation. `work` holds whatever the command
self-reports through [`mark()`](#reporting-work-scale) (rows, bytes, files): the
denominator that turns a resource number into a *rate* (per-row, per-MB), which is
what makes sizing predictive rather than merely descriptive. `provenance` records
the run-time git SHA and dirty flag, the Python version, host, virtualenv, and a
hash of the installed dependency set — the context that attributes a later resource
or failure shift to the exact code and environment that produced it, which the
repo's current state cannot reconstruct.

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

`racecar-upgrade` does this for you, mechanically: [`scripts/instrument_telemetry.py`](../scripts/instrument_telemetry.py)
delivers the probe to each top package and `ast`-wraps every `__main__.py` run-guard — a single
`main()` dispatch becomes `run(main)`, any other non-trivial guard is wrapped whole in
`with record():` (behavior-preserving for any body), and every generated file is re-parsed
before it is written. It is idempotent (a guard already calling `run()`/`record()` is skipped)
and delivers the probe by AST comparison, so a re-run never fights the adopter's formatter. The
manual form, for a repo not yet on racecar:

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

### Reporting work scale

A command turns its resource numbers into *rates* by reporting how much work it did:

```python
from <pkg>._telemetry import mark

mark(rows=len(batch))     # accumulates across calls; lands in the record's `work`
mark(bytes=path.stat().st_size, files=1)
```

`mark()` is a no-op when telemetry is off, accumulates numeric counters across calls
(mark each batch), and never raises — so a command calls it unconditionally, with no
`if enabled()` guard. Report the unit that *scales* the cost (rows, bytes, files); a
reducer can then rank commands by cost-per-unit and project the profile to future
scale, not just fit past peaks.

## Enable switch — on by default, opt-out

Usage telemetry records **by default**; a governed repo opts out deliberately. The
switch is resolved in this order:

1. **Env override** — `RACECAR_USAGE_TELEMETRY` (truthy = on, any other value = off).
   The per-run / per-shell control; wins when set.
2. **Repo-local settings** — `[telemetry].usage` in `.telemetry/settings.toml`, the
   per-developer, gitignored override the `/racecar-telemetry-build` and
   `/racecar-telemetry-share` toggles write (backed by `scripts/telemetry_toggle.py`). It
   sits below the env var and above pyproject, so a developer opts a checkout in or out
   without touching the shared default.
3. **pyproject** — `[tool.racecar.telemetry].usage` (`true`/`false`) in the nearest
   `pyproject.toml`. The shared per-repo config home, so the choice lives in one declarative
   place and a project inherits the default unless it sets it (see `pyproject.toml` in
   racecar itself). The log dir resolves the same way: env `RACECAR_TELEMETRY_DIR` >
   `[tool.racecar.telemetry].dir` > `.telemetry`.
4. **Default on.** Absent all, telemetry records.

The state is never silent: a SessionStart hook (`hooks/session_telemetry_notice.py`) prints
`racecar telemetry: build=… share=… usage=…` and the toggles every session entry in a racecar
repo — consent by disclosure. The `share` switch (`RACECAR_SHARE_TELEMETRY`) is the
build-telemetry counterpart that gates whether the anonymized aggregate leaves the machine; see
[`../shared/DRIFT.md`](../shared/DRIFT.md).

On-by-default is the deliberate choice: opt-in telemetry mostly never gets turned on, so
the data the sizing lens needs never accumulates. It is safe *because measurement cannot
break or surprise* — the log is local and gitignored (never committed or published),
argv is redacted (below), and the probe never alters the command (off is a no-op, on
only appends). The value measured is only ever the owner's own resource cost, on the
owner's own machine; a repo that wants silence sets `usage = false` once in its pyproject
or exports `RACECAR_USAGE_TELEMETRY=0`. (The developer-telemetry counterpart,
`RACECAR_BUILD_TELEMETRY` / `[tool.racecar.telemetry].build`, resolves identically — see
[`../shared/DRIFT.md`](../shared/DRIFT.md).)

## Storage and privacy

Append-only JSONL at `$RACECAR_TELEMETRY_DIR/usage.jsonl`, default
`./.telemetry/usage.jsonl` relative to the process CWD, which for a
`python -m <pkg>` run is the repo root. The log is local machine-and-workload data,
never committed: the first write drops a self-ignoring `.telemetry/.gitignore` (`*`, the
pytest-`.pytest_cache` pattern), so the directory stays out of every commit regardless of
the repo's root `.gitignore` — no root-gitignore edit is required for safety, though the
canonical template lists `.telemetry/` there too. Each line is a single sub-`PIPE_BUF`
write under `O_APPEND`, so concurrent processes never interleave.

Privacy boundary: argv is stored, but **secret-shaped tokens are masked** before it
is written — the value after a secret-named flag (`--token X`, `--password=X`), a
standalone key shape (JWT, `ghp_` / `sk-` / `AKIA…`, a PEM header), and the password
inside a URL all become `<redacted>`. The convention is still that racecar CLIs take
credentials from the environment (dotenv at entrypoints), never as arguments; the
redaction is the belt to that suspenders, so a stray credential on a command line can
never turn the log into a credential store, and — because masking happens once, up
front — it can't leak into the derived `subcommand` / `command` fields either.
Ordinary paths and arguments pass through unchanged. The log stays on the machine that
produced it; the aggregator reads it locally.

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

One object per line. Schema version 2.

| Field | Type | Meaning |
|---|---|---|
| `schema` | int | Schema version (currently 2). |
| `ts_start`, `ts_end` | str | ISO-8601 UTC timestamps (`...Z`). |
| `command` | str | `python -m <module> <subcommand>`, reconstructed. |
| `module` | str or null | Dotted package of the entrypoint (e.g. `gfem.radiant`). |
| `subcommand` | str or null | First positional argv token (the argparse verb). |
| `argv` | list of str | The argument vector with secret-shaped tokens masked to `<redacted>` (paths pass through). |
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
| `work` | object | Work-scale counters the command reported via `mark()` (e.g. `{"rows": 1500}`); `{}` if none. Schema 2. |
| `provenance` | object | Run-time context: `git_sha`, `git_dirty`, `python`, `host`, `venv`, `env_fingerprint`. Gathered after the measurement, so it never inflates the resource numbers; nulls off a git tree. Schema 2. |

POSIX only: the probe needs `resource` and degrades to a no-op where it is
absent (e.g. Windows).
