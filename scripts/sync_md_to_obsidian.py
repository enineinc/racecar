#!/usr/bin/env python3
"""Mirror tracked .md files from the repo into an Obsidian vault.

Sources: all tracked .md files (`git ls-files`). Submodule contents are
excluded automatically — `git ls-files` lists the gitlink, not its files.
By default, paths with any dot-prefixed component (`.data/...`,
`.downloads/...`, `.venv/...`) are filtered out; pass `--dotfiles` to
include them.

Destination root resolution order:
  1. --dest CLI flag
  2. OBSIDIAN_SYNC_ROOT env var
  3. dest_root in ~/.config/obsidian-sync.toml

If none are set, the script exits with a helpful error. There is no
default — the destination is per-user and the script refuses to guess.

Files are copied preserving the repo-relative path. Identical files
(same size + content) are skipped. Pass --prune to delete files in the
destination that no longer exist in the source set.

Usage:
    python scripts/sync_md_to_obsidian.py [--dest PATH] [--dry-run] [--prune] [--dotfiles]
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "obsidian-sync.toml"


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    raise SystemExit(f"no .git ancestor of {start}")


def load_config_dest() -> Path | None:
    if not CONFIG_PATH.is_file():
        return None
    data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw = data.get("dest_root")
    if not raw:
        return None
    return Path(os.path.expanduser(raw)).expanduser()


def resolve_dest(cli_dest: str | None) -> Path:
    if cli_dest:
        return Path(cli_dest).expanduser().resolve()
    env = os.environ.get("OBSIDIAN_SYNC_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    cfg = load_config_dest()
    if cfg is not None:
        return cfg.resolve()
    raise SystemExit(
        "no destination configured; pass --dest, set OBSIDIAN_SYNC_ROOT, "
        f"or put dest_root = \"...\" in {CONFIG_PATH}"
    )


def tracked_md_files(root: Path, *, include_dotfiles: bool) -> list[Path]:
    out = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.md"],
    )
    rels = [Path(p) for p in out.decode().split("\0") if p]

    if include_dotfiles:
        return sorted(rels)
    return sorted(r for r in rels if not any(part.startswith(".") for part in r.parts))


def copy_one(src: Path, dst: Path, *, dry_run: bool) -> str:
    if dst.is_file() and filecmp.cmp(src, dst, shallow=False):
        return "skip"
    if dry_run:
        return "would-copy"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "copy"


def prune_extras(dest_root: Path, expected: set[Path], *, dry_run: bool) -> list[Path]:
    """Delete .md files under dest_root that aren't in `expected` (relative paths)."""
    removed: list[Path] = []
    if not dest_root.is_dir():
        return removed
    for path in dest_root.rglob("*.md"):
        rel = path.relative_to(dest_root)
        if rel in expected:
            continue
        removed.append(rel)
        if not dry_run:
            path.unlink()
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", help="override destination root")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--prune",
        action="store_true",
        help="delete .md files in dest that aren't in source",
    )
    ap.add_argument(
        "--dotfiles",
        action="store_true",
        help="include paths with dot-prefixed components (.data, .downloads, ...)",
    )
    args = ap.parse_args()

    root = repo_root(Path.cwd().resolve())
    dest = resolve_dest(args.dest)

    files = tracked_md_files(root, include_dotfiles=args.dotfiles)
    if not files:
        print("no tracked .md files found")
        return 0

    print(f"repo:  {root}")
    print(f"dest:  {dest}")
    print(f"files: {len(files)}")
    print()

    counts = {"copy": 0, "skip": 0, "would-copy": 0}
    for rel in files:
        action = copy_one(root / rel, dest / rel, dry_run=args.dry_run)
        counts[action] = counts.get(action, 0) + 1
        if action != "skip":
            print(f"  {action}: {rel}")

    if args.prune:
        removed = prune_extras(dest, set(files), dry_run=args.dry_run)
        for rel in removed:
            print(f"  {'would-remove' if args.dry_run else 'remove'}: {rel}")
        counts["pruned"] = len(removed)

    print()
    print("summary:", ", ".join(f"{k}={v}" for k, v in counts.items() if v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
