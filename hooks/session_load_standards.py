#!/usr/bin/env python3
"""SessionStart hook — force-load racecar's cross-cutting baseline into context.

The pointer in the consuming project's CLAUDE.md is only an instruction; the
agent may treat racecar as a routing table to consult later, not as loaded
standards present right now. This hook inlines racecar's machine baseline
(CLAUDE.md and every shared/*.md) as `additionalContext` and frames them so the
agent recognizes them as already loaded — not as a preview or table of contents.
README.md is racecar's human-facing storefront and is deliberately NOT loaded.

Framing rule:
  - Racecar's baseline (CLAUDE.md router + shared/*.md) is ALWAYS loaded by
    this hook on every SessionStart.
  - The lens files (arch-coherence/, eng-review/, doc-coherence/,
    llm-summary/) are LOADED ON DEMAND per CLAUDE.md's routing table —
    by design; CLAUDE.md itself says "do not load lenses speculatively."
  - The correct answer to "is racecar loaded?" is "yes — baseline is
    present; lenses load when a task selects them."

Wired by sync_claude_md.py on four SessionStart matchers — startup, resume,
clear, compact — so the baseline is re-injected after /clear and after
auto-compaction as well.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RACECAR_ROOT = Path(__file__).resolve().parent.parent


def load_token(items: list[tuple[Path, str]]) -> str:
    """Content-derived load token: first 12 hex of sha256 over the baseline.

    Deterministic — same baseline bytes, same token. Planted in the preamble
    so 'is racecar loaded?' can be answered by reproducing the token from
    context (challenge-response), not by echoing a banner. scripts/doctor.py
    recomputes this independently; one home for the computation is here.
    """
    digest = hashlib.sha256()
    for _, body in items:
        digest.update(body.encode("utf-8"))
    return digest.hexdigest()[:12]


def collect_baseline() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    claude_md = RACECAR_ROOT / "CLAUDE.md"
    if claude_md.is_file():
        items.append((claude_md, claude_md.read_text()))
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

    items = collect_baseline()
    if not items:
        return 0

    file_list = "\n".join(f"  - {p}" for p, _ in items)
    sections = [f"### {path}\n\n{body}" for path, body in items]
    token = load_token(items)
    preamble = (
        "RACECAR IS LOADED.\n"
        "\n"
        f"Load token: {token}\n"
        "\n"
        "The files below are now part of your context. Treat them as already "
        "loaded — do not Read them again, do not describe them as a "
        "'preview' or 'routing table not yet loaded'. They are present, in "
        "full, right here:\n"
        f"{file_list}\n"
        "\n"
        "What 'loaded' means for racecar:\n"
        "  - Baseline (the files above: CLAUDE.md router + shared/*.md) is "
        "ALWAYS loaded on every SessionStart by the session_load_standards "
        "hook. This is the always-on layer — operational discipline, "
        "persona, drift doctrine, voice, glossary, ownership, commit rules, "
        "TODO format.\n"
        "  - Lenses (arch-coherence/, eng-review/, doc-coherence/, "
        "llm-summary/) load on demand. CLAUDE.md is the router — when a "
        "task matches a topic, Read the lens file it points to. Per CLAUDE.md "
        "itself: do not load lens files speculatively. (README.md is the "
        "human storefront and is not loaded here.)\n"
        "\n"
        "If asked 'is racecar loaded?' the answer is YES — and the evidence "
        "is the load token above. Reproduce the token and one substantive "
        "baseline fact (a specific rule from shared/) from context, without "
        "re-reading any file. Echoing 'RACECAR IS LOADED' alone is assertion, "
        "not evidence. If you cannot produce the token, the baseline is NOT "
        "in context — say so and recommend `make doctor` in the racecar "
        "checkout.\n"
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
