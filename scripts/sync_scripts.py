#!/usr/bin/env python3
"""Sync canonical racecar check scripts into an existing adopter repo.

Copies the canonical racecar check scripts from their homes into
<dest>/scripts/<basename>.py. Scripts that are already up-to-date are left
untouched. Scripts that differ are overwritten; new scripts are created.

Use this when racecar updates a check script and you want the adopter repo
to pick up the change without re-running the full scaffolder (which refuses
non-empty destinations).

Usage:
    python scripts/sync_scripts.py --dest /path/to/repo
    python scripts/sync_scripts.py --dest /path/to/repo --dry-run
    python scripts/sync_scripts.py --dest /path/to/repo --templates  # + missing templates

    # Via Make (from racecar root):
    make sync-scripts DEST=/path/to/repo
    make sync-scripts DEST=/path/to/repo DRY_RUN=--dry-run

Exit codes: 0 always (sync is not a gate).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def canon_ref() -> str:
    """Human label for the racecar canon state: short git SHA, marked '-dirty'
    when the checkout has uncommitted changes.

    The synced scripts are compared by CONTENT, not by this label; the ref exists
    only so the staleness hook can say which racecar a repo is in sync with. The
    '-dirty' marker keeps it from claiming a clean commit the working tree does not
    match (during racecar development the checkout is normally dirty). Falls back to
    the VERSION label when git is unavailable. One home: session_check_sync imports
    this so the stamp and the hook agree.
    """
    try:
        sha = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (OSError, subprocess.CalledProcessError):
        v = REPO_ROOT / "VERSION"
        return f"v{v.read_text(encoding='utf-8').strip()}" if v.is_file() else "unknown"


# Scripts synced to every adopter repo. This set must equal the canonical
# check-script set every adopter needs to run its own gate locally: a script that
# racecar runs ON an adopter's behalf but that the adopter cannot run itself
# couples the adopter to the racecar checkout (the bug this list exists to avoid).
#   - check_subsystem_docs.py: stdlib; no-ops without import-linter contracts.
#     Wired into the template `docs:` target.
#   - check_brief.py: validates the adopter's own docs/summary/<REPO>.md. It needs
#     pyyaml, which is a canonical dev tool (PACKAGING.md §6); the template `docs:`
#     target runs it guarded so it no-ops when the repo has no brief.
CHECK_SCRIPTS = (
    "arch-coherence/scripts/check_upward_imports.py",
    "arch-coherence/scripts/check_cli_commands.py",
    "arch-coherence/scripts/check_packaging.py",
    "arch-coherence/scripts/check_surface_orchestration.py",
    "arch-coherence/scripts/check_surface_auth.py",
    "doc-coherence/scripts/check_docs.py",
    "doc-coherence/scripts/check_doc_graph.py",
    "doc-coherence/scripts/check_subsystem_docs.py",
    "doc-coherence/scripts/check_todo_format.py",
    "doc-coherence/scripts/check_file_placement.py",
    "llm-summary/scripts/check_brief.py",
    "scripts/check_version_bump.py",
    "scripts/clean_files.sh",
)

# Scripts synced only when the dest repo contains a manage.py (Django project).
DJANGO_SCRIPTS = ("arch-coherence/scripts/check_dj_model_ref_as_string.py",)

# Scripts no longer canonical (renamed or deleted); removed from dest/scripts/ on sync
# so an adopter that received an earlier version does not keep a stale, unused copy.
REMOVED_SCRIPTS = (
    "check_string_relations.py",
    "repo_context.py",
    "check_claude_shape.py",
    "check_prose_punctuation.py",  # retired: dash gate, false positives > value (VOICE.md)
)

# Templates delivered create-if-missing only (--templates). Existing copies are
# never overwritten: templates are per-project-customized example artifacts,
# not canon — drift in an existing Makefile is check_packaging.py's to report,
# not sync's to clobber. (source relative to racecar root, target relative to dest)
TEMPLATE_FILES = (
    ("templates/classic/Makefile", "Makefile"),
    ("templates/classic/pre-commit-config.yaml", ".pre-commit-config.yaml"),
    ("templates/classic/gitignore", ".gitignore"),
    ("templates/classic/install_system_deps.sh", "scripts/install_system_deps.sh"),
    # Human README skeleton (who-what -> Getting Started -> Using -> when/where/why).
    # Create-if-missing only: a repo with a README keeps it untouched.
    ("templates/classic/README.md", "README.md"),
)


def delivered_files(rel_source: str) -> list[tuple[Path, Path]]:
    """The canonical files delivered for one script entry, as (source, dest) pairs.

    A heavyweight checker keeps a thin entry file (check_packaging.py) and moves its
    implementation into a sibling `<stem>_rules/` package (check_packaging_rules/).
    The package is NOT listed separately in CHECK_SCRIPTS: it travels with its entry
    by this naming convention, so the two cannot drift apart. One home for "what an
    entry actually delivers", reused by sync, the scaffolder, and the staleness hook.

    Returns (absolute source, dest relative to scripts/) pairs: the entry itself, then
    every module of its sibling impl package if one exists. An entry whose source is
    missing yields no pairs.
    """
    source = REPO_ROOT / rel_source
    if not source.exists():
        return []
    pairs = [(source, Path(source.name))]
    rules_pkg = source.with_name(f"{source.stem}_rules")
    if rules_pkg.is_dir():
        for module in sorted(rules_pkg.glob("*.py")):
            pairs.append((module, Path(rules_pkg.name) / module.name))
    return pairs


MANIFEST_REL = "scripts/racecar-manifest.txt"


def manifest() -> list[str]:
    """The canonical list of every file racecar delivers to an adopter, one per line.

    Each line is a repo-relative source path; a Django-only script carries a trailing
    ` django` tag. Derived from CHECK_SCRIPTS + DJANGO_SCRIPTS through `delivered_files`
    (the one home, so sibling `_rules/` package modules are expanded in too), then
    written to MANIFEST_REL by `--write-manifest` and pinned by a test. `sync_remote`
    fetches this file rather than keeping its own copy of the list: it is how the two
    sync paths stay in step without a shared import (the remote path runs with no
    clone to glob, so it cannot reach `delivered_files` itself).
    """
    lines: list[str] = []
    for rel in CHECK_SCRIPTS:
        lines += [str(src.relative_to(REPO_ROOT)) for src, _ in delivered_files(rel)]
    for rel in DJANGO_SCRIPTS:
        lines += [
            f"{src.relative_to(REPO_ROOT)} django" for src, _ in delivered_files(rel)
        ]
    return lines


def write_manifest() -> Path:
    """Write the canonical manifest to MANIFEST_REL; return the path written."""
    path = REPO_ROOT / MANIFEST_REL
    path.write_text("\n".join(manifest()) + "\n", encoding="utf-8")
    return path


def _is_django_repo(dest: Path) -> bool:
    return any(dest.rglob("manage.py"))


def _materialize_racecar_mk(dest: Path, dry_run: bool) -> str:
    """Install dest/racecar.mk as a verbatim copy of the canonical template.

    racecar.mk is IDENTICAL in every repo: it detects the shape from the filesystem
    at make-time (see templates/classic/racecar.mk), so there is nothing per-repo to
    generate. It is canonical content (like the check scripts), always overwritten to
    the canonical form, not a create-if-missing template.
    Returns 'created' / 'updated' / 'unchanged' / 'missing'.
    """
    template = REPO_ROOT / "templates" / "classic" / "racecar.mk"
    if not template.exists():
        print("  MISSING in racecar: templates/classic/racecar.mk (skipped)")
        return "missing"
    content = template.read_text(encoding="utf-8")
    target = dest / "racecar.mk"
    if target.exists():
        label = (
            "unchanged" if target.read_text(encoding="utf-8") == content else "updated"
        )
    else:
        label = "created"
    if not dry_run and label != "unchanged":
        target.write_text(content, encoding="utf-8")
    print(f"  {label:<9} racecar.mk")
    return label


def _sync_one(source: Path, target: Path, dry_run: bool) -> str:
    """Write source to target if changed. Returns 'created', 'updated', or 'unchanged'."""
    canonical = source.read_text(encoding="utf-8")
    if target.exists():
        if target.read_text(encoding="utf-8") == canonical:
            return "unchanged"
        label = "updated"
    else:
        label = "created"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical, encoding="utf-8")
    return label


def _sync_templates(dest: Path, dry_run: bool) -> int:
    """Create-if-missing template delivery. Returns count created."""
    created = 0
    for rel_source, rel_target in TEMPLATE_FILES:
        source = REPO_ROOT / rel_source
        if not source.exists():
            print(f"  MISSING in racecar: {rel_source} (skipped)")
            continue
        target = dest / rel_target
        if target.exists():
            print(f"  exists     {rel_target}  (templates are never overwritten)")
            continue
        note = (
            "  — owned root; edit freely (racecar.mk holds the canon)"
            if rel_target == "Makefile"
            else ""
        )
        print(f"  created    {rel_target}  (from {rel_source}{note})")
        created += 1
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            if rel_target.endswith(".sh"):
                target.chmod(target.stat().st_mode | 0o111)
    return created


def sync(dest: Path, dry_run: bool, templates: bool = False) -> None:
    """Copy canonical scripts into dest/scripts/, reporting each outcome."""
    if not dest.is_dir():
        raise SystemExit(f"sync_scripts: {dest} does not exist or is not a directory.")

    scripts_dir = dest / "scripts"
    is_django = _is_django_repo(dest)
    created = updated = unchanged = removed = 0

    all_scripts = list(CHECK_SCRIPTS) + (list(DJANGO_SCRIPTS) if is_django else [])
    for rel_source in all_scripts:
        pairs = delivered_files(rel_source)
        if not pairs:
            print(f"  MISSING in racecar: {rel_source} (skipped)")
            continue
        # The entry plus every module of its sibling _rules package (if any), so a
        # thin-entry checker delivers its implementation, not just the runnable shell.
        for source, dest_rel in pairs:
            target = scripts_dir / dest_rel
            label = _sync_one(source, target, dry_run)
            print(f"  {label:<9} {target.relative_to(dest)}")
            if label == "created":
                created += 1
            elif label == "updated":
                updated += 1
            else:
                unchanged += 1

    for old_name in REMOVED_SCRIPTS:
        old = scripts_dir / old_name
        if old.exists():
            print(f"  removed    scripts/{old_name}  (no longer canonical)")
            removed += 1
            if not dry_run:
                old.unlink()

    # Stamp the racecar ref synced from (short SHA, '-dirty' if the checkout had
    # uncommitted changes). The SessionStart staleness hook reports it; the
    # byte-compare is the real signal.
    if not dry_run:
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / ".racecar-version").write_text(
            canon_ref() + "\n", encoding="utf-8"
        )

    racecar_mk = _materialize_racecar_mk(dest, dry_run)

    templates_created = _sync_templates(dest, dry_run) if templates else 0

    suffix = " (dry run — no files written)" if dry_run else ""
    parts = [f"{created} created", f"{updated} updated", f"{unchanged} unchanged"]
    if removed:
        parts.append(f"{removed} removed")
    parts.append(f"racecar.mk {racecar_mk}")
    if templates:
        parts.append(f"{templates_created} template(s) created")
    print(f"sync_scripts: {', '.join(parts)}{suffix}")


def parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the script sync."""
    p = argparse.ArgumentParser(
        description="Sync canonical racecar check scripts into an existing adopter repo.",
    )
    p.add_argument(
        "--dest",
        type=Path,
        help="Root of the adopter repo (the directory containing its Makefile). "
        "Required unless --write-manifest.",
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
    p.add_argument(
        "--write-manifest",
        action="store_true",
        help="Regenerate scripts/racecar-manifest.txt (the canonical delivered-file "
        "list that sync_remote fetches) from the current scripts, then exit.",
    )
    return p


def main(argv: list[str]) -> int:
    """Sync the canonical check scripts into the adopter repo; return an exit code."""
    args = parser().parse_args(argv)
    if args.write_manifest:
        path = write_manifest()
        print(
            f"sync_scripts: wrote {path.relative_to(REPO_ROOT)} ({len(manifest())} files)"
        )
        return 0
    if args.dest is None:
        raise SystemExit("sync_scripts: --dest is required (or pass --write-manifest).")
    dest = args.dest.expanduser().resolve()
    sync(dest, dry_run=args.dry_run, templates=args.templates)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
