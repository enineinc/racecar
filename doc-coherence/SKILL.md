---
name: racecar-doc-coherence
description: Documentation coherence review — update protocol (PRESERVE, ADD, UPDATE, DELETE, REVIEW) plus the review lens: cogency, scope honesty, file naming, rule testability, one-home-per-rule. Owns the mechanical pre-pass implemented by `scripts/check_docs.py` — a generic tool that auto-discovers repo layout via `.git` walk-up, not racecar-specific. Use when asked to review docs, check link integrity, audit documentation drift, verify doc-vs-code agreement, or before shipping any doc change.
---

# racecar-doc-coherence

Load [`README.md`](README.md) in full. It holds the update protocol, the mechanical pre-pass, the five document checks, mental models, red flags, decision patterns, feedback format, and invocation prompts.

Operational reminder: run the mechanical pre-pass first via Bash before any prose review.

```
# From inside the racecar repo
make check-docs

# From any project with this skill installed at ~/.claude/skills/racecar-doc-coherence/
python3 ~/.claude/skills/racecar-doc-coherence/scripts/check_docs.py
```

The script walks up from CWD to find `.git`, auto-discovers top-level directories, and is not repo-specific — it runs against any repo that adopts this lens. Exit 0 is clean; exit 1 prints each drift finding with file and line. Collapse drift findings into a single root; do not inflate into N independent issues.

Output format: numbered roots with severity (Blocker / Major / Minor / Nit), verdict line at the end (Ship / Revise / Rework). No preamble.
