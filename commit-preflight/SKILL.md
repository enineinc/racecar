---
name: racecar-commit-preflight
description: Dry-run the pre-commit hook suite against the staged set before committing — apply formatter autofixes (isort, black, whitespace) to a fixpoint and re-stage, then report green or the exact non-fixable blockers, so the real commit never fails mid-way. Never runs git commit. Use when asked to "preflight", "will this commit pass", "check the hooks first", "pre-commit dry run", or before any commit in a repo that has pre-commit hooks.
---

# racecar-commit-preflight

Make a commit green *before* attempting it, so you never burn a round trip on a hook that auto-fixes a file or rejects the change halfway. The mechanics are deterministic and live in [`scripts/commit_preflight.sh`](../scripts/commit_preflight.sh); this skill runs it and reads the result.

## Run it

    bash "$RACECAR_HOME/scripts/commit_preflight.sh"

(`$RACECAR_HOME` defaults to `~/.claude/skills/racecar`; from a racecar checkout, call `scripts/commit_preflight.sh` directly.) It operates on whatever is currently staged and changes no commits.

## What it does

1. Reads the staged file list (`--diff-filter=ACMR`).
2. Runs `pre-commit run` on the staged set.
3. If a hook auto-modified a staged file (isort/black/whitespace), re-stages exactly those files and retries, to a fixpoint (max 3 passes). It never stages files that were not already part of the commit.
4. If a run fails with no fixable change (doc-coherence, import-linter, tests), it stops and prints those findings verbatim.

## Read the result by exit code

- **0 green** — staged set passes; the owner may commit now (draft the message with [`racecar-commit`](../commit/SKILL.md)).
- **1 blocked** — non-fixable failures remain; the printed findings are what the commit would hit. Fix them, re-stage, run preflight again. Do not commit.
- **2 unmet** — nothing staged, or no repo / `pre-commit` / `.pre-commit-config.yaml`. Stage the commit's files first, or there is nothing to check.

## Boundaries

- Never runs `git commit` — the owner commits (per [`shared/OWNERSHIP.md`](../shared/OWNERSHIP.md)).
- Auto-fixes only formatting hooks; it never edits source to satisfy a logic/doc check — those are surfaced for a human decision.
- Assumes the staged files are not also dirty-unstaged (a half-staged file makes pre-commit's stash ambiguous). If they are, stage or stash the rest first.
- One commit at a time. To green a whole series, [`racecar-commit-decompose`](../commit-decompose/SKILL.md) calls this per group.
