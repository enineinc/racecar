#!/usr/bin/env python3
"""Consumer-side gate: a repo must not override racecar, it must fix racecar.

Two assertions, both expressing the one rule stated in upgrade/README.md and
upgrade/SKILL.md: "There is no `[tool.racecar.overrides]`; the Makefile fold absorbs
build customization structurally." A repo that dislikes a racecar default changes the
standard (an Escalate finding), it does not fork it locally.

  1. pyproject.toml carries no `[tool.racecar]` table (its `[tool.racecar.overrides]`
     form, or any other `[tool.racecar.*]` subtable). racecar has no such table by
     design; its presence is a local override registry, the second-home drift racecar
     fights.
  2. racecar.mk is byte-identical to the canonical `templates/classic/racecar.mk`.
     racecar.mk is the same file in every repo (it self-detects the shape at make-time),
     so any difference is a hand-edit of canon. Build customization belongs in the owned
     `Makefile`, never here.

Racecar-run-only, like check_config_drift.py: assertion 2 diffs against this checkout's
`templates/classic/`, so it runs from the racecar checkout against an adopter via --root
(the `RACECAR_ROOT` the vendored racecar.mk resolves from the installed skill symlink).
It is a no-op on racecar's own repo, which vendors neither a root racecar.mk nor a
`[tool.racecar]` table.

Usage:
    python scripts/check_racecar_overrides.py [--root <project>]

--root defaults to CWD (the project to inspect). Exit 0 when clean or not applicable,
1 on any override.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from check_config_drift import unified_template_diff

RACECAR_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_RACECAR_MK = RACECAR_ROOT / "templates" / "classic" / "racecar.mk"


def overrides_table(root: Path) -> bool:
    """True when the project's pyproject.toml declares a `[tool.racecar]` table."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return "racecar" in data.get("tool", {})


def racecar_mk_drift(root: Path) -> list[str]:
    """Return the diff of the project's racecar.mk against canon, or [] when in sync.

    Empty when the project has no racecar.mk (not vendored, or racecar's own repo).
    """
    vendored = root / "racecar.mk"
    if not vendored.is_file():
        return []
    return unified_template_diff(vendored, CANONICAL_RACECAR_MK)


def main(argv: list[str]) -> int:
    """Assert the project has not overridden racecar; return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()

    if not CANONICAL_RACECAR_MK.is_file():
        print(
            f"check_racecar_overrides: canonical template missing: {CANONICAL_RACECAR_MK}",
            file=sys.stderr,
        )
        return 2

    violations = 0
    if overrides_table(root):
        print(
            "  pyproject.toml declares a [tool.racecar] table; racecar has no override "
            "registry. Remove it and change the standard instead (fix racecar, do not "
            "override it). See upgrade/README.md.",
            file=sys.stderr,
        )
        violations += 1

    drift = racecar_mk_drift(root)
    if drift:
        print(
            "  racecar.mk differs from canon (a hand-edit of shape content). racecar.mk "
            "is identical in every repo; put customization in the owned Makefile and run "
            "`make sync` to restore canon:",
            file=sys.stderr,
        )
        for line in drift:
            print(f"    {line}", file=sys.stderr)
        violations += 1

    if violations:
        print("check_racecar_overrides: overrides found", file=sys.stderr)
        return 1
    print("check_racecar_overrides: OK (no racecar overrides)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
