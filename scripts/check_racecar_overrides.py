#!/usr/bin/env python3
"""Consumer-side gate: a repo must not override racecar, it must fix racecar.

Two assertions, both expressing the one rule stated in upgrade/README.md and
upgrade/SKILL.md: "There is no `[tool.racecar.overrides]`; the Makefile fold absorbs
build customization structurally." A repo that dislikes a racecar default changes the
standard (an Escalate finding), it does not fork it locally.

  1. pyproject.toml declares no non-canon `[tool.racecar]` key. The only legitimate
     `[tool.racecar.*]` tables are the input bindings racecar's own checkers read:
     `surface` (scaffold_surfaces), `roles` (check_surface_orchestration), and
     `subsystem-docs` (check_subsystem_docs). Any other key, notably the
     `[tool.racecar.overrides]` registry, is a local override, the second-home drift
     racecar fights. A new binding is added to this allow-list in racecar, never
     smuggled into a consumer's config.
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

# The only legitimate `[tool.racecar.*]` subtables: input bindings racecar's own checkers
# read. Everything else under `[tool.racecar]` (notably `overrides`) is a local override.
ALLOWED_RACECAR_KEYS = frozenset({"surface", "roles", "subsystem-docs"})


def disallowed_racecar_keys(root: Path) -> list[str]:
    """Return the non-canon `[tool.racecar.*]` keys a project declares, sorted.

    Empty when the project declares only canon bindings (ALLOWED_RACECAR_KEYS) or no
    `[tool.racecar]` table at all. Any other key is a local override, the drift this
    gate catches.
    """
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return []
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    racecar = data.get("tool", {}).get("racecar", {})
    if not isinstance(racecar, dict):
        return ["<non-table [tool.racecar]>"]
    return sorted(key for key in racecar if key not in ALLOWED_RACECAR_KEYS)


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
    extra_keys = disallowed_racecar_keys(root)
    if extra_keys:
        print(
            "  pyproject.toml declares non-canon [tool.racecar] key(s): "
            f"{', '.join(extra_keys)}. The only [tool.racecar] tables are the surface / "
            "roles / subsystem-docs bindings racecar's checkers read; racecar has no "
            "override registry. Remove the extra key and change the standard instead "
            "(fix racecar, do not override it). See upgrade/README.md.",
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
