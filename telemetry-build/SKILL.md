---
name: racecar-telemetry-build
description: Turn build (developer) telemetry on or off for this checkout — the gate-outcome ledger record_gate.py appends to .telemetry/build.jsonl when you run make check / make arch. Writes the per-developer, gitignored .telemetry/settings.toml (env > settings.toml > pyproject > on). Use when asked to "turn off build telemetry", "stop recording gate outcomes", "opt out of developer telemetry", "/racecar-telemetry-build on|off", or to check the current build-telemetry state.
---

# racecar-telemetry-build

Flip **build telemetry** for this checkout. Build telemetry is racecar measuring *itself*:
`record_gate.py` appends one gate-outcome record (which checkers fired, finding counts,
pass/fail, the canon version in force) to `.telemetry/build.jsonl` each time you run
`make check` / `make arch`. It is on by default, opt-out, local and gitignored; a later
`racecar-upgrade` harvests it — anonymized, minimized — into racecar's fleet so racecar learns
which of its checkers are dead or noisy. Off is a pure no-op.

## Run it

Deterministic; the logic lives in [`scripts/telemetry_toggle.py`](../scripts/telemetry_toggle.py):

    python3 scripts/telemetry_toggle.py build off    # opt this checkout out
    python3 scripts/telemetry_toggle.py build on     # opt back in
    python3 scripts/telemetry_toggle.py build        # report the current setting

Parse the user's argument (`on` / `off`, or none = report) and invoke accordingly, then relay
the printed state. It writes one boolean into `[telemetry]` in `.telemetry/settings.toml` — the
per-developer, gitignored override resolved as **env > `.telemetry/settings.toml` > pyproject
`[tool.racecar.telemetry]` > on**. It never edits pyproject and never commits.

## Notes

- This governs the **local** ledger only. To stop the anonymized aggregate leaving the machine,
  use [`/racecar-telemetry-share`](../telemetry-share/SKILL.md); the two are independent switches.
- A per-run override without writing the file: `RACECAR_BUILD_TELEMETRY=0 make check`.
- The session disclosure line (`racecar telemetry: build=…`) reflects the new state next session.
