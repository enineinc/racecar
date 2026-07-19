---
name: racecar-telemetry-share
description: Turn sharing on or off for this checkout — whether the anonymized, minimized build-telemetry aggregate may leave the machine for racecar's fleet. Writes the per-developer, gitignored .telemetry/settings.toml (env > settings.toml > pyproject > on). Use when asked to "stop sharing telemetry", "don't send telemetry off my machine", "opt out of sharing", "/racecar-telemetry-share on|off", or to check the current share state.
---

# racecar-telemetry-share

Flip **sharing** for this checkout — whether the anonymized, minimized build-telemetry aggregate
may leave this machine for racecar's shared fleet. On by default, opt-out. Sharing is bounded by
two walls: the *company wall* (only structural checker data crosses — an opaque, machine-
independent repo id, never a real SHA, branch, command, or path) and the *person wall* (no writer
identity or timestamp is ever in a record, so nothing can profile a person). What would be shared
is only `{racecar_version, checker, fired, findings}` per gate run. Off keeps every record local.

## Run it

Deterministic; the logic lives in [`scripts/telemetry_toggle.py`](../scripts/telemetry_toggle.py):

    python3 scripts/telemetry_toggle.py share off    # keep telemetry on this machine only
    python3 scripts/telemetry_toggle.py share on      # allow the anonymized aggregate to be shared
    python3 scripts/telemetry_toggle.py share          # report the current setting

Parse the user's argument (`on` / `off`, or none = report) and invoke accordingly, then relay the
printed state. It writes one boolean into `[telemetry]` in `.telemetry/settings.toml`, resolved as
**env > `.telemetry/settings.toml` > pyproject `[tool.racecar.telemetry]` > on**. It never edits
pyproject and never commits.

## Notes

- Sharing off does **not** stop local recording — build telemetry still accumulates in
  `.telemetry/build.jsonl` for your own use; it just never leaves. To stop local recording too,
  use [`/racecar-telemetry-build`](../telemetry-build/SKILL.md).
- A per-run override without writing the file: `RACECAR_SHARE_TELEMETRY=0 …`.
- The session disclosure line (`racecar telemetry: … share=…`) reflects the new state next session.
