---
pnode: [README.md]
---

# Content-blindness — the contract

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

This is the one home for the content-blindness rule. A repo declares the *policy* in its `README.md` frontmatter and points here for the *definition*; the definition is never restated in each repo (one home per rule, [`../shared/PRINCIPLES.md`](../shared/PRINCIPLES.md) P-02). The discipline originated in the seshat repo, whose `tests/guards/test_content_blind.py` motivated it; this page generalizes it into a racecar-owned contract every governed repo can adopt.

## The rule

A repo published *content-blind* is published from a fresh history where a leak, once pushed, is permanent. The rule is absolute:

> No tracked file (code, docs, config, or tests) may name a real project, deal, model, or counterparty, or embed a real figure or a real workbook filename. Real names and numbers live only in gitignored paths; only synthetic placeholders appear in tracked files.

The leak is usually the *number*, not the name. A real strike in a test fixture, a real draw in a docstring, a real runoff in a worked example: each is invisible to lint, to types, and to every other test, and each author believed they were complying because they were checking for names. So the enforceable core of the rule is structural:

> Formulae, worked examples, and illustrations in PROSE are written in VARIABLES, not numbers. A number that reads like a rate, price, notional, balance, threshold, share, or capacity is out, even one you believe you invented. Only content-blind structural constants (from the calendar or from arithmetic) may appear as literals.

```
NOT:  balance(2028) = 24,000              YES:  balance(y) = premium_total * (tenor - elapsed) / tenor
NOT:  fee = 0.0625 * 200                  YES:  fee(m) = rate_kw_mo * volume_mw
```

A formula written in its class's own field names cannot carry a figure at all. That is why the fix is never to pick a safer number; it is to remove the number.

## Declaration — the machine-checkable policy in README frontmatter

The policy, and only the policy, lives in the repo-root `README.md` YAML frontmatter. It is a small, machine-readable set of keys added ALONGSIDE the existing `pnode` edge (never replacing it):

```yaml
---
pnode: []
content_blind: true                 # opt in; absent or false => the guard is a no-op
content_blind_exempt:               # tracked paths exempt from the prose rule
  - tests/guards/test_content_blind.py
content_blind_placeholders:         # the synthetic tokens that stand in for real names
  - orion
  - draco
content_blind_structural:           # optional: extra structural constants this repo allows
  - 7.0
---
```

- `content_blind` (bool) is the whole switch, and it is **off by default**: absent or `false`, a repo has not opted in and the guard enforces nothing. The discipline was generalized from a confidential-financial repo; defaulting it on across every domain over-fires on the legitimate figures many carry, so enabling it is a deliberate per-repo choice. Turning it on is a one-line change — set `content_blind: true` here — and needs no other edit: `check_content_blind.py` is already run by `make check` and the `content-blind` pre-commit hook ships in the classic template, so no `pyproject.toml` or `Makefile` change is required.
- `content_blind_exempt` lists the files that must talk *about* the boundary (the guard's own test, a `.gitignore`) and so are exempt from the prose rule, never from the intent.
- `content_blind_placeholders` records the invented tokens (e.g. `orion`, `draco`) that legitimately appear where a real name would leak. Advisory: it documents what the synthetic set is so a reviewer and the generators know which names are safe.
- `content_blind_structural` optionally extends the built-in structural set — which already exempts calendar values (years, `YYYYMM`/`YYYYMMDD` date keys) and tolerances — with a repo's own legitimate constants: config magic numbers a domain carries in prose (ports, TTLs, byte sizes, chunk counts) that are not deal terms. This is how an opted-in non-financial repo silences over-fires without exempting whole files.

The human *definition* of the rule is not duplicated into each README; the frontmatter carries the policy and the README points here. The docs orchestrator asks once whether a repo is content-blind when the key is absent, writes the answer, and thereafter reads it ([`ORCHESTRATION.md`](ORCHESTRATION.md), "Invocation").

## The reusable guard

[`scripts/check_content_blind.py`](scripts/check_content_blind.py) is the racecar-owned generalization of seshat's Tier-2 structural test, parameterized entirely by the frontmatter policy. It reads `content_blind` from `README.md`; off by default, it is a no-op until a repo opts in with `content_blind: true`. When enabled it scans the prose of every file git would publish (Python comments and docstrings, markdown outside fenced blocks) for deal-shaped figures, honoring `content_blind_exempt`, the structural allowlist, and the racecar-delivered files it never scans (below). It needs no private data, so it runs identically on a fresh clone and on the owner's machine.

racecar's own delivered files are never scanned. `sync_scripts.py` records what it delivered in `scripts/racecar-manifest.txt`, and the guard exempts exactly that set: those files are tooling the repo owns no prose in and cannot edit without the next sync clobbering it, so a figure-shaped comment in canon must never turn a downstream repo's gate red. racecar does not touch the repo's owned README to record this (that would break the no-clobber contract) — the manifest is a delivered artifact, rewritten on every sync, so the exemption stays current.

What it deliberately does NOT generalize: seshat's *blocklist* tier, which diffs the gitignored private corpus against the published tree to catch a specific leaked figure. That tier is inherently repo-specific (it needs the private data), so it stays in the consuming repo. The structural tier is the one that generalizes, and it is the tier that matters, because it removes the leak class by construction instead of relying on a writer's judgment about whether a given number is safe.

## Content-blind-aware generation

"Apply" the contract means two things, and the guard above is only the first:

1. **The guard** (above): any governed repo runs `check_content_blind.py`, parameterized by its own frontmatter policy.
2. **Content-blind-aware generators.** When `content_blind: true`, the generation stage emits structure and placeholders only, never a real name or figure. The llm-summary brief and the CLI / REST / MCP surface docs are driven to produce the shape of the system (entity names, endpoint paths, cardinalities) with synthetic tokens standing in for anything private. The mechanical guarantee is the gate: `check_content_blind.py` runs immediately after generation in the [orchestration sequence](ORCHESTRATION.md), so a generator that emitted a real figure fails the pipeline and the output cannot ship. The gate is what makes "refuse to emit real figures" enforced rather than professed ([`../shared/PRINCIPLES.md`](../shared/PRINCIPLES.md) R-02).

## Voice

Common voice: [`../shared/VOICE.md`](../shared/VOICE.md).
