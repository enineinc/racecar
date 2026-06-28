---
name: racecar-commit
description: Draft a conventional commit from staged changes and decide the version bump deterministically — classify the type from the diff, map type to semver bump per COMMITS.md, update the single version home (pyproject [project].version, or VERSION where no [project] table exists), and present the message. Never runs git commit. Use when asked to "write a commit message", "commit with version", "does this warrant a bump", "stage and write commit", "assess version bump", or any phrasing combining commit authoring with versioning.
---

# racecar-commit

One pass from staged diff to commit message plus version bump. The rules live in [`shared/COMMITS.md`](../shared/COMMITS.md) (format, type→bump table, valid increments, version home) — this skill is the procedure that applies them; it restates nothing.

## Step 1: inspect the staged diff

    git status
    git diff --cached

If nothing is staged: summarize what `git diff` shows as unstaged, then stop. Stage files only when the user explicitly asks, and confirm the file list before running `git add`.

## Step 2: classify the commit type

Classify the staged diff into exactly one allowed type from COMMITS.md §Format. Breaking indicators: a removed or renamed public symbol, a changed CLI flag or contract, a changed output schema, or the user saying so. A diff that fits no conventional type is a stop-and-ask, not an invented type.

If the diff mixes unrelated concerns, say so and propose a split into separate commits. If the user wants one commit anyway, classify by the highest-impact change (COMMITS.md §Bump from commit type).

## Step 3: decide the bump

Apply the COMMITS.md type→bump table, including the pre-1.0 rule. State the decision as a claim with the evidence line: "`feat` (new checker `check_x.py`) → minor: 0.7.0 → 0.8.0". A `none` bump is a valid and common outcome — say "no bump warranted" and skip to Step 6.

## Step 4: resolve the version home

Per COMMITS.md §Version home. Locate the library pyproject by shape (`pyproject.toml` at root, or `src/pyproject.toml`):

- `[project].version` exists → that is the home.
- No `[project]` table anywhere → root `VERSION` is the home.
- Both `[project].version` and a `VERSION` file exist → report the PACKAGING.md §8 finding and propose deleting `VERSION`. Do not sync the two. Do not proceed with the bump until the user picks.

Report which home was resolved and the current version.

## Step 5: apply the bump

Validate the proposed increment against COMMITS.md §Valid version increments; an invalid delta is refused with the intended valid bump named. With the user's consent, edit the version home and ask before staging it (`git add <home>`).

## Step 6: draft the message

Per COMMITS.md §Format. When the version home is in the diff, append the `Bump version to X.Y.Z.` body line per §Version bumps in commits. Do not reference internal identifiers (PKs, local paths) that mean nothing in the log.

Present the message for approval. Never run `git commit` — the owner commits.
