#!/usr/bin/env python3
"""Sync canonical racecar check scripts from GitHub into an adopter repo.

Fetches the canonical check scripts directly from the racecar GitHub repository
using urllib (stdlib — no pip required). Use this when you do not have a
local racecar clone and want to update an existing adopter repo to the latest
scripts (or a pinned ref).

Usage:
    # Fetch this script and run it in one step (no local clone needed):
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo

    # Pin to a specific tag or commit:
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo --ref v0.6.0

    # Preview without writing:
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo --dry-run

    # Also deliver missing templates (Makefile, pre-commit config, gitignore,
    # system-deps script) — create-if-missing, never overwrites:
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo --templates

Exit codes: 0 always (sync is not a gate).
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_RAW = "https://raw.githubusercontent.com/vishalapte/racecar/{ref}/{path}"

# The canonical delivered-file list lives in ONE home: scripts/racecar-manifest.txt,
# generated from the real scripts by `sync_scripts.py --write-manifest` and pinned by
# a test. The remote path FETCHES it rather than hardcoding a copy, which is exactly
# how the old hardcoded list here silently drifted out of step with sync_scripts (and
# never learned to deliver the sibling `_rules/` package modules). Each manifest line
# is a repo-relative source path; a Django-only file carries a trailing ` django` tag.
MANIFEST_REL = "scripts/racecar-manifest.txt"

# Templates delivered create-if-missing only (--templates). Existing copies are
# never overwritten: templates are per-project-customized example artifacts,
# not canon — drift in an existing Makefile is check_packaging.py's to report,
# not sync's to clobber. (source path in the racecar repo, target relative to dest)
TEMPLATE_FILES = (
    ("templates/classic/Makefile", "Makefile"),
    ("templates/classic/pre-commit-config.yaml", ".pre-commit-config.yaml"),
    ("templates/classic/gitignore", ".gitignore"),
    ("templates/classic/install_system_deps.sh", "scripts/install_system_deps.sh"),
)


def fetch(url: str) -> str:
    """Fetch `url` over HTTPS and return the decoded UTF-8 body."""
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        return resp.read().decode("utf-8")


def _sync_templates(dest: Path, ref: str, dry_run: bool) -> int:
    """Create-if-missing template delivery from GitHub. Returns count created."""
    created = 0
    for rel_source, rel_target in TEMPLATE_FILES:
        target = dest / rel_target
        if target.exists():
            print(f"  exists     {rel_target}  (templates are never overwritten)")
            continue
        url = BASE_RAW.format(ref=ref, path=rel_source)
        try:
            content = fetch(url)
        except urllib.error.URLError as exc:
            print(f"  FETCH ERROR  {rel_source}: {exc}")
            continue
        note = "  — set the shape variables" if rel_target == "Makefile" else ""
        print(f"  created    {rel_target}  (from {rel_source}{note})")
        created += 1
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            if rel_target.endswith(".sh"):
                target.chmod(target.stat().st_mode | 0o111)
    return created


def _is_django_repo(dest: Path) -> bool:
    """An adopter is a Django repo if it has a manage.py somewhere (mirrors sync_scripts)."""
    return any(dest.rglob("manage.py"))


def _manifest_entries(ref: str) -> list[tuple[str, bool]]:
    """Fetch and parse the canonical manifest: (repo-relative source, is_django) pairs."""
    raw = fetch(BASE_RAW.format(ref=ref, path=MANIFEST_REL))
    entries: list[tuple[str, bool]] = []
    for line in raw.splitlines():
        parts = line.split()
        if parts:
            entries.append((parts[0], len(parts) > 1 and parts[1] == "django"))
    return entries


def sync(dest: Path, ref: str, dry_run: bool, templates: bool = False) -> None:
    """Fetch canonical scripts from GitHub and write them into dest/scripts/.

    Drives off the fetched manifest (one home for the delivered-file list), so the
    remote path delivers exactly what `make sync` does, including the `_rules/`
    package modules under their subdirectory and the Django-only checks when the
    adopter has a manage.py.
    """
    if not dest.is_dir():
        raise SystemExit(f"sync_remote: {dest} does not exist or is not a directory.")

    scripts_dir = dest / "scripts"
    is_django = _is_django_repo(dest)
    created = updated = unchanged = 0

    for rel_source, django_only in _manifest_entries(ref):
        if django_only and not is_django:
            continue
        url = BASE_RAW.format(ref=ref, path=rel_source)
        try:
            canonical = fetch(url)
        except urllib.error.URLError as exc:
            print(f"  FETCH ERROR  {rel_source}: {exc}")
            continue

        # Preserve the package subdirectory: a `_rules/` module lands under it, an
        # entry script lands flat. The path tail after the lens `scripts/` is the dest.
        target = scripts_dir / rel_source.rsplit("scripts/", 1)[-1]

        if target.exists():
            if target.read_text(encoding="utf-8") == canonical:
                print(f"  unchanged  {target.relative_to(dest)}")
                unchanged += 1
                continue
            label = "updated"
            updated += 1
        else:
            label = "created"
            created += 1

        print(f"  {label:<9} {target.relative_to(dest)}")
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(canonical, encoding="utf-8")

    templates_created = _sync_templates(dest, ref, dry_run) if templates else 0

    suffix = " (dry run — no files written)" if dry_run else ""
    tail = f", {templates_created} template(s) created" if templates else ""
    print(
        f"sync_remote: {created} created, {updated} updated,"
        f" {unchanged} unchanged{tail}{suffix}"
    )


def parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the remote sync."""
    p = argparse.ArgumentParser(
        description="Sync canonical racecar check scripts from GitHub into an adopter repo.",
    )
    p.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Root of the adopter repo (the directory containing its Makefile).",
    )
    p.add_argument(
        "--ref",
        default="main",
        help="Git ref (branch, tag, or commit SHA) to fetch from. Default: main.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files.",
    )
    p.add_argument(
        "--templates",
        action="store_true",
        help="Also deliver missing template files (Makefile, .pre-commit-config.yaml, "
        ".gitignore, scripts/install_system_deps.sh). Create-if-missing only; "
        "existing files are never overwritten.",
    )
    return p


def main(argv: list[str]) -> int:
    """Fetch canonical scripts from GitHub into the adopter repo; return an exit code."""
    args = parser().parse_args(argv)
    dest = args.dest.expanduser().resolve()
    sync(dest, ref=args.ref, dry_run=args.dry_run, templates=args.templates)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
