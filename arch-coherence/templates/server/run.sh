#!/usr/bin/env bash
# Local flight: two processes, one per surface (mirrors the two-vhost deploy).
# REST on :__API_PORT__ (project.settings.api), MCP on :__MCP_PORT__ (project.settings.mcp).
set -euo pipefail
cd "$(dirname "$0")"
DJANGO_SETTINGS_MODULE=project.settings.api uvicorn project.asgi:application \
    --host 127.0.0.1 --port __API_PORT__ "$@" &
api_pid=$!
DJANGO_SETTINGS_MODULE=project.settings.mcp uvicorn project.asgi:application \
    --host 127.0.0.1 --port __MCP_PORT__ "$@" &
mcp_pid=$!
trap 'kill $api_pid $mcp_pid 2>/dev/null' EXIT
wait
