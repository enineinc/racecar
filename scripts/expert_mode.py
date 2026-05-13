#!/usr/bin/env python3
"""Install/uninstall the optional `racecar-expert-mode` overlay.

Separate from `./install` — expert mode is opt-in. Two idempotent operations
against `~/.claude/`:

1. Skill symlink `~/.claude/skills/racecar-expert-mode` -> `<racecar>/expert`,
   so the `/racecar-expert-mode` slash command resolves.
2. A managed pointer block in `~/.claude/CLAUDE.md`, delimited by
   `<!-- BEGIN racecar-expert-mode pointer (managed) -->` /
   `<!-- END racecar-expert-mode pointer (managed) -->`, pointing the agent at
   `<racecar>/expert/EXPERT.md`. Content outside the markers is preserved.

Refuses to clobber: a non-symlink at the skill path, or a symlink pointing
somewhere other than `<racecar>/expert`, is left alone (uninstall too).

Discovery / overrides (consistent with `./install`):
  - RACECAR_ROOT  = parent of `scripts/`.
  - skills dir    = `$CLAUDE_SKILLS_PATH` or `~/.claude/skills`.
  - CLAUDE.md     = `$CLAUDE_MD_PATH` or `~/.claude/CLAUDE.md`.

Usage:
    python3 <racecar>/scripts/expert_mode.py install
    python3 <racecar>/scripts/expert_mode.py uninstall
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RACECAR_ROOT = Path(__file__).resolve().parent.parent
EXPERT_DIR = RACECAR_ROOT / "expert"
SKILL_NAME = "racecar-expert-mode"

BEGIN_MARKER = "<!-- BEGIN racecar-expert-mode pointer (managed) -->"
END_MARKER = "<!-- END racecar-expert-mode pointer (managed) -->"


def _skills_dir() -> Path:
    return Path(
        os.environ.get("CLAUDE_SKILLS_PATH", Path.home() / ".claude" / "skills")
    ).expanduser()


def _claude_md() -> Path:
    return Path(
        os.environ.get("CLAUDE_MD_PATH", Path.home() / ".claude" / "CLAUDE.md")
    ).expanduser()


def _block() -> str:
    expert_md = EXPERT_DIR / "EXPERT.md"
    return (
        f"{BEGIN_MARKER}\n"
        f"## Expert output mode: racecar-expert-mode\n"
        f"Operate per `{expert_md}` — terse, high-density output for an expert "
        f"operator: lead with the result; no preamble, recap, or hedging; "
        f"expand only on genuine tradeoffs; do not ask permission for "
        f"authorized work. Re-invoke `/racecar-expert-mode` to reset mid-session.\n"
        f"{END_MARKER}\n"
    )


# --- skill symlink -----------------------------------------------------------


def _link_path() -> Path:
    return _skills_dir() / SKILL_NAME


def _is_ours(link: Path) -> bool:
    return link.is_symlink() and link.resolve() == EXPERT_DIR.resolve()


def install_symlink() -> None:
    """Create the ~/.claude/skills/racecar-expert-mode symlink (refuse to clobber)."""
    link = _link_path()
    if link.is_symlink():
        if _is_ours(link):
            print(f"expert_mode: {link} -> {EXPERT_DIR} (already linked)")
            return
        raise SystemExit(
            f"expert_mode: {link} is a symlink to {link.resolve()}, refusing to "
            f"overwrite. Remove it manually."
        )
    if link.exists():
        raise SystemExit(
            f"expert_mode: {link} exists and is not a symlink, refusing to "
            f"overwrite. Remove it manually."
        )
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(EXPERT_DIR)
    print(f"expert_mode: created {link} -> {EXPERT_DIR}")


def uninstall_symlink() -> None:
    """Remove the skill symlink iff it is ours."""
    link = _link_path()
    if not link.exists() and not link.is_symlink():
        print(f"expert_mode: {link} not present")
        return
    if not link.is_symlink():
        raise SystemExit(f"expert_mode: {link} is not a symlink, refusing to remove.")
    if not _is_ours(link):
        raise SystemExit(
            f"expert_mode: {link} points at {link.resolve()}, not {EXPERT_DIR}; "
            f"refusing to remove."
        )
    link.unlink()
    print(f"expert_mode: removed {link}")


# --- CLAUDE.md block ---------------------------------------------------------


def install_block() -> None:
    """Insert/refresh the managed pointer block in ~/.claude/CLAUDE.md."""
    md = _claude_md()
    existing = md.read_text(encoding="utf-8") if md.exists() else ""
    block = _block()
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before, _, rest = existing.partition(BEGIN_MARKER)
        _, _, after = rest.partition(END_MARKER)
        after = after[1:] if after.startswith("\n") else after
        updated = f"{before}{block}{after}"
    elif not existing:
        updated = block
    else:
        sep = (
            ""
            if existing.endswith("\n\n")
            else ("\n" if existing.endswith("\n") else "\n\n")
        )
        updated = f"{existing}{sep}{block}"
    if updated == existing:
        print(f"expert_mode: {md} already up to date")
        return
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(updated, encoding="utf-8")
    print(f"expert_mode: {'created' if not existing else 'updated'} {md}")


def uninstall_block() -> None:
    """Strip the managed pointer block from ~/.claude/CLAUDE.md."""
    md = _claude_md()
    if not md.exists():
        print(f"expert_mode: {md} not present")
        return
    existing = md.read_text(encoding="utf-8")
    if BEGIN_MARKER not in existing or END_MARKER not in existing:
        print(f"expert_mode: no managed block in {md}")
        return
    before, _, rest = existing.partition(BEGIN_MARKER)
    _, _, after = rest.partition(END_MARKER)
    after = after[1:] if after.startswith("\n") else after
    # collapse a blank-line seam left behind
    if before.endswith("\n\n") and after.startswith("\n"):
        after = after.lstrip("\n")
    updated = f"{before}{after}"
    md.write_text(updated, encoding="utf-8")
    print(f"expert_mode: removed managed block from {md}")


# --- entry point -------------------------------------------------------------


def main() -> int:
    """CLI entry point: install or uninstall the overlay."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("install", "uninstall"))
    args = parser.parse_args()
    if args.action == "install":
        install_symlink()
        install_block()
    else:
        uninstall_symlink()
        uninstall_block()
    return 0


if __name__ == "__main__":
    sys.exit(main())
