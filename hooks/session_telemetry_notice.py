#!/usr/bin/env python3
"""SessionStart hook — disclose the telemetry state every time Claude starts in a racecar repo.

racecar's telemetry is on by default (opt-out). That is only good citizenship if it is never
silent: this hook makes the state impossible to miss. On every session entry in a racecar-
governed repo it prints one line — whether build, share, and usage telemetry are on or off —
and names the two toggles that turn them off. Consent by disclosure, not by opt-in.

  * build — record gate outcomes locally (`.telemetry/build.jsonl`).
  * share — let the anonymized aggregate leave the machine (the deferred push).
  * usage — record per-command resource cost (`.telemetry/usage.jsonl`).

The switch resolution is reused from `record_gate.py` (one home): env > the per-developer
`.telemetry/settings.toml` (what the toggles write) > pyproject `[tool.racecar.telemetry]` >
on. No-ops silently outside a racecar repo. Emits on session entry only (startup/resume); on
mid-session clear/compact the state is unchanged, so re-announcing would be noise. Pure stdlib.

Wired by sync_claude_md.py on the SessionStart matchers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RACECAR_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACECAR_ROOT / "scripts"))
# Reuse record_gate's switch resolver so there is one home for env > settings > pyproject > on;
# the hook lives outside scripts/ and reaches its sibling at runtime (pylint can't model it).
from record_gate import _switch  # noqa: E402 # pylint: disable=wrong-import-position,import-error


def _governed(root: Path) -> bool:
    """A repo where racecar telemetry can be produced: an adopter, or racecar itself."""
    if (root / "scripts" / "check_packaging.py").is_file():
        return True  # adopter (the canonical synced marker)
    if (root / "scripts" / "record_gate.py").is_file():
        return True  # adopter with the build producer delivered
    return root.resolve() == RACECAR_ROOT.resolve()


def _project_root(start: Path) -> Path:
    for base in (start, *start.parents):
        if (base / ".git").exists():
            return base
    return start


def _state(env_name: str, cfg_key: str) -> str:
    return "ON" if _switch(env_name, cfg_key) else "OFF"


def main() -> int:
    """Emit the telemetry disclosure line (the SessionStart entry point)."""
    raw = sys.stdin.read()
    try:
        source = (json.loads(raw) if raw.strip() else {}).get("source", "")
    except json.JSONDecodeError:
        source = ""
    if source in ("clear", "compact"):
        return 0  # mid-session: state unchanged, stay quiet

    root = _project_root(Path.cwd())
    if not _governed(root):
        return 0

    build = _state("RACECAR_BUILD_TELEMETRY", "build")
    share = _state("RACECAR_SHARE_TELEMETRY", "share")
    usage = _state("RACECAR_USAGE_TELEMETRY", "usage")
    line = (
        f"racecar telemetry: build={build} share={share} usage={usage} · "
        f"toggle /racecar-telemetry-build off | /racecar-telemetry-share off"
    )
    print(json.dumps({"systemMessage": line}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
