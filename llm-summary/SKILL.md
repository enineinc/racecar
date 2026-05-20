---
name: racecar-llm-summary
description: Generate a single-file Markdown knowledge package (`docs/$repo/$REPO.md`, ~400-800 lines) designed to be shared as one drag-and-drop file into Claude / Gemini / ChatGPT (mobile or desktop). A recipient using their own LLM can interview the system — ask what it is, how it works conceptually, what entities exist at the class level, what relationships connect them, what endpoints it exposes, why design choices were made, what's working, what's open — without needing source access or repo installation. YAML frontmatter carries the queryable spine (class-level entities, relationships DAG, endpoints by surface kind). Markdown body carries narrative (purpose, design decisions, intentional weirdness, flows, operational, configuration as bullets). Not a reconstruction-grade spec; not a CLAUDE.md replacement. Use when asked to "share a brief of this repo," "produce a knowledge package," "summarize for another LLM," or to noodle on refactors from mobile.
---

# racecar-llm-summary

Load [`README.md`](README.md) in full. It holds the YAML frontmatter schema (entities / relationships / external_surface), the discovery procedure, the output contract (which sections live in frontmatter vs body), the query examples the bundle must answer, the bundle lifecycle, and the structural budget enforced by [`scripts/check_brief.py`](scripts/check_brief.py).

Operational reminder: do not write the brief from memory or guesses. Run the discovery procedure first, cite paths in the draft, then validate with `check_brief.py` (or `make check-brief` from the racecar root) before handing off.
