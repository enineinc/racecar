#!/usr/bin/env bash
# PostToolUse hook for Claude Code: when a Read tool call targets
# `racecar/README.md` or `racecar/CLAUDE.md`, re-run `sync_claude_md.py` so
# the pointer in ~/.claude/CLAUDE.md stays aligned with this checkout.
#
# Claude Code passes the tool invocation as JSON on stdin. We extract
# `tool_input.file_path` and act only when it matches racecar/README.md or
# racecar/CLAUDE.md. Any other Read is ignored. Always exits 0 so the hook
# never blocks the tool call.
#
# Wire it from ~/.claude/settings.json — see racecar/README.md "Pointer sync".

set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sync_script="$script_dir/../scripts/sync_claude_md.py"

payload="$(cat)"

if command -v jq >/dev/null 2>&1; then
  file_path="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
else
  file_path="$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
fi

case "$file_path" in
  */racecar/README.md | */racecar/CLAUDE.md)
    python3 "$sync_script" >/dev/null 2>&1 || true
    ;;
esac

exit 0
