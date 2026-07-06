---
pnode: [SKILL.md]
---

# LLM Summary

The generator (not a review lens): it packages a repo into one shareable Markdown file another person can drag into their own LLM and interview (what the system is, how it works, what entities and endpoints exist) without source access.

Run it with `/racecar-llm-summary`. The bundle lands at `docs/summary/<REPO>.md`.

**When to reach for it:** you want a single file to share with a collaborator, partner, or investor so they can ask their own LLM about the system; or you want to brainstorm refactors from your phone without uploading the repo.

**Not for:** code-writing handoff (that is `CLAUDE.md`), release notes, or reconstruction-grade specs.

## What's here

| Doc | Covers |
|---|---|
| [`SPEC.md`](SPEC.md) | **Start here.** The bundle spec: the YAML frontmatter schema (entities / relationships / external surface), the discovery procedure, the output contract, the bundle lifecycle, the structural budget. |

The validator is [`scripts/check_brief.py`](scripts/check_brief.py).

Pair with the review lenses under [`../arch-coherence/README.md`](../arch-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md), and [`../doc-coherence/README.md`](../doc-coherence/README.md). The human storefront is the repo [`../README.md`](../README.md).
