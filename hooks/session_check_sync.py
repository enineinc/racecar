#!/usr/bin/env python3
"""SessionStart hook — warn when a repo's synced racecar checks are behind canon.

The gap this closes: an adopter repo's synced check scripts (copied by
sync_scripts.py / racecar-normalize / racecar-upgrade) can silently fall behind
racecar's canon between syncs. Nothing in `make check` notices, so a repo can run
stale checks indefinitely. This hook is the standing detector: every time Claude
starts in an adopter repo, it byte-compares the repo's synced scripts against the
current canon and, if any drifted, injects a notice naming them and the fix.

Deterministic (content compare, not a version label that can lie), and it reuses
ONE home for the script list (`sync_scripts.CHECK_SCRIPTS`). It no-ops silently
for a non-adopter repo (no synced scripts) or a repo already in sync.

Wired by sync_claude_md.py on the SessionStart matchers. Pure stdlib.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RACECAR_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACECAR_ROOT / "scripts"))
from sync_scripts import CHECK_SCRIPTS, canon_ref  # noqa: E402  (one home for both)

# Written into an adopter's scripts/ by sync_scripts.py: the racecar ref the repo
# last synced from. Advisory context only; the content compare is the truth.
STAMP_REL = "scripts/.racecar-version"


def find_project_root(start: Path) -> Path:
    """Nearest ancestor of `start` (default CWD) containing `.git`."""
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    return start


def is_adopter(project_root: Path) -> bool:
    """A racecar adopter has the canonical packaging check synced in."""
    return (project_root / "scripts" / "check_packaging.py").is_file()


def sync_status(project_root: Path) -> tuple[list[str], list[str], str | None]:
    """Return (stale, missing, stamp_version) for the project's synced scripts.

    `stale`   = synced scripts whose bytes differ from current canon.
    `missing` = canon scripts absent from the repo's scripts/.
    `stamp_version` = the version recorded at last sync, or None.
    """
    stale: list[str] = []
    missing: list[str] = []
    for rel in CHECK_SCRIPTS:
        source = RACECAR_ROOT / rel
        if not source.is_file():
            continue
        name = Path(rel).name
        target = project_root / "scripts" / name
        if not target.is_file():
            missing.append(name)
        elif target.read_bytes() != source.read_bytes():
            stale.append(name)
    stamp = project_root / STAMP_REL
    stamp_version = stamp.read_text(encoding="utf-8").strip() if stamp.is_file() else None
    return sorted(stale), sorted(missing), stamp_version


def main() -> int:
    raw = sys.stdin.read()
    try:
        source = (json.loads(raw) if raw.strip() else {}).get("source", "")
    except json.JSONDecodeError:
        source = ""

    # Act only on session entry. On mid-session context events (clear/compact) the
    # staleness state is unchanged from startup, so re-emitting the status would be
    # noise — stay silent. Unknown/absent source falls through and runs.
    if source in ("clear", "compact"):
        return 0

    project_root = find_project_root(Path.cwd())

    # na — not a racecar adopter. Do nothing, silently: a status line in every
    # unrelated repo on the machine would be pure noise.
    if not is_adopter(project_root):
        return 0

    stale, missing, stamp_ref = sync_status(project_root)
    ref = canon_ref()
    repo = project_root.name

    # noop — adopter, in sync. Emit a one-line confirmation so "ran and clean" is
    # distinguishable from "never ran" (the silence is ambiguous otherwise). The
    # systemMessage is the user-visible status; no additionalContext to keep the
    # agent's context uncluttered when there is nothing to do.
    if not stale and not missing:
        print(json.dumps({"systemMessage": f"racecar: noop | {repo} in sync with racecar:{ref}"}))
        return 0

    # upgrade — adopter, drifted. Prompt the fix, loud (systemMessage) and in the
    # agent's context (additionalContext) so it does not trust a green gate.
    n = len(stale) + len(missing)
    from_ref = f", synced from {stamp_ref}" if stamp_ref else ""
    detail = ", ".join(stale + missing)
    notice = (
        f"RACECAR OUT OF SYNC. {repo} is behind racecar:{ref}{from_ref} — {n} synced "
        f"check script(s) drifted: {detail}. The repo is running stale checks. Refresh "
        f"with `python {RACECAR_ROOT}/scripts/sync_scripts.py --dest .` or run "
        f"/racecar-upgrade. Do not trust a green gate until resynced."
    )
    out = {
        "systemMessage": f"racecar: upgrade | {repo} out-of-sync with racecar:{ref} ({n} script(s)) — run /racecar-upgrade",
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": notice},
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
