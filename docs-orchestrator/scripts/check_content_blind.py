#!/usr/bin/env python3
"""Content-blindness guard: no tracked file's prose may embed a real figure.

The reusable, frontmatter-parameterized generalization of seshat's
``tests/guards/test_content_blind.py`` (see
``docs-orchestrator/CONTENT_BLINDNESS.md`` for the one-home rule definition).
It implements the tier of that guard that GENERALIZES — the always-runs
STRUCTURAL rule that needs no private corpus:

    Formulae, worked examples and illustrations in PROSE must be written in
    VARIABLES, not numbers. A number that looks like a rate, price, notional,
    balance, threshold, share or capacity is a leak, even one the author
    believes they invented. Only content-blind structural constants (from the
    calendar or from arithmetic) may appear as literals.

The blocklist tier of seshat's guard (diff the private corpus against the
published tree) is inherently repo-specific — it needs the gitignored data —
and stays in the consuming repo. This checker is the tier every governed repo
can run identically, so it lives once in racecar.

Policy is read from the repo-root ``README.md`` YAML frontmatter, never
hardcoded here (CONTENT_BLINDNESS.md, "Declaration"):

    content_blind: true                    # opt in; absent/false => no-op
    content_blind_exempt:                  # paths exempt from the prose rule
      - tests/guards/test_content_blind.py
    content_blind_placeholders: [orion, draco]   # synthetic tokens (advisory)
    content_blind_structural: [7.0]        # extra structural constants (opt)

When ``content_blind`` is absent or false the check is a no-op (one info line,
exit 0): a repo that has not opted in has nothing to enforce.

Prose scanned:
  - Python: every comment and docstring line (never code — a test asserting
    ``approx(625.0)`` is doing its job; prose is where a formula gets
    "helpfully" illustrated with a real number).
  - Markdown: every line OUTSIDE a fenced code block (a fence is a config
    example, i.e. data).

Files scanned: what git would publish (tracked + new-and-not-ignored); on a
non-git tree, every text file under the root minus hidden dirs.

Output:
  - One line per finding: ``check_content_blind: <severity>: <message>``.
  - Summary: ``check_content_blind: OK`` (exit 0) or
    ``check_content_blind: N errors`` (exit 1).

Usage:
    python3 <path-to>/check_content_blind.py [--root <path>]
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import subprocess
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

TEXT_SUFFIXES = frozenset(
    {".py", ".md", ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini", ".txt"}
)

# Content-blind STRUCTURAL constants: from the calendar or from arithmetic,
# carrying no information about any deal. Everything else that LOOKS like a deal
# term is out. Mirrors seshat's STRUCTURAL set; a repo may extend it via
# `content_blind_structural` in frontmatter.
STRUCTURAL = frozenset({0.0, 1.0, 2.0, 12.0, 100.0, 360.0, 365.0, 1000.0})

COMMA_GROUPED = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")  # 22,000  12,345.67
UNDERSCORE_GROUPED = re.compile(r"\b\d+_\d{3}(?:_\d{3})*\b")  # 22_000
PRECISE_DECIMAL = re.compile(r"(?<![\d.])\d*\.\d{4,}(?![\d])")  # 0.0625  0.9394
LARGE_INTEGER = re.compile(r"(?<![\d.\w$§])\d{4,}(?:\.\d+)?(?![\d\w])")  # 22000


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


def read_frontmatter_block(text: str) -> str | None:
    """Return the raw YAML frontmatter block of a doc, or None if absent."""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    return m.group(1) if m else None


def parse_policy(frontmatter: str) -> dict[str, object]:
    """Parse the flat content-blind keys from a frontmatter block, stdlib-only.

    Handles exactly the shapes CONTENT_BLINDNESS.md declares: a boolean scalar
    (`content_blind: true`), an inline list (`key: [a, b]`), and a block list
    (`key:` then `  - item` lines). No general YAML dependency — this checker
    stays stdlib-only like its doc-coherence peers.
    """
    policy: dict[str, object] = {}
    keys = {
        "content_blind",
        "content_blind_exempt",
        "content_blind_placeholders",
        "content_blind_structural",
    }
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m or m.group(1) not in keys:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if key == "content_blind":
            policy[key] = rest.lower() in ("true", "yes", "on")
        elif rest.startswith("["):
            policy[key] = _parse_inline_list(rest)
        elif rest == "":
            items, i = _consume_block_list(lines, i + 1)
            policy[key] = items
            continue
        else:
            policy[key] = [rest]
        i += 1
    return policy


def _parse_inline_list(rest: str) -> list[str]:
    """Parse a `[a, b, c]` inline YAML list into a list of stripped strings."""
    inner = rest.strip().lstrip("[").rstrip("]")
    return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]


def _consume_block_list(lines: list[str], start: int) -> tuple[list[str], int]:
    """Consume `  - item` lines starting at `start`; return (items, next_index)."""
    items: list[str] = []
    i = start
    while i < len(lines):
        item = re.match(r"^\s*-\s+(.*)$", lines[i])
        if not item:
            break
        items.append(item.group(1).strip().strip("'\""))
        i += 1
    return items, i


def published_files(root: Path) -> list[Path]:
    """Every text file git would publish; fall back to an rglob on a non-git tree."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return _rglob_text(root)
    files = []
    for name in out.splitlines():
        if not name:
            continue
        path = root / name
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def _rglob_text(root: Path) -> list[Path]:
    """Every text file under `root`, skipping hidden directories."""
    files = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


