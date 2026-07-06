---
pnode: [../README.md]
---

# TODO List Rendering Format

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

This file has two halves. The **source schema** is how open work is written on disk — the contract every project's `TODO.md` and per-concern TODO sections must satisfy, enforced mechanically by [`../doc-coherence/scripts/check_todo_format.py`](../doc-coherence/scripts/check_todo_format.py). The **render format** is how a sorted view is produced on demand; it reads the source and never rewrites it.

When asked for a sorted TODO view (e.g. `/todo`, "show TODO", "sort TODO by DAG", "what's open"), gather the open items from every `## TODO` section the resolver reaches and render them in the exact format below. No emojis — the `L0 > L1 > … > Ln` ordering is self-explanatory.

## Source schema

Open work is **federated by orthogonal concern**. A concern that owns a doc (`LABELS.md`, `VOTES.md`, `FEATURES.md`, a subsystem `DESIGN.md` / `SYSTEM.md`, …) co-locates its own work *with* that doc, so everything about labels — the design, the backlog, the schedule — lives in one home. Two co-located sections per concern:

- **`## TODO`** — the backlog for that concern: items in the item schema below.
- **`## PLAN`** — the dated / flightplan instantiation of some of those items: when they happen and in what order, referencing item ids. PLAN never introduces work that is not in a `## TODO`.

The repo-root `TODO.md` is the **one index**. It is a *resolver*: a routing table that links to each concern's `## TODO` (and `## PLAN`). It does not restate the items — that would be a second home that drifts. A repo with no orthogonal concerns is the degenerate case: `TODO.md` holds the items directly under its own `## TODO`. Either way `TODO.md` is where you start.

```markdown
# TODO

This is the index. Open work lives with its concern; this resolves to each.

## TODO
- Labels — [LABELS.md](LABELS.md#todo) · plan [LABELS.md](LABELS.md#plan)
- Votes — [VOTES.md](VOTES.md#todo) · plan [VOTES.md](VOTES.md#plan)
- Features — [FEATURES.md](FEATURES.md#todo)

## Completed
- 2026-05-12 — 1A vendored the racecar CLI helper (see [VOTES.md](VOTES.md))
```

And inside a concern doc, e.g. `LABELS.md`:

```markdown
## TODO

### 2B — Settlement schema discovery
- Prio: P0
- Depends: 1A, 1C
- Updated: 2026-05-28

What: validate the provisional APX CSV schemas against real downloads.
Why: wrong shape corrupts the cube.
Status: blocked on first real APX export.

## PLAN
- 2026-06 — 2B, then 1C once the export lands.
```

The **item schema** is invariant — it holds wherever an item lives (a concern's `## TODO`, or the degenerate root `## TODO`). Each rule is independently failable; this is what the checker enforces:

- Every item is an `### {id} — {title}` heading. The **id** is short and stable (`2B`, `1A`, `2B-dedup`); ids are unique within their file. The **title** is ≤ 8 words.
- Every item carries three fields as body lines, one per line:
  - `Prio:` — literally one of `P0`, `P1`, `P2`, `P3` (`P0` highest). This is the severity tag; map any older scheme (Major/Minor/Nit, CRITICAL/HIGH/LOW) onto it.
  - `Depends:` — comma-separated ids this item waits on, or `none`, or `LAST` (the render reserves `Ln` for `LAST`). The render derives DAG levels from this.
  - `Updated:` — an ISO date `YYYY-MM-DD`, the last time the item was touched. This is the freshness signal: a well-formed but stale entry is worse than an honest gap, so the date is mandatory and the reviewer treats an ancient date as a smell.
- Free-form body follows the three fields. `What:` / `Why:` / `Status:` lines are the recommended shape but not enforced.
- Inline code TODOs do not restate work; they point at the tracked item: `# TODO(2B): ...`.

A `## TODO` section that is a resolver (links, no `###` items) is valid — it routes rather than holds. Finished items move (not copy) to a `## Completed` section: per-concern, or centralized in the root `TODO.md`. Completed items need no `Prio` / `Depends` / `Updated`; a trailing ` — YYYY-MM-DD` completion date is the convention.

This federation is the [resolver pattern and one-home-per-rule](../doc-coherence/PROTOCOL.md#mental-models) applied to work tracking. A structured, checked `## TODO` / `## PLAN` section is sanctioned co-located structure, not the freeform scratchpad that [doc-coherence](../doc-coherence/PROTOCOL.md#mental-models) bans.

## Grouping

Group all open items by DAG level: `L0`, `L1`, `L2`, …, `Ln` (where `Ln` is reserved for items the user has explicitly designated "LAST"). Skip the `## Completed` section entirely — open items only.

## Level headers

Single-line header per non-empty level:

- `L0 — No internal deps, start anytime`
- `L1 — Depend on L0`
- `L2 — Depend on L1`
- (continue as needed; each level depends on the level above)
- `Ln — LAST` (explicitly-last items)

## Per-level table

Render a Unicode box-drawing table with these columns:

- **L0**: `Prio | Item | Why this tier`
- **L1+**: `Prio | Item | Depends on`

Use the characters `┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ─ │`. Do not use ASCII tables (`+---+`).

## Row ordering

Within each level, sort by priority `P0` → `P3` (highest first). Break ties on TODO id ascending (`1A < 1B < 2A`).

## Item cell

`{TODO-id} {short title, ≤8 words}`. If one TODO id has parts that live at different levels, split it with a stable suffix. Suffixes can be alphabetical (`2B-a`, `2B-b`) or semantic (`2B-qp`, `2B-dedup`, `2D-floors`, `2D-override`) — prefer semantic when the parts have distinct identities. Use the same suffix consistently across sessions.

## Priority labels

Values are literally `P0`, `P1`, `P2`, `P3` — nothing else. `P0` = highest within its level. `P3` = lowest / deferred.

## Sprint order footer

After all level tables, append a numbered list headed `Suggested sprint order:`. Reference items by `{TODO-id}` only — do not restate titles. One clause per step (today, next, parallel, background, defer).

## Do not

- Do not reformat, paraphrase, or rewrite the underlying `TODO.md` file itself. Just render.
- Do not include items from the `## Completed` section.
- Do not add prose before or after the output. Tables + sprint order are the entire response.
