#!/usr/bin/env python3
"""Report how a project's Makefile / .pre-commit-config.yaml drift from base.

The mechanical floor for `/racecar-upgrade` (see upgrade/README.md, Procedure
step 1): it finds *where* a consuming project's config differs from the current
`templates/classic/` base, so the divergence can be classified Conform / Declare /
Escalate. It does not judge and it does not clobber; it only shows the differing
lines. Run from the racecar checkout against an adopter via --root; it is not
synced to adopters (it needs templates/classic/ to diff against).

Why Python and not a shell drift check: a drift check is a file->base map, which
in bash means an associative array (`declare -A`), which is a bash 4 feature that
macOS bash 3.2 does not support. In Python the map is a free, portable dict, and
this matches racecar's "checks are stdlib Python" doctrine. Pure stdlib
(difflib + pathlib + re); runs anywhere python3 does.

Nuance (so it does not cry wolf): the Makefile's per-project SHAPE VARIABLES
(SRC / PKG / DJAPP / LIB_PYPROJECT / DJAPP_PYPROJECT) are *intended* to differ by
project, set by init_project per shape. Their assignment lines are normalized to a
placeholder before diffing, so a project's legitimate shape config is not reported
as drift. Everything else that differs is real divergence.

Usage:
    python scripts/check_config_drift.py [--root <project>] [--strict]

--root defaults to CWD (the project to inspect). The base is this racecar
checkout's templates/classic/. Exit 0 always (advisory) unless --strict and drift
was found.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

RACECAR_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = RACECAR_ROOT / "templates" / "classic"

# (project-relative path, template filename). The map racecar would have written
# with `declare -A` in bash; here it is a plain list of pairs, portable everywhere.
PAIRS = (
    ("Makefile", "Makefile"),
    (".pre-commit-config.yaml", "pre-commit-config.yaml"),
)

# Makefile assignment lines whose right-hand side is intended per-project config,
# not drift. Normalized before diffing so they never show up as divergence.
SHAPE_VARS = ("SRC", "PKG", "DJAPP", "LIB_PYPROJECT", "DJAPP_PYPROJECT")
_SHAPE_RE = re.compile(rf"^\s*({'|'.join(SHAPE_VARS)})\s*[?:!]?=")


def _normalize(text: str) -> list[str]:
    """Lines with per-project shape-variable values collapsed to a placeholder."""
    out: list[str] = []
    for line in text.splitlines():
        m = _SHAPE_RE.match(line)
        if m:
            out.append(f"{m.group(1)} ?= <project shape value>")
        else:
            out.append(line)
    return out


def _drift(project_file: Path, template_file: Path) -> list[str]:
    """Unified diff (base -> project) over normalized lines, or [] if in sync."""
    base = _normalize(template_file.read_text(encoding="utf-8"))
    proj = _normalize(project_file.read_text(encoding="utf-8"))
    diff = list(
        difflib.unified_diff(
            base, proj, fromfile="base", tofile="project", lineterm=""
        )
    )
    return diff


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true", help="exit 1 if any drift")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()

    any_drift = False
    for rel, template_name in PAIRS:
        project_file = root / rel
        template_file = TEMPLATES / template_name
        if not template_file.is_file():
            print(f"check_config_drift: base missing: {template_file}", file=sys.stderr)
            continue
        if not project_file.is_file():
            print(f"  {rel}: absent in project (base ships one; add or declare why)")
            any_drift = True
            continue
        diff = _drift(project_file, template_file)
        if not diff:
            print(f"  {rel}: in sync with base")
            continue
        any_drift = True
        print(f"  {rel}: drifts from base (classify each: Conform / Declare / Escalate)")
        for line in diff:
            print(f"    {line}")

    if not any_drift:
        print("check_config_drift: OK (no Makefile / pre-commit drift)")
        return 0
    print(
        "check_config_drift: drift found (advisory). Conform real drift to base, "
        "Declare intentional divergence in [tool.racecar.overrides], or Escalate a "
        "racecar defect. See upgrade/README.md."
    )
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