# ---------------------------------------------------------------------------
# Prose extraction
# ---------------------------------------------------------------------------


def py_prose(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (lineno, text) for every comment and docstring line in a python file."""
    source = path.read_text(encoding="utf-8", errors="ignore")
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                yield token.start[0], token.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            doc = ast.get_docstring(node, clean=False)
            if doc and node.body:
                start = node.body[0].lineno
                for offset, line in enumerate(doc.splitlines()):
                    yield start + offset, line


def md_prose(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (lineno, text) for every markdown line OUTSIDE a fenced code block."""
    fenced = False
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
    ):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield lineno, line


def deal_figures_in(line: str, structural: frozenset[float]) -> list[str]:
    """Return the literals in `line` that look like a deal term, not a constant."""
    found = []
    for pattern in (COMMA_GROUPED, UNDERSCORE_GROUPED, PRECISE_DECIMAL, LARGE_INTEGER):
        for match in pattern.finditer(line):
            raw = match.group(0)
            try:
                value = float(raw.replace(",", "").replace("_", ""))
            except ValueError:
                continue
            if value in structural:
                continue
            # A year or an ISO month key: 1899 (Excel's serial epoch) to 2100.
            if value.is_integer() and 1899 <= value <= 2100:
                continue
            # A residual or a tolerance (1e-3 and below) is a measure of error.
            if abs(value) <= 1e-3:
                continue
            found.append(raw)
    return found


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
# Main
# ---------------------------------------------------------------------------


def load_policy(root: Path) -> dict[str, object]:
    """Read the content-blind policy from the repo-root README.md frontmatter."""
    readme = root / "README.md"
    if not readme.is_file():
        return {}
    block = read_frontmatter_block(readme.read_text(encoding="utf-8"))
    return parse_policy(block) if block else {}


def structural_set(policy: dict[str, object]) -> frozenset[float]:
    """Return STRUCTURAL extended by any `content_blind_structural` frontmatter."""
    extra = policy.get("content_blind_structural", [])
    values: set[float] = set(STRUCTURAL)
    if isinstance(extra, list):
        for item in extra:
            try:
                values.add(float(item))
            except (TypeError, ValueError):
                continue
    return frozenset(values)


def scan(root: Path, exempt: frozenset[str], structural: frozenset[float]) -> list[str]:
    """Return `rel:lineno: figure | line` for every deal-shaped figure in prose."""
    offenders: list[str] = []
    # This guard necessarily quotes the very shapes it forbids to explain them,
    # so it always exempts its own file (seshat's PROSE_EXEMPT_FILES pattern) —
    # otherwise it would flag itself once synced into a content-blind adopter.
    self_path = Path(__file__).resolve()
    for path in published_files(root):
        if path.resolve() == self_path:
            continue
        rel = path.relative_to(root).as_posix()
        if rel in exempt:
            continue
        if path.suffix == ".py":
            prose = py_prose(path)
        elif path.suffix == ".md":
            prose = md_prose(path)
        else:
            continue
        for lineno, line in prose:
            for figure in deal_figures_in(line, structural):
                offenders.append(f"{rel}:{lineno}: {figure}  |  {line.strip()[:80]}")
    return offenders


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the content-blind check."""
    parser = argparse.ArgumentParser(
        description="Assert no tracked file's prose embeds a real figure "
        "(content-blindness Tier 2)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root to scan. Default: discovered via .git walk-up from CWD.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the content-blind prose scan when opted in; return an exit code."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    root = args.root.resolve() if args.root else find_repo_root()
    f = Findings()

    policy = load_policy(root)
    if not policy.get("content_blind"):
        f.info(
            "content_blind not declared true in README.md frontmatter; "
            "nothing to enforce (see CONTENT_BLINDNESS.md)"
        )
        return emit(f)

    exempt_raw = policy.get("content_blind_exempt", [])
    exempt = frozenset(exempt_raw if isinstance(exempt_raw, list) else [])
    offenders = scan(root, exempt, structural_set(policy))
    for offender in offenders:
        f.error(f"deal-shaped figure in prose — {offender}")
    return emit(f)


def emit(f: Findings) -> int:
    """Print all findings and return 1 if any error was recorded, else 0."""
    for severity, msg in f.entries:
        print(f"check_content_blind: {severity}: {msg}")
    if f.error_count == 0:
        print("check_content_blind: OK")
        return 0
    print(
        f"check_content_blind: {f.error_count} errors. A formula or worked example "
        "in prose must be written in VARIABLES, not numbers (CONTENT_BLINDNESS.md)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
