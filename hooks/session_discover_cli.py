#!/usr/bin/env python3
"""SessionStart hook — inject a JSON snapshot of the repo's CLI surface.

A fresh Claude session walks into a repo and doesn't know what CLI entry
points exist. Without this hook, agents (and humans new to the repo)
re-discover composed `python -m <pkg>` commands by trial and error. With
it, an authoritative tree is one screen of pre-loaded context away.

Delegates auditing AND enrichment to arch-coherence/scripts/check_cli_commands.py
— that script is the single source of CLI-surface truth, and its
`--json` output is the canonical *enriched* tree (raw audit fields plus
resolved `command`/`role`/`description`). This hook is a downstream
consumer: it reads the enriched tree and applies its own SUMMARIZATION
(drop kind, drop pattern-N codes, drop audit noise that the agent
doesn't need to use the surface) before injecting into context. The
script enriches; the hook summarizes. Other consumers (doc generators,
CI scripts) read the same enriched tree and apply their own summary.

  1. Finds the repo root by walking up from CWD until a `.git` entry.
  2. Discovers CLI roots by scanning the filesystem — every direct-child
     directory of `<repo>/` and `<repo>/src/` that has both
     `__init__.py` and `__main__.py` is a candidate. This deliberately
     ignores `pyproject.toml`'s `[project].name`: distribution name and
     import name routinely differ (e.g. dist `gfem-workspace`, import
     `gfem`), and a single repo can host multiple CLI roots
     (monorepo / workspace layouts).
  3. Picks an interpreter — in-tree `.venv` preferred, falling back to
     `sys.executable` — that can run check_cli_commands.py.
  4. For each discovered root, invokes
     `check_cli_commands.py --json <path>` from the repo root and parses
     stdout. The script returns the enriched audit tree — every node
     already carries the resolved `command`/`role`/`description` fields
     alongside the raw audit affordances.
  5. Applies a local SUMMARIZATION pass (`_summarize`) that strips audit
     noise the SessionStart agent doesn't need: drops `kind`, raw
     `pattern-N` codes, raw `commands` tuples, the always-present
     boolean `orphan` when false, empty `violations`, empty `children`.
     Renames `role` → `pattern` and `children` → `subcommands` so the
     in-context JSON reads as a command surface, not an audit tree.
  6. Emits one SessionStart envelope with the summarized roots collected
     into a single `{"roots": [<summary>, ...]}` object as
     additionalContext.

Silent no-op when any prerequisite is missing: no repo root, no usable
interpreter, no CLI roots discovered, check_cli_commands.py missing, or
every audit failed to produce JSON. Any unexpected exception is
swallowed and the hook returns 0 — SessionStart hooks must never be the
reason a session fails to start.

Opt-out: if `<repo_root>/.claude/cli-discovery.disabled` exists, emits a
one-line systemMessage and no additionalContext.

Wired by sync_claude_md.py on four SessionStart matchers — startup,
resume, clear, compact — so the snapshot is re-injected after `/clear`
and after auto-compaction as well, mirroring session_load_standards.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

RACECAR_ROOT = Path(__file__).resolve().parent.parent
AUDIT_SCRIPT = RACECAR_ROOT / "arch-coherence" / "scripts" / "check_cli_commands.py"


def _find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _discover_cli_roots(repo_root: Path) -> list[Path]:
    """Find direct-child Python packages that look like CLI surfaces.

    A CLI root is a directory containing BOTH `__init__.py` and
    `__main__.py`. Scanned locations:

      - `<repo>/` (flat layout, e.g. `repo/gfem/__main__.py`)
      - `<repo>/src/` (src layout, e.g. `repo/src/gfem/__main__.py`)

    Names beginning with `.` or `_` are skipped (build/cache/private).
    Sorted, deduplicated by package name across the two bases.
    """
    found: dict[str, Path] = {}
    for base in (repo_root, repo_root / "src"):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            if (child / "__init__.py").is_file() and (child / "__main__.py").is_file():
                found.setdefault(child.name, child)
    return [found[name] for name in sorted(found)]


def _resolve_python(repo_root: Path) -> Path | None:
    for candidate in (
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "bin" / "python3",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    fallback = Path(sys.executable)
    return fallback if fallback.is_file() else None


def _slim_arg(arg: dict[str, Any]) -> dict[str, Any]:
    """Trim an enriched argparse arg entry to the slim agent-facing shape.

    Drops fields an agent doesn't need to *invoke* the CLI:
      - `dest` (Python variable name; agent doesn't write Python)
      - `type: "str"` (implicit — argparse defaults to string)
      - `type: "bool"` + `action: "store_true"` (collapse — the flag's
        presence/absence IS the value)
      - `default: false` paired with store_true (implicit)
      - `default: null` (always implicit)
    Collapses `flags: ["--foo"]` (length 1) into `flag: "--foo"` to save
    a level of nesting on the common case.

    Mutex groups (`{"oneOf": [...]}`) are recursed into and preserved as
    JSON-Schema-style oneOf entries; the agent reads them as "pick at
    most one (or exactly one when `required: true`)."
    """
    # Mutex group: recurse and preserve the oneOf shape.
    if "oneOf" in arg:
        out: dict[str, Any] = {"oneOf": [_slim_arg(m) for m in arg["oneOf"]]}
        if arg.get("required"):
            out["required"] = True
        return out

    out = {}
    flags = arg.get("flags") or []
    if not flags:
        out["positional"] = arg["dest"]
    elif len(flags) == 1:
        out["flag"] = flags[0]
    else:
        out["flags"] = flags
    if arg.get("help"):
        out["help"] = arg["help"]
    if arg.get("required"):
        out["required"] = True
    if arg.get("choices"):
        out["choices"] = arg["choices"]
    if "default" in arg:
        default = arg["default"]
        if default is not None and default is not False:
            out["default"] = default
    action = arg.get("action")
    if action == "store_true":
        pass  # implicit boolean flag — presence sets True
    elif action in ("store_false", "count", "append"):
        out["action"] = action
    elif "type" in arg and arg["type"] not in ("str", "bool"):
        out["type"] = arg["type"]
    if "nargs" in arg:
        out["nargs"] = arg["nargs"]
    return out


def _summarize(node: dict[str, Any]) -> dict[str, Any]:
    """Trim an enriched audit Node to the slim shape the SessionStart
    agent actually uses.

    The enriched tree from check_cli_commands.py carries every field a
    consumer could want — audit affordances (`pkg`, `kind`, `pattern`,
    raw `commands`, `orphan`, `violations`) AND agent-facing
    resolutions (`command`, `role`, `description`, enriched
    `subcommands`). For the SessionStart context block we want a
    structural map ('what entry points exist and how they compose'),
    not a help dump and not an audit report, so we drop the audit
    affordances and keep only what an agent needs to PICK and INVOKE
    a command:

      - `command`     (always)
      - `description` (when present — i.e. not the root)
      - `pattern`     (from enriched `role`)
      - `subcommands` (merged: §3-composed children FIRST, then
                       argparse subparsers from the enriched
                       `subcommands` field — the agent sees one
                       unified 'things you can run from here' list
                       since the §3-vs-argparse distinction is an
                       implementation detail it doesn't care about)
      - `orphan`      (only when true — flags a §3 violation worth
                       surfacing even in the slim view)
      - `violations`  (only when non-empty — same reason)

    The script enriches; the hook summarizes. Other downstream consumers
    that want a different summary roll their own.
    """
    out: dict[str, Any] = {
        "command": node["command"],
        "pattern": node["role"],
    }
    description = node.get("description")
    if description is not None:
        out["description"] = description
    if node.get("orphan"):
        out["orphan"] = True
    if node.get("violations"):
        out["violations"] = list(node["violations"])
    # Top-level parser args (when the leaf exposes a parser() factory).
    if node.get("args"):
        out["args"] = [_slim_arg(a) for a in node["args"]]

    merged: list[dict[str, Any]] = []
    for child in node.get("children") or []:
        merged.append(_summarize(child))
    for sub in node.get("subcommands") or []:
        entry: dict[str, Any] = {
            "command": sub["command"],
            "description": sub["description"],
        }
        if sub.get("args"):
            entry["args"] = [_slim_arg(a) for a in sub["args"]]
        merged.append(entry)
    if merged:
        out["subcommands"] = merged
    return out


def _audit_one(python: Path, package_dir: Path, repo_root: Path) -> dict[str, Any] | None:
    """Run check_cli_commands.py against one package directory and return
    the parsed JSON tree, or None on failure. Non-zero exit is fine —
    §3 violations don't suppress the JSON output."""
    try:
        result = subprocess.run(
            [str(python), str(AUDIT_SCRIPT), "--json", str(package_dir)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    stdout = result.stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _emit(envelope: dict[str, object]) -> None:
    print(json.dumps(envelope))


def _disabled(repo_root: Path) -> bool:
    return (repo_root / ".claude" / "cli-discovery.disabled").is_file()


def _build_context(roots: list[dict[str, Any]]) -> str:
    count = len(roots)
    summary = f"{count} CLI root" + ("s" if count != 1 else "")
    payload = json.dumps({"roots": roots}, indent=2)
    return (
        f"CLI surface discovered ({summary}).\n"
        "\n"
        "The JSON below is the repo's `python -m <pkg>` surface, audited "
        "by racecar's `arch-coherence/scripts/check_cli_commands.py` "
        "against the §3 contract (`__main__.py` + `commands()`). Treat "
        "it as authoritative for 'what CLI entry points exist' — prefer "
        "browsing this tree to calling `--help` on guess-named modules.\n"
        "\n"
        "Schema per entry:\n"
        "  - `command`: the literal invocation (already includes "
        "`python -m`)\n"
        "  - `description`: the parent's `commands()` blurb (omitted on "
        "the top-level root)\n"
        "  - `pattern`: `pure-discovery` (composes children only) | "
        "`discovery+cli` (composes children AND has its own argparse) | "
        "`leaf` (own argparse, no children)\n"
        "  - `subcommands`: recursive entries (omitted when empty)\n"
        "  - `orphan`: present and true only when this entry is a "
        "runnable `__main__` that the parent's `commands()` did NOT "
        "register — a §3 violation worth surfacing\n"
        "  - `violations`: present only when non-empty\n"
        "\n"
        "```json\n"
        f"{payload}\n"
        "```\n"
    )


def main() -> int:
    # SessionStart input is a JSON blob on stdin; we don't currently need
    # any of its fields (CWD comes from the process environment), but we
    # consume stdin so the harness doesn't see EPIPE.
    try:
        sys.stdin.read()
    except OSError:
        pass

    try:
        repo_root = _find_repo_root(Path.cwd())
        if repo_root is None:
            return 0

        if _disabled(repo_root):
            _emit({"systemMessage": "racecar: CLI discovery disabled (.claude/cli-discovery.disabled)"})
            return 0

        if not AUDIT_SCRIPT.is_file():
            return 0

        cli_roots = _discover_cli_roots(repo_root)
        if not cli_roots:
            return 0

        python = _resolve_python(repo_root)
        if python is None:
            return 0

        roots: list[dict[str, Any]] = []
        for pkg_dir in cli_roots:
            enriched = _audit_one(python, pkg_dir, repo_root)
            if enriched is None:
                continue
            roots.append(_summarize(enriched))

        if not roots:
            return 0

        names = ", ".join(f"`{pkg_dir.name}`" for pkg_dir in cli_roots)
        _emit(
            {
                "systemMessage": f"racecar: CLI surface discovered ({names})",
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": _build_context(roots),
                },
            }
        )
    except Exception:
        # SessionStart hooks must never block a session from starting.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
