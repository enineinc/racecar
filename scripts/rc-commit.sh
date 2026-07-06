#!/usr/bin/env bash
#
# rc-commit.sh — stage the named paths and open an editor-reviewed commit
# seeded from a drafted message file.
#
# racecar's rule is that the owner commits, not the agent (OWNERSHIP.md).
# This is the owner's tool: `git commit -e` forces the editor open every
# time, so nothing lands without passing under your eyes, even when the
# message was drafted for you. The `-F` seeds that editor from the file.
#
# Usage:
#   scripts/rc-commit.sh <message-file> [path ...]
#
#   With paths:    stages exactly those paths, then commits the staged set.
#   Without paths: commits whatever is already staged (stage it yourself first).
#
# Explicit by design: the message file is required, never inferred. To skip
# the editor (non-interactive), drop the `-e` on the last line; the default
# keeps it, for the control freak this is written for.

set -euo pipefail

usage() {
	echo "usage: $(basename "$0") <message-file> [path ...]" >&2
	exit 2
}

[ $# -ge 1 ] || usage
msgfile=$1
shift

[ -f "$msgfile" ] || {
	echo "rc-commit: message file not found: $msgfile" >&2
	exit 2
}

# Stage the named paths if any were given; otherwise use the current index.
if [ $# -gt 0 ]; then
	git add -- "$@"
fi

# Refuse an empty staging set rather than opening an editor for nothing.
if git diff --cached --quiet; then
	echo "rc-commit: nothing staged (pass paths, or stage first)" >&2
	exit 1
fi

# Editor-reviewed commit, seeded from the drafted message. `-e` is the point:
# you review and edit before it lands.
git commit -eF "$msgfile"
