#!/usr/bin/env python3
"""Mechanical check: a racecar repo owns the required repo-root doc spine.

The required-docs manifest has one home — ``docs-orchestrator/ORCHESTRATION.md``
("Required-docs manifest"). This script mechanizes the REPO-ROOT tier of it and
nothing else, so it composes with (never duplicates) the subsystem tier already
owned by ``doc-coherence/scripts/check_subsystem_docs.py``:

  - ``check_subsystem_docs.py`` — every MAJOR SUBSYSTEM in an import-linter
    layer owns README.md + CLAUDE.md.
  - ``check_required_docs.py`` (this file) — the REPO ROOT owns the three
    top-level docs a racecar repo always has, plus the README frontmatter that
    carries the doc-graph edge and the content-blindness policy.

Required at the repo root:
  1. ``README.md`` — exists, non-empty, opens with a YAML frontmatter block
     carrying a ``pnode`` key (the doc-graph root edge; DOC_GRAPH.md).
  2. ``CLAUDE.md`` — exists, non-empty, carries >= 1 ``## `` heading.
  3. ``docs/summary/<REPO>.md`` — the racecar-llm-summary brief (SPEC.md).
     ``<REPO>`` is the repo-root basename uppercased, ``[^A-Z0-9_-]`` -> ``-``.

Advisory (info, never an error, so a repo that has not opted in stays green):
  - README frontmatter declares no ``content_blind`` policy. The docs
    orchestrator asks once and writes it (CONTENT_BLINDNESS.md, "Declaration").

Configuration (optional, ``pyproject.toml``):

    [tool.racecar.required-docs]
    brief = false          # this repo publishes no llm-summary brief

Output:
  - One line per finding: ``check_required_docs: <severity>: <message>``.
  - Summary: ``check_required_docs: OK`` (exit 0) or
    ``check_required_docs: N errors`` (exit 1). Info notes do not fail.

Usage:
    python3 <path-to>/check_required_docs.py [--root <path>]
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def find_repo_root(start: Path | None = None) -> Path:
    """Return the nearest ancestor of `start` (default CWD) containing `.git`."""
    start = start or Path.cwd()
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    return start


def repo_slug_upper(repo_root: Path) -> str:
    """Return the brief basename: the repo-root name uppercased, non-word -> `-`."""
    base = repo_root.name.lower()
    return re.sub(r"[^a-z0-9_-]", "-", base).upper()


def load_pyproject(repo_root: Path) -> dict:
    """Parse the repo-root pyproject.toml (the library pyproject in every shape)."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        return {}
    try:
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}


def brief_required(pyproject: dict) -> bool:
    """Whether the llm-summary brief is required (default True; opt out in config)."""
    cfg = pyproject.get("tool", {}).get("racecar", {}).get("required-docs", {})
    return cfg.get("brief", True) is not False


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def frontmatter_keys(text: str) -> set[str] | None:
    """Return the top-level frontmatter key names, or None if there is no block."""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    keys: set[str] = set()
    for line in m.group(1).splitlines():
        key = re.match(r"^([A-Za-z_][\w-]*):", line)
        if key:
            keys.add(key.group(1))
    return keys


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


class Findings:
    """Accumulator for severity-tagged findings (errors and info notes)."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []

    def error(self, msg: str) -> None:
        """Record an error-severity finding."""
        self.entries.append(("error", msg))

    def info(self, msg: str) -> None:
        """Record an info-severity note."""
        self.entries.append(("info", msg))

    @property
    def error_count(self) -> int:
        """Number of error-severity findings recorded."""
        return sum(1 for sev, _ in self.entries if sev == "error")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_readme(repo_root: Path, f: Findings) -> None:
    """Verify the root README exists with frontmatter, and note the CB policy."""
    readme = repo_root / "README.md"
    if not readme.is_file():
        f.error("missing: README.md (the human storefront and doc-graph root)")
        return
    text = readme.read_text(encoding="utf-8")
    if not text.strip():
        f.error("empty: README.md")
        return
    keys = frontmatter_keys(text)
    if keys is None:
        f.error(
            "README.md has no YAML frontmatter block (expected a `pnode` key; "
            "see doc-coherence/DOC_GRAPH.md)"
        )
        return
    if "pnode" not in keys:
        f.error("README.md frontmatter is missing the `pnode` key (DOC_GRAPH.md)")
    if "content_blind" not in keys:
        f.info(
            "README.md declares no `content_blind` policy; the docs orchestrator "
            "asks once and writes it (see docs-orchestrator/CONTENT_BLINDNESS.md)"
        )


def check_claude(repo_root: Path, f: Findings) -> None:
    """Verify the root CLAUDE.md exists, is non-empty, and has an H2 heading."""
    claude = repo_root / "CLAUDE.md"
    if not claude.is_file():
        f.error("missing: CLAUDE.md (the agent baseline / resolver)")
        return
    text = claude.read_text(encoding="utf-8")
    if not text.strip():
        f.error("empty: CLAUDE.md")
    elif not H2_RE.search(text):
        f.error("no H2 heading: CLAUDE.md")


def check_brief(repo_root: Path, pyproject: dict, f: Findings) -> None:
    """Verify the llm-summary brief exists at docs/summary/<REPO>.md when required."""
    if not brief_required(pyproject):
        f.info("llm-summary brief opted out via [tool.racecar.required-docs].brief")
        return
    brief = repo_root / "docs" / "summary" / f"{repo_slug_upper(repo_root)}.md"
    if not brief.is_file():
        f.error(
            f"missing: {brief.relative_to(repo_root).as_posix()} "
            "(the racecar-llm-summary brief; run /racecar-llm-summary)"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the required-docs check."""
    parser = argparse.ArgumentParser(
        description="Check the repo root owns README + CLAUDE + the llm-summary brief."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root to scan. Default: discovered via .git walk-up from CWD.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Verify the repo-root doc spine; return an exit code."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    repo_root = args.root.resolve() if args.root else find_repo_root()
    pyproject = load_pyproject(repo_root)

    f = Findings()
    check_readme(repo_root, f)
    check_claude(repo_root, f)
    check_brief(repo_root, pyproject, f)
    f.info(
        "subsystem README/CLAUDE coverage is check_subsystem_docs.py's; "
        "run it too (the orchestrator does)"
    )
    return emit(f)


def emit(f: Findings) -> int:
    """Print all findings and return 1 if any error was recorded, else 0."""
    for severity, msg in f.entries:
        print(f"check_required_docs: {severity}: {msg}")
    if f.error_count == 0:
        print("check_required_docs: OK")
        return 0
    print(f"check_required_docs: {f.error_count} errors")
    return 1


if __name__ == "__main__":
    sys.exit(main())
