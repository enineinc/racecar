#!/usr/bin/env python3
"""Sync racecar bootstrap into the local Claude Code config.

Two idempotent operations against `~/.claude/`:

1. Pointer block in `~/.claude/CLAUDE.md` — a managed `<!-- BEGIN/END
   racecar pointer -->` block that points the agent at this checkout.
2. Hooks in `~/.claude/settings.json`, wired to absolute paths inside
   this checkout:
     - `PreToolUse` Bash  → `hooks/compound-command-allow.sh`
     - `PostToolUse` Read → `hooks/claude_racecar_hook.sh`
     - `PreCompact` (matcher "" = manual+auto) → `hooks/precompact_history.py`
       (deterministic decision-log marker)
     - `SessionStart` (matcher "compact") → `hooks/session_compact_history.py`
       (prompts the agent to reconcile <repo>/.claude/HISTORY.md from the
       transcript after compaction)
     - `SessionStart` (matchers startup/resume/clear/compact) →
       `hooks/session_load_standards.py` (force-loads CLAUDE.md + shared/*.md)
     - `SessionStart` (matchers startup/resume/clear/compact) →
       `hooks/session_discover_cli.py` (runs check_cli_commands.py --json
       on the consuming repo and injects the audit tree as
       additionalContext)
   The decision-log hooks no-op unless the project has a
   `.claude/HISTORY.md`. The discovery hook no-ops unless the project has
   a pyproject.toml with `[project].name`.

Every run rewrites both in place. Designed to be invoked manually
(Makefile) or automatically (Claude Code PostToolUse hook on Read of
`racecar/README.md` or `racecar/CLAUDE.md`).

Discovery:
  - RACECAR_ROOT is the parent directory of `scripts/`, computed from
    this file's own location. Works regardless of where racecar is
    cloned on this machine.
  - CLAUDE.md target defaults to `~/.claude/CLAUDE.md`. Override with
    `--claude-md` or `CLAUDE_MD_PATH`.
  - settings.json target defaults to `~/.claude/settings.json`.
    Override with `--settings` or `CLAUDE_SETTINGS_PATH`.

Block markers (CLAUDE.md):
  <!-- BEGIN racecar pointer (managed) -->
  ...
  <!-- END racecar pointer (managed) -->

Hook identification (settings.json): an existing hook entry whose
`command` ends with the same script basename is treated as racecar's
and rewritten in place. Other hooks at the same matcher are preserved.

Usage:
    python3 <racecar>/scripts/sync_claude_md.py
    python3 <racecar>/scripts/sync_claude_md.py --dry-run
    python3 <racecar>/scripts/sync_claude_md.py --claude-md /path/to/CLAUDE.md
    python3 <racecar>/scripts/sync_claude_md.py --settings /path/to/settings.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

BEGIN_MARKER = "<!-- BEGIN racecar pointer (managed) -->"
END_MARKER = "<!-- END racecar pointer (managed) -->"

RACECAR_ROOT = Path(__file__).resolve().parent.parent

POST_HOOK_BASENAME = "claude_racecar_hook.sh"
PRE_HOOK_BASENAME = "compound-command-allow.sh"
PRECOMPACT_HOOK_BASENAME = "precompact_history.py"
SESSIONSTART_HOOK_BASENAME = "session_compact_history.py"
SESSION_LOAD_HOOK_BASENAME = "session_load_standards.py"
SESSION_DISCOVER_HOOK_BASENAME = "session_discover_cli.py"
SESSION_CHECK_SYNC_HOOK_BASENAME = "session_check_sync.py"
SESSION_LOAD_MATCHERS = ("startup", "resume", "clear", "compact")


# --- CLAUDE.md pointer block -------------------------------------------------


def render_block(racecar_root: Path) -> str:
    claude_md = racecar_root / "CLAUDE.md"
    shared = racecar_root / "shared"
    readme = racecar_root / "README.md"
    return (
        f"{BEGIN_MARKER}\n"
        f"## Standards: racecar (governs this repo)\n"
        f"racecar is a deterministic code-review framework applied to this "
        f"project. When doing AI-assisted work here, use its lenses and run "
        f"its checks.\n\n"
        f"Machine baseline (you, the agent): `{claude_md}` plus every `*.md` "
        f"under `{shared}` are FORCE-LOADED every SessionStart by the "
        f"`session_load_standards` hook (wired by `./install` on matchers "
        f"startup/resume/clear/compact) — operational discipline, persona, "
        f"drift, voice, glossary, ownership, commits, TODO format, plus the "
        f"resolver. Treat the baseline as already loaded; do not Read those "
        f"files again. Human overview: `{readme}`.\n\n"
        f"Load a lens ON DEMAND when the task matches, never speculatively:\n"
        f"- architecture / import cycles / layers / faces  -> /racecar-arch-coherence\n"
        f"- code quality / Python-Django hygiene           -> /racecar-eng-review\n"
        f"- docs / drift / link integrity                  -> /racecar-doc-coherence\n"
        f"- repo brief for another LLM                      -> /racecar-llm-summary\n"
        f"- commit + version bump                          -> /racecar-commit\n"
        f"- before committing (dry-run the hooks)          -> /racecar-commit-preflight\n"
        f"- split a working tree into commits              -> /racecar-commit-decompose\n"
        f"- audit this project against racecar             -> /racecar-normalize\n"
        f"- \"is racecar loaded?\"                           -> /racecar-doctor\n\n"
        f"Enforce mechanically in THIS repo: `make arch` / `make check` plus "
        f"pre-commit. A failure names file:line; fix it before proceeding.\n"
        f"{END_MARKER}\n"
    )


def replace_or_append(existing: str, block: str) -> str:
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before, _, rest = existing.partition(BEGIN_MARKER)
        _, _, after = rest.partition(END_MARKER)
        if after.startswith("\n"):
            after = after[1:]
        return f"{before}{block}{after}"
    separator = (
        ""
        if existing.endswith("\n\n")
        else ("\n" if existing.endswith("\n") else "\n\n")
    )
    if not existing:
        return block
    return f"{existing}{separator}{block}"


# --- settings.json hooks -----------------------------------------------------


def upsert_hook(
    settings: dict[str, Any],
    event: str,
    matcher: str,
    command: str,
    basename: str,
) -> bool:
    """Ensure `settings.hooks[event]` has a matcher entry containing `command`.

    A racecar-managed hook is identified by its command ending in `basename`
    (with optional whitespace/quotes), allowing us to rewrite a stale path
    without disturbing unrelated hooks. Returns True if the settings dict
    was mutated.
    """
    hooks_root = settings.setdefault("hooks", {})
    if not isinstance(hooks_root, dict):
        raise ValueError(
            f"settings.json `hooks` is not an object: {type(hooks_root).__name__}"
        )

    event_entries = hooks_root.setdefault(event, [])
    if not isinstance(event_entries, list):
        raise ValueError(f"settings.json `hooks.{event}` is not an array")

    matcher_entry: dict[str, Any] | None = None
    for entry in event_entries:
        if isinstance(entry, dict) and entry.get("matcher") == matcher:
            matcher_entry = entry
            break

    created_matcher = False
    if matcher_entry is None:
        matcher_entry = {"matcher": matcher, "hooks": []}
        event_entries.append(matcher_entry)
        created_matcher = True

    inner = matcher_entry.setdefault("hooks", [])
    if not isinstance(inner, list):
        raise ValueError(
            f"settings.json `hooks.{event}[matcher={matcher}].hooks` is not an array"
        )

    desired = {"type": "command", "command": command}

    for h in inner:
        if not isinstance(h, dict):
            continue
        cmd = h.get("command", "")
        if isinstance(cmd, str) and cmd.rstrip().rstrip('"').rstrip("'").endswith(
            basename
        ):
            if h == desired:
                return created_matcher
            h.clear()
            h.update(desired)
            return True

    inner.append(desired)
    return True


def sync_settings(
    racecar_root: Path,
    settings_path: Path,
    *,
    dry_run: bool,
) -> tuple[bool, str]:
    """Upsert both hooks into settings.json. Returns (changed, rendered_text)."""
    pre_command = str(racecar_root / "hooks" / PRE_HOOK_BASENAME)
    post_command = str(racecar_root / "hooks" / POST_HOOK_BASENAME)

    if settings_path.exists():
        raw = settings_path.read_text()
        try:
            settings = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as e:
            raise SystemExit(f"sync_claude_md: cannot parse {settings_path}: {e}")
    else:
        raw = ""
        settings = {}

    if not isinstance(settings, dict):
        raise SystemExit(
            f"sync_claude_md: {settings_path} top-level value is not a JSON object"
        )

    pre_changed = upsert_hook(
        settings, "PreToolUse", "Bash", pre_command, PRE_HOOK_BASENAME
    )
    post_changed = upsert_hook(
        settings, "PostToolUse", "Read", post_command, POST_HOOK_BASENAME
    )

    # Decision-log hooks. The PreCompact marker is deterministic (matcher ""
    # catches both manual + auto compaction); the SessionStart(compact) hook
    # prompts the agent to reconcile <repo>/.claude/HISTORY.md from the
    # transcript after compaction. Both no-op unless the project has a
    # .claude/HISTORY.md — see hooks/precompact_history.py.
    precompact_command = str(racecar_root / "hooks" / PRECOMPACT_HOOK_BASENAME)
    sessionstart_command = str(racecar_root / "hooks" / SESSIONSTART_HOOK_BASENAME)
    precompact_changed = upsert_hook(
        settings, "PreCompact", "", precompact_command, PRECOMPACT_HOOK_BASENAME
    )
    sessionstart_changed = upsert_hook(
        settings,
        "SessionStart",
        "compact",
        sessionstart_command,
        SESSIONSTART_HOOK_BASENAME,
    )

    # SessionStart standards-loader. The pointer block above is only an
    # instruction; the agent may skip it. This hook inlines racecar's machine
    # baseline (CLAUDE.md + shared/*.md) as additionalContext on every relevant
    # session boundary so the standards are present whether or not the agent
    # followed the pointer.
    session_load_command = str(racecar_root / "hooks" / SESSION_LOAD_HOOK_BASENAME)
    session_load_changed = False
    for matcher in SESSION_LOAD_MATCHERS:
        if upsert_hook(
            settings,
            "SessionStart",
            matcher,
            session_load_command,
            SESSION_LOAD_HOOK_BASENAME,
        ):
            session_load_changed = True

    # SessionStart CLI-discovery hook. Runs check_cli_commands.py --json
    # against the consuming repo and injects the audit tree as
    # additionalContext, so agents land in a repo already knowing its
    # `python -m <pkg>` surface. Same four matchers as the standards
    # loader — startup, resume, clear, compact — so the snapshot is
    # re-injected after /clear and auto-compaction.
    session_discover_command = str(
        racecar_root / "hooks" / SESSION_DISCOVER_HOOK_BASENAME
    )
    session_discover_changed = False
    for matcher in SESSION_LOAD_MATCHERS:
        if upsert_hook(
            settings,
            "SessionStart",
            matcher,
            session_discover_command,
            SESSION_DISCOVER_HOOK_BASENAME,
        ):
            session_discover_changed = True

    # SessionStart sync-staleness hook. Warns when this repo's synced racecar
    # check scripts have fallen behind canon (session_check_sync.py byte-compares
    # them against the checkout). No-ops in a non-adopter repo or one in sync.
    session_check_command = str(
        racecar_root / "hooks" / SESSION_CHECK_SYNC_HOOK_BASENAME
    )
    session_check_changed = False
    for matcher in SESSION_LOAD_MATCHERS:
        if upsert_hook(
            settings,
            "SessionStart",
            matcher,
            session_check_command,
            SESSION_CHECK_SYNC_HOOK_BASENAME,
        ):
            session_check_changed = True

    rendered = json.dumps(settings, indent=2) + "\n"
    changed = (
        pre_changed
        or post_changed
        or precompact_changed
        or sessionstart_changed
        or session_load_changed
        or session_discover_changed
        or session_check_changed
        or (rendered != raw)
    )

    if changed and not dry_run:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(rendered)

    return changed, rendered


# --- target resolution -------------------------------------------------------


def resolve_path(arg: str | None, env: str, default: Path) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env_value = os.environ.get(env)
    if env_value:
        return Path(env_value).expanduser().resolve()
    return default.resolve()


# --- entry point -------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--claude-md",
        "--target",
        dest="claude_md",
        help="Path to CLAUDE.md (default: $CLAUDE_MD_PATH or ~/.claude/CLAUDE.md).",
    )
    parser.add_argument(
        "--settings",
        help="Path to settings.json (default: $CLAUDE_SETTINGS_PATH or ~/.claude/settings.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resulting files to stdout instead of writing.",
    )
    args = parser.parse_args()

    claude_md = resolve_path(
        args.claude_md, "CLAUDE_MD_PATH", Path.home() / ".claude" / "CLAUDE.md"
    )
    settings_path = resolve_path(
        args.settings, "CLAUDE_SETTINGS_PATH", Path.home() / ".claude" / "settings.json"
    )

    block = render_block(RACECAR_ROOT)
    existing_md = claude_md.read_text() if claude_md.exists() else ""
    updated_md = replace_or_append(existing_md, block)

    settings_changed, rendered_settings = sync_settings(
        RACECAR_ROOT, settings_path, dry_run=args.dry_run
    )

    if args.dry_run:
        sys.stdout.write(f"--- {claude_md} ---\n")
        sys.stdout.write(updated_md)
        sys.stdout.write(f"\n--- {settings_path} ---\n")
        sys.stdout.write(rendered_settings)
        return 0

    md_changed = updated_md != existing_md
    if md_changed:
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(updated_md)
        print(
            f"sync_claude_md: {'created' if not existing_md else 'updated'} {claude_md}"
        )
    else:
        print(f"sync_claude_md: {claude_md} already up to date")

    if settings_changed:
        print(f"sync_claude_md: updated hooks in {settings_path}")
    else:
        print(f"sync_claude_md: {settings_path} hooks already up to date")

    return 0


if __name__ == "__main__":
    sys.exit(main())
