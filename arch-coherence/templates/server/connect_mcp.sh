#!/usr/bin/env bash
# Register this project's MCP surface with Claude Code. Same script local and live -- only the
# --url changes when you deploy.
#
#   ./connect_mcp.sh                                  # local (http://mcp.localhost:__MCP_PORT__/mcp)
#   ./connect_mcp.sh --url https://mcp.<host>/mcp     # live
#   ./connect_mcp.sh --url https://... --client-id <id> --client-secret   # pre-registered client
#
# On first tool use Claude Code drives the OAuth itself: it discovers the Authorization Server
# from the surface's protected-resource metadata, self-registers via DCR (or uses
# --client-id/--secret if you pre-registered a confidential client), opens a browser for the
# WebAuthn login, receives an opaque bearer token, then calls tools. No token or secret is
# stored by this script.
set -euo pipefail

URL="http://mcp.localhost:__MCP_PORT__/mcp"   # local default; override with --url to deploy
NAME="__PKG__"
SCOPE="user"                                  # user = all your projects | local | project
CALLBACK_PORT=""                              # fixed OAuth callback port if the AS needs a pre-registered redirect URI
CLIENT_ID=""                                  # set to skip DCR and use a pre-registered confidential client
USE_CLIENT_SECRET=0                           # with --client-id, prompt for the secret (or MCP_CLIENT_SECRET env)

while [ $# -gt 0 ]; do
  case "$1" in
    --url)           URL="$2"; shift 2;;
    --name)          NAME="$2"; shift 2;;
    --scope)         SCOPE="$2"; shift 2;;
    --callback-port) CALLBACK_PORT="$2"; shift 2;;
    --client-id)     CLIENT_ID="$2"; shift 2;;
    --client-secret) USE_CLIENT_SECRET=1; shift;;
    -h|--help)       sed -n '2,14p' "$0"; exit 0;;
    *) echo "unknown arg: $1 (see --help)"; exit 2;;
  esac
done

command -v claude >/dev/null 2>&1 || { echo "ABORT: the 'claude' CLI is not on PATH"; exit 1; }

args=(--transport http --scope "$SCOPE")
[ -n "$CALLBACK_PORT" ] && args+=(--callback-port "$CALLBACK_PORT")
[ -n "$CLIENT_ID" ]     && args+=(--client-id "$CLIENT_ID")
[ "$USE_CLIENT_SECRET" = 1 ] && args+=(--client-secret)

# idempotent: drop any prior registration of this name, then add
claude mcp remove "$NAME" >/dev/null 2>&1 || true
claude mcp add "${args[@]}" "$NAME" "$URL"

echo
echo "registered MCP server '$NAME' -> $URL  (scope: $SCOPE)"
echo "verify:  claude mcp list"
echo "use:     open a Claude session and list/call a $NAME tool; complete the WebAuthn login when the browser opens."
