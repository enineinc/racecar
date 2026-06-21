---
name: racecar-commit-decompose
description: Turn a working tree of mixed changes into a dependency-ordered series of coherent, individually-buildable commits — group by concern, flag single files that straddle two concerns for splitting, order bottom-up so each commit builds, detect forward-references, and emit a per-commit runbook that preflights then drafts each message via racecar-commit. Never runs git commit. Use when asked to "split this into commits", "break up these changes", "decompose the working tree", "how should I commit this", or when staging a large mixed diff.
---

# racecar-commit-decompose

One pass from a sprawling working tree to a clean commit series a reviewer can follow. The grouping is judgment; the ordering and the checks are mechanical. Pairs with [`racecar-commit-preflight`](../commit-preflight/SKILL.md) (greens each commit) and [`racecar-commit`](../commit/SKILL.md) (message + version per commit). Conventions live in [`shared/COMMITS.md`](../shared/COMMITS.md); this restates none of them.

## Step 1: inventory the whole tree

    git status --short
    git diff --stat
    git diff --cached --stat

Account for every change: staged, unstaged, AND untracked. Untracked files are the ones most often forgotten. Note anything that should NOT be committed at all (client-specific assets, secrets, local scratch) and set it aside explicitly — name it so it is a decision, not an omission.

## Step 2: group by concern (the judgment step)

Cluster files into the smallest set of commits that each tell one story. Strong default seams:

- **Layer/feature**: a feature is its data model + migration + service + tests, as one commit (or split if large).
- **Templates-only vs code**: a pure presentation/markup change is its own commit, separate from logic.
- **Docs and bookkeeping**: docs, PLAN/TODO updates ride together, apart from code.
- **Unrelated fixes**: a drive-by fix that rode along gets its own commit, never folded into a feature.

Surface the proposed grouping as a table (commit → files → one-line intent) and get the owner's read before proceeding. Grouping is theirs to correct.

## Step 3: flag files that straddle two concerns

A single file changed for two reasons cannot sit in two commits as-is. Detect these (e.g. one module that gained both a feature-A method and a feature-B import) and resolve by **feature-editing**, not blind hunk-staging:

- Rewrite the file to concern A only, commit it in A's group; then restore concern B and commit it in B's group. Snapshot the full version first (`cp file /tmp/file.full`) so B is a faithful restore.
- This keeps each intermediate commit importable. Hunk-staging (`git add -p`) can leave a syntactically valid but semantically half-wired file; prefer feature-editing when the two concerns interleave.

## Step 4: order bottom-up and check each commit stands alone

Order so dependencies land before their users — data layer → infra → services → view/wiring → templates → docs. Then prove each commit independently:

- **Builds/imports**: would `python manage.py check` (or the project's import gate) pass with only this commit applied? A commit whose code imports a symbol introduced in a *later* commit is mis-ordered — move the definition earlier or merge the two.
- **Forward-references**: a comment/docstring/citation pointing at a file added in a later commit will trip whole-tree linters on a clean checkout even though the tip is consistent. Either move the referenced artifact no later than its first mention, or record the gap as a knowing trade-off — never claim "each commit is green" without this check.

## Step 5: emit the runbook (the owner commits)

For each commit in order:

    git add <files for this commit>
    # then: racecar-commit-preflight  -> must be green
    # then: racecar-commit            -> draft message + version; owner commits

Never run `git commit` — the owner commits (per [`shared/OWNERSHIP.md`](../shared/OWNERSHIP.md)). Hand over the staged-add list per commit; let preflight green it and racecar-commit author it.

## Rewriting commits already made

When the series exists and must be re-cut (regroup, or scrub content that should never have landed):

- Make the content edits, then create one `git commit --fixup=<target-sha>` per target group, then fold them with a non-interactive autosquash: `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <base>` (base = parent of the earliest target).
- A message-only reword of a non-HEAD commit needs scripted editors: point `GIT_SEQUENCE_EDITOR` at a script that flips the target lines to `reword` (match by unique subject, not by sha-abbreviation), and `GIT_EDITOR` at a script that makes the textual edit.
- During a rebase, only `reword`/`edit` steps re-run pre-commit; if an intermediate commit trips a whole-tree linter on a forward-reference (Step 4), `SKIP=<hook-id>` for the message-only rebase is legitimate since no file content changes.

## Verify completeness (especially when scrubbing)

A scrub is done only when it is gone from every surface:

- Build the FULL term set including run-together and hyphen/underscore variants (`law-firm`, `law firm`, `LAWFIRM`, the product name) — a single regex like `law.firm` silently misses `LAWFIRM`.
- Grep the working tree, but ALSO grep **commit messages** (`git log <range> --format=%B`) and confirm no commit *adds* the offending file (`git log --follow -- <path>`). Content can be scrubbed from trees while the name survives in a message.
