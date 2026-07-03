#!/usr/bin/env python3
"""Prose-punctuation gate: no em-dashes (and no en-dash / `--` sentence dashes).

Enforces shared/VOICE.md "No em-dashes in prose. Use a comma, colon, parentheses,
or period." The same voice rule extends to the en-dash (U+2013) and to `--` used as
a sentence dash, the two common substitutes a writer reaches for once the em-dash is
gone. Punctuation is not code, so a fix is always a mechanical rewrite, never a
suppression.

Two invocations:

  - `--commit-msg <file>` scans a commit message. A commit message is always
    human-voiced, so it is scanned unconditionally.
  - Positional file arguments scan staged prose files: whole-file for Markdown,
    docstrings only for Python (code is not prose; a `--flag` in an argparse string
    is not a sentence dash).

Carve-out (VOICE.md): a genuinely machine-generated artifact (the CLAUDE.md router,
a generated brief, a manifest) is exempt. The exemption is inclusive, not a central
ignore-list: a file opts out by carrying the marker `racecar:prose-exempt` (in any
comment form). Generators emit it; a hand-authored file cannot silently inherit it.

Usage (invoked by pre-commit):
    python scripts/check_prose_punctuation.py --commit-msg <commit-msg-file>
    python scripts/check_prose_punctuation.py <file.md> [<file.py> ...]

Exit 0 when clean, 1 when any violation is found.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

EXEMPT_MARKER = "racecar:prose-exempt"

_EM_DASH = "—"
_EN_DASH = "–"
# `--` as a sentence dash: joined words (`word--word`) or spaced (` -- `). A CLI long
# option (` --flag`) has no trailing space after the dashes, and a Markdown rule / table
# separator (`---`, `-----`) has no adjacent word character, so neither is matched.
_DOUBLE_DASH_RE = re.compile(r"\w--\w| -- ")


def find_violations(text: str) -> list[tuple[int, str]]:
    """Return (1-based line number, description) for every prose-punctuation hit in text."""
    violations: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _EM_DASH in line:
            violations.append((lineno, "em-dash (U+2014); use a comma, colon, or period"))
        if _EN_DASH in line:
            violations.append((lineno, "en-dash (U+2013); use a hyphen or reword"))
        if _DOUBLE_DASH_RE.search(line):
            violations.append((lineno, "`--` used as a sentence dash; use a comma or period"))
    return violations


def _docstring_violations(source: str) -> list[tuple[int, str]]:
    """Return violations found only within the docstrings of a Python module."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc is None:
            continue
        base = node.body[0].value.lineno  # the docstring literal's start line
        for local_line, description in find_violations(doc):
            violations.append((base + local_line - 1, description))
    return violations


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return violations for one staged prose file, or [] when it is exempt or code."""
    text = path.read_text(encoding="utf-8")
    if EXEMPT_MARKER in text:
        return []
    if path.suffix == ".py":
        return _docstring_violations(text)
    return find_violations(text)


def _commit_message_prose(commit_msg_file: Path) -> str:
    """Return the commit message body with git comment lines and the scissors trailer removed."""
    lines: list[str] = []
    for line in commit_msg_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ------------------------ >8"):
            break
        if line.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """Scan a commit message or staged prose files; return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--commit-msg",
        type=Path,
        default=None,
        help="Scan a commit message file (always human-voiced).",
    )
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)

    total = 0
    if args.commit_msg is not None:
        for lineno, description in find_violations(_commit_message_prose(args.commit_msg)):
            print(f"commit message:{lineno}: {description}")
            total += 1
    for path in args.files:
        if not path.is_file():
            continue
        for lineno, description in check_file(path):
            print(f"{path}:{lineno}: {description}")
            total += 1
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
