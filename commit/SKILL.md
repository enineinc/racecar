---
name: racecar-commit
description: Draft conventional commit(s) from the working tree and decide the version bump deterministically. Inventories the whole tree, groups by concern, and DECOMPOSES BY DEFAULT — one coherent concern yields one commit, a mixed tree yields a dependency-ordered series, each drafted and version-checked the same way. Classifies type from the diff, maps type to semver bump per COMMITS.md, updates the single version home, and emits a runbook the owner runs (scripts/rc-commit.sh). Never runs git commit. Use for "write a commit message", "commit with version", "does this warrant a bump", "split this into commits", "break up these changes", "decompose the working tree", "how should I commit this", or any commit authoring, one change or many.
---

# racecar-commit

One pass from the working tree to a commit, or to a clean series of them, each with its version bump decided. Decomposition is not a separate skill: this inventories the whole tree and commits it as one when the tree tells one story, or as an ordered series when it tells several. The grouping is judgment; the ordering, the type-to-bump mapping, and the checks are mechanical. Conventions live in [`shared/COMMITS.md`](../shared/COMMITS.md) (format, type→bump table, valid increments, version home) and [`shared/OWNERSHIP.md`](../shared/OWNERSHIP.md) (the owner commits); this restates neither.

## Step 1: inventory the whole tree

    git status --short
    git diff --stat
    git diff --cached --stat

Account for every change: staged, unstaged, AND untracked. Untracked files are the ones most often forgotten. Set aside explicitly anything that should not be committed at all (secrets, local scratch, client-specific assets), naming it so it is a decision, not an omission.

## Step 2: group by concern, and count the groups

Cluster the changes into the smallest set of commits that each tell one story. Strong default seams:

- **Layer/feature**: a feature is its data model + migration + service + tests, one commit (or split if large).
- **Templates-only vs code**: a pure presentation/markup change is its own commit, separate from logic.
- **Docs and bookkeeping**: docs, PLAN/TODO updates ride together, apart from code.
- **Unrelated fixes**: a drive-by fix that rode along gets its own commit, never folded into a feature.

The group count decides the path, with no separate invocation:

- **Exactly one group** → a single commit. Go to Step 3 for it, skip Step 4, emit one block in Step 5.
- **More than one group** → a series. Surface the grouping as a table (commit → files → one-line intent), get the owner's read (grouping is theirs to correct), then run Steps 3-4 per group in the order Step 4 fixes.

## Step 3: classify type, decide bump, resolve the version home (per commit)

For the commit, or for each commit in the series:

**Classify the type.** Exactly one allowed type from COMMITS.md §Format. Breaking indicators: a removed or renamed public symbol, a changed CLI flag or contract, a changed output schema, or the user saying so. A diff that fits no conventional type is a stop-and-ask, not an invented type. In a series, classify each group by its own highest-impact change.

**Decide the bump.** Apply the COMMITS.md type→bump table, including the pre-1.0 rule. State it as a claim with evidence: "`feat` (new checker `check_x.py`) → minor: 0.7.0 → 0.8.0". `none` is valid and common; say "no bump warranted". One bump per commit; across a series at most one commit carries the bump (the highest-impact change), and it is the one that edits the version home.

**Resolve the version home** (only when a bump is due), per COMMITS.md §Version home:

- `[project].version` exists → that is the home.
- No `[project]` table anywhere → root `VERSION`.
- Both exist → report the PACKAGING.md §8 finding, propose deleting `VERSION`, do not proceed until the user picks.

Validate the increment against COMMITS.md §Valid version increments; refuse an invalid delta and name the intended one. With consent, edit the home; it stages with its own commit.

## Step 4: for a series, keep each commit standing alone

(only when Step 2 found more than one group)

**Flag straddling files.** A single file changed for two reasons cannot sit in two commits as-is. Resolve by feature-editing, not blind hunk-staging: rewrite the file to concern A, commit it in A's group, then restore concern B for its group (snapshot the full file first, `cp file /tmp/file.full`, so B is a faithful restore). Hunk-staging (`git add -p`) is acceptable only when the two concerns are additive and non-interleaved (frontmatter at the top plus a change far below, two separate router rows); when logic interleaves, feature-edit so each intermediate commit still imports.

**Order bottom-up and check forward-references.** Order so dependencies land before their users: data layer → infra → services → wiring → templates → docs. Then prove each commit alone:

- Builds/imports: would the project's import gate pass with only this commit applied? A commit importing a symbol a later commit introduces is mis-ordered; move the definition earlier or merge the two.
- Forward-references: a comment, citation, or link pointing at a file a later commit adds will trip whole-tree linters on a clean checkout even though the tip is consistent. Move the referenced artifact no later than its first mention, or record the gap as a knowing trade-off. Never claim "each commit is green" without this check.

## Step 5: draft the message(s) and emit the runbook (the owner commits)

Draft each message per COMMITS.md §Format. When the version home is in the commit, append the `Bump version to X.Y.Z.` body line (§Version bumps in commits). Do not reference internal identifiers (PKs, local paths) that mean nothing in the log.

Emit a runbook the owner runs, one block per commit in order, via [`scripts/rc-commit.sh`](../scripts/rc-commit.sh) — it stages the named paths and opens the editor (`git commit -e`) seeded from the drafted message, so the owner reviews before it lands:

    cat > <msgfile> <<'EOF'
    <drafted message>
    EOF
    scripts/rc-commit.sh <msgfile> <files for this commit>

Preflight each commit with [`racecar-commit-preflight`](../commit-preflight/SKILL.md) where the repo runs pre-commit hooks. Never run `git commit` — the owner commits (OWNERSHIP.md).

## Rewriting commits already made

When the series exists and must be re-cut (regroup, or scrub content that should never have landed):

- Make the content edits, then create one `git commit --fixup=<target-sha>` per target group, then fold them with a non-interactive autosquash: `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <base>` (base = parent of the earliest target).
- A message-only reword of a non-HEAD commit needs scripted editors: point `GIT_SEQUENCE_EDITOR` at a script that flips the target lines to `reword` (match by unique subject, not by sha-abbreviation), and `GIT_EDITOR` at a script that makes the textual edit.
- During a rebase, only `reword`/`edit` steps re-run pre-commit; if an intermediate commit trips a whole-tree linter on a forward-reference (Step 4), `SKIP=<hook-id>` for the message-only rebase is legitimate since no file content changes.

## Verify completeness (especially when scrubbing)

A scrub is done only when it is gone from every surface:

- Build the FULL term set including run-together and hyphen/underscore variants (`law-firm`, `law firm`, `LAWFIRM`, the product name) — a single regex like `law.firm` silently misses `LAWFIRM`.
- Grep the working tree, but ALSO grep **commit messages** (`git log <range> --format=%B`) and confirm no commit *adds* the offending file (`git log --follow -- <path>`). Content can be scrubbed from trees while the name survives in a message.
