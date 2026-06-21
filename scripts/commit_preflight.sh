#!/usr/bin/env bash
# racecar commit-preflight: dry-run the pre-commit suite against the STAGED
# set, auto-apply formatter fixes to a fixpoint and re-stage, then report
# whether the real commit will pass. Never runs git commit.
#
# The procedure that wraps this lives in commit-preflight/SKILL.md.
#
# Exit codes:
#   0  green   — staged set passes; safe to commit
#   1  blocked — non-fixable hook failures remain (commit would fail)
#   2  unmet   — nothing staged, or no git repo / pre-commit / config
#
# bash 3.2 compatible (no mapfile, no associative arrays).
set -uo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "preflight: not inside a git repository" >&2
    exit 2
}
cd "$root" || exit 2

# Put a project virtualenv on PATH if one exists, so pre-commit resolves
# whether or not the venv is activated (mirrors how the hooks themselves
# locate their tools).
venv=""
for d in .venv venv ../venv; do
    [ -d "$d" ] && venv="$d" && break
done
[ -n "$venv" ] && export PATH="$venv/bin:$PATH"

if ! command -v pre-commit >/dev/null 2>&1; then
    echo "preflight: pre-commit is not installed — nothing to dry-run" >&2
    exit 2
fi
if [ ! -f .pre-commit-config.yaml ]; then
    echo "preflight: no .pre-commit-config.yaml at repo root" >&2
    exit 2
fi

# Snapshot the staged file list (added/copied/modified/renamed). Autofixers
# touch the working tree; we only ever re-stage files that were already part
# of this commit, never unrelated working changes.
staged=()
while IFS= read -r f; do
    [ -n "$f" ] && staged+=("$f")
done < <(git diff --cached --name-only --diff-filter=ACMR)

if [ "${#staged[@]}" -eq 0 ]; then
    echo "preflight: nothing staged — stage this commit's files first" >&2
    exit 2
fi

max_passes=3
pass=1
while [ "$pass" -le "$max_passes" ]; do
    out=$(pre-commit run 2>&1)
    rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "preflight: green — safe to commit (${#staged[@]} file(s), ${pass} pass(es))"
        exit 0
    fi

    # Did any hook modify a staged file? If not, the failures are not
    # auto-fixable (doc-coherence, import-linter, tests) — real blockers.
    if git diff --quiet -- "${staged[@]}"; then
        echo "preflight: BLOCKED — not auto-fixable, the commit would fail:"
        echo "$out"
        exit 1
    fi

    # Formatter autofixes landed in the working tree; re-stage and retry.
    git add -- "${staged[@]}"
    echo "preflight: applied autofixes (pass ${pass}) and re-staged; retrying"
    pass=$((pass + 1))
done

out=$(pre-commit run 2>&1)
if [ "$?" -eq 0 ]; then
    echo "preflight: green — safe to commit (after ${max_passes} autofix passes)"
    exit 0
fi
echo "preflight: BLOCKED — still failing after ${max_passes} autofix passes:"
echo "$out"
exit 1
