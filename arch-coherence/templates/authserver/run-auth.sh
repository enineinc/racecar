#!/usr/bin/env bash
# Local flight: the Authorization Server process (project.settings.auth) on :__PORT__.
# Run beside run.sh (the two surface processes); the AS is the only stateful one.
set -euo pipefail
cd "$(dirname "$0")"
DJANGO_SETTINGS_MODULE=project.settings.auth uvicorn project.asgi:application \
    --host 127.0.0.1 --port __PORT__ "$@"
