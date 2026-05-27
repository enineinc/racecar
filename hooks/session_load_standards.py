#!/usr/bin/env python3
"""SessionStart hook — force-load racecar's cross-cutting baseline into context.

The CLAUDE.md pointer alone is only an instruction; the agent may treat
racecar's README as a routing table to consult later, not as loaded standards
present right now. This hook inlines README.md and every shared/*.md as
`additionalContext` and frames them so the agent recognizes them as already
loaded — not as a preview or table of contents.

Framing rule:
  - Racecar's baseline (README router + shared/*.md) is ALWAYS loaded by
    this hook on every SessionStart.
  - The lens files (arch-coherence/, eng-review/, doc-coherence/,
    llm-summary/) are LOADED ON DEMAND per the README's routing table —
    by design; the README itself says "Do not load component files
    speculatively."
  - The correct answer to "is racecar loaded?" is "yes — baseline is
    present; lenses load when a task selects them."

Wired by sync_claude_md.py on four SessionStart matchers — startup, resume,
clear, compact — so the baseline is re-injected after /clear and after
auto-compaction as well.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RACECAR_ROOT = Path(__file__).resolve().parent.parent


def _collect() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    readme = RACECAR_ROOT / "README.md"
    if readme.is_file():
        items.append((readme, readme.read_text()))
    shared = RACECAR_ROOT / "shared"
    if shared.is_dir():
        for path in sorted(shared.glob("*.md")):
            items.append((path, path.read_text()))
    return items


def main() -> int:
    raw = sys.stdin.read()
    try:
        _ = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        pass

    items = _collect()
    if not items:
        return 0

    file_list = "\n".join(f"  - {p}" for p, _ in items)
    sections = [f"### {path}\n\n{body}" for path, body in items]
    preamble = (
        "RACECAR IS LOADED.\n"
        "\n"
        "The files below are now part of your context. Treat them as already "
        "loaded — do not Read them again, do not describe them as a "
        "'preview' or 'routing table not yet loaded'. They are present, in "
        "full, right here:\n"
        f"{file_list}\n"
        "\n"
        "What 'loaded' means for racecar:\n"
        "  - Baseline (the files above: README router + shared/*.md) is "
        "ALWAYS loaded on every SessionStart by the session_load_standards "
        "hook. This is the always-on layer — operational discipline, "
        "persona, drift doctrine, voice, glossary, ownership, commit rules, "
        "TODO format.\n"
        "  - Lenses (arch-coherence/, eng-review/, doc-coherence/, "
        "llm-summary/) load on demand. The README is the router — when a "
        "task matches a topic, Read the lens file it points to. Per the "
        "README itself: do not load lens files speculatively.\n"
        "\n"
        "If asked 'is racecar loaded?' the answer is YES — the baseline is "
        "present in this context; lenses load when a task selects them.\n"
    )
    message = preamble + "\n---\n\n" + "\n\n---\n\n".join(sections)
    # `systemMessage` is the user-visible terminal line. `additionalContext`
    # is silent — it enters the agent's context only. The agent's loud
    # "RACECAR IS LOADED" preamble lives in additionalContext (it's for the
    # agent's framing, not for the user); the systemMessage here is a short
    # operator confirmation that the hook ran.
    visible = f"racecar: baseline loaded ({len(items)} files)"
    out = {
        "systemMessage": visible,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        },
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
