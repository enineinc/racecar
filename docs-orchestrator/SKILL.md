---
name: racecar-docs
description: Orchestrate a racecar repo's documentation as a THIN COMPOSER — never a re-implementation. Runs the doc pipeline in dependency order (generate the missing required docs, regenerate the machine-derivable spine, apply the content-blindness gate, then the coherence/link gate), composing the homes that already own each capability: the llm-summary lens for the shareable brief, arch-coherence's surface-doc scaffolders for CLI/REST/MCP docs, and doc-coherence's checkers for links, the doc graph, subsystem coverage, and placement. Newly owns only what has no home yet: the required-docs manifest, the content-blindness contract (a frontmatter-declared, leak-preventing discipline generalized from seshat), and the orchestration sequence with its no-clobber-but-repair generation. Use when asked to "set up the docs", "generate missing documentation", "regenerate the doc spine", "make this repo content-blind", "run the docs pipeline", or "audit and fix the documentation set".
---

# racecar-docs

Load [`ORCHESTRATION.md`](ORCHESTRATION.md) in full. It holds the required-docs manifest, the four-stage orchestration sequence, the no-clobber-but-repair generation contract, the checker-composition table (which existing home each capability comes from), and the invocation prompts. Load [`CONTENT_BLINDNESS.md`](CONTENT_BLINDNESS.md) when the task touches the content-blindness policy: it is the one home for the rule definition and the README-frontmatter schema.

Operational reminder: this skill COMPOSES; it does not re-implement. Before writing any doc, run the deterministic backbone to see the current state:

```
# From inside the racecar repo
make docs

# From any project with the skill installed
python3 ~/.claude/skills/racecar-docs/scripts/docs_orchestrate.py
```

The orchestrator runs the composed checkers in dependency order and prints one consolidated report with a single exit code. Generation of narrative and of the brief is the agent's to drive per ORCHESTRATION.md; the orchestrator gates it. Exit 0 is clean; a failed gate names the checker and the finding.
