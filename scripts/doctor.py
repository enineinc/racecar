#!/usr/bin/env python3
"""racecar doctor — verify the load mechanism layer by layer.

"Loaded" is not one thing. It is five layers, and a printed banner evidences
only the weakest. This script checks the four deterministic layers; the fifth
(is the model actually conditioning on the content) is not mechanically
checkable — the load-token challenge-response in the doctor skill is the
honest eval for it, and this script prints the expected token so the answer
can be compared.

  Layer 1  files    — baseline docs, hook scripts, and skill symlinks exist
  Layer 2  wiring   — every racecar hook is wired in settings.json on the
                      right event/matcher and points at an existing
                      executable inside this checkout
  Layer 3  execute  — session_load_standards.py actually runs and emits the
                      full baseline (every file header + the load token)
  Layer 4  context  — best-effort: the newest session transcript for the
                      CWD's project contains the load token. The transcript
                      format is harness-internal; when it cannot be located
                      this layer reports UNAVAILABLE, never a fake green.

Layers 1-3 drive the exit code (0 all pass / 1 any fail). Layer 4 warns.

Expected wiring is imported from sync_claude_md.py and expected skills are
derived from the checkout's SKILL.md files — one home each; doctor catches
drift in `install` instead of duplicating its list.

Usage:
    python3 scripts/doctor.py            # report
    python3 scripts/doctor.py --fix      # re-run sync_claude_md + create
                                         # missing symlinks (refuses to
                                         # clobber, same as ./install)

Overrides (same as sync_claude_md.py): CLAUDE_MD_PATH, CLAUDE_SETTINGS_PATH,
CLAUDE_SKILLS_PATH, or --settings / --skills flags.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
RACECAR_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(RACECAR_ROOT / "hooks"))

# One home for the wiring table and the token computation: import the hook and
# the installer instead of restating their constants. Both live outside a
# package (hooks/ and scripts/ are plain directories), so the sys.path inserts
# above are the only way in — hence the post-path imports.
# pylint: disable=wrong-import-position
import session_load_standards  # noqa: E402  (hooks/session_load_standards.py)
import sync_claude_md  # noqa: E402  (scripts/sync_claude_md.py)

# pylint: enable=wrong-import-position

# Optional overlays: installed by a separate command (`make expert`), so their
# symlink absence is not a defect.
OPTIONAL_SKILL_DIRS = {"expert"}

# (event, matcher, hook basename) — one row per required wiring entry,
# built from sync_claude_md's constants so the two scripts cannot drift.
EXPECTED_WIRING: list[tuple[str, str, str]] = [
    ("PreToolUse", "Bash", sync_claude_md.PRE_HOOK_BASENAME),
    ("PostToolUse", "Read", sync_claude_md.POST_HOOK_BASENAME),
    ("PreCompact", "", sync_claude_md.PRECOMPACT_HOOK_BASENAME),
    ("SessionStart", "compact", sync_claude_md.SESSIONSTART_HOOK_BASENAME),
] + [
    ("SessionStart", matcher, basename)
    for basename in (
        sync_claude_md.SESSION_LOAD_HOOK_BASENAME,
        sync_claude_md.SESSION_DISCOVER_HOOK_BASENAME,
        sync_claude_md.SESSION_CHECK_SYNC_HOOK_BASENAME,
    )
    for matcher in sync_claude_md.SESSION_LOAD_MATCHERS
]


class Report:
    """Collects findings; renders one line per check, exit code at the end."""

    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def ok(self, layer: str, message: str) -> None:
        print(f"  ok    [{layer}] {message}")

    def fail(self, layer: str, message: str) -> None:
        self.failures += 1
        print(f"  FAIL  [{layer}] {message}")

    def warn(self, layer: str, message: str) -> None:
        self.warnings += 1
        print(f"  warn  [{layer}] {message}")


# ---------------------------------------------------------------------------
# Layer 1 — files
# ---------------------------------------------------------------------------


def expected_skills() -> dict[str, Path]:
    """Derive the expected skill symlinks from the checkout itself.

    The root SKILL.md is the `racecar` router skill; every top-level
    directory holding a SKILL.md is `racecar-<dir>` — except optional
    overlays. Self-updating: adding a skill directory makes doctor expect
    its symlink, which catches a stale `install` list.
    """
    skills: dict[str, Path] = {}
    if (RACECAR_ROOT / "SKILL.md").is_file():
        skills["racecar"] = RACECAR_ROOT
    for child in sorted(RACECAR_ROOT.iterdir()):
        if not child.is_dir() or child.name in OPTIONAL_SKILL_DIRS:
            continue
        if (child / "SKILL.md").is_file():
            skills[f"racecar-{child.name}"] = child
    return skills


def _check_baseline_docs(report: Report) -> None:
    # CLAUDE.md is the machine baseline the loader force-loads; README.md is the
    # human storefront and is intentionally not part of the loaded baseline.
    claude_md = RACECAR_ROOT / "CLAUDE.md"
    if claude_md.is_file() and claude_md.stat().st_size > 0:
        report.ok("files", f"{claude_md}")
    else:
        report.fail("files", f"{claude_md} missing or empty")

    shared = RACECAR_ROOT / "shared"
    shared_md = sorted(shared.glob("*.md")) if shared.is_dir() else []
    if not shared_md:
        report.fail("files", f"{shared} has no *.md baseline files")
    for path in shared_md:
        if path.stat().st_size > 0:
            report.ok("files", f"{path}")
        else:
            report.fail("files", f"{path} is empty")


def _check_hook_scripts(report: Report) -> None:
    for basename in dict.fromkeys(b for _, _, b in EXPECTED_WIRING):
        hook = RACECAR_ROOT / "hooks" / basename
        if not hook.is_file():
            report.fail("files", f"{hook} missing")
        elif not os.access(hook, os.X_OK):
            report.fail("files", f"{hook} not executable (chmod +x)")
        else:
            report.ok("files", f"{hook}")


def _check_skill_symlinks(report: Report, skills_dir: Path) -> None:
    for name, target in expected_skills().items():
        link = skills_dir / name
        if not link.is_symlink():
            if link.exists():
                report.fail(
                    "files",
                    f"{link} exists but is not a symlink; remove it manually",
                )
            else:
                report.fail("files", f"{link} missing (run ./install)")
            continue
        if Path(os.path.realpath(link)) == Path(os.path.realpath(target)):
            report.ok("files", f"{link} -> {target}")
        else:
            report.fail(
                "files",
                f"{link} -> {os.path.realpath(link)} (expected {target})",
            )


def check_files(report: Report, skills_dir: Path) -> None:
    _check_baseline_docs(report)
    _check_hook_scripts(report)
    _check_skill_symlinks(report, skills_dir)


# ---------------------------------------------------------------------------
# Layer 2 — wiring
# ---------------------------------------------------------------------------


def _find_wired_command(
    settings: dict, event: str, matcher: str, basename: str
) -> str | None:
    for entry in settings.get("hooks", {}).get(event, []):
        if not isinstance(entry, dict) or entry.get("matcher") != matcher:
            continue
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "") if isinstance(hook, dict) else ""
            if isinstance(cmd, str) and cmd.rstrip().rstrip("\"'").endswith(basename):
                return cmd
    return None


def check_wiring(report: Report, settings_path: Path) -> None:
    if not settings_path.is_file():
        report.fail("wiring", f"{settings_path} does not exist (run ./install)")
        return
    try:
        settings = json.loads(settings_path.read_text() or "{}")
    except json.JSONDecodeError as exc:
        report.fail("wiring", f"{settings_path} is not valid JSON: {exc}")
        return
    if not isinstance(settings, dict):
        report.fail("wiring", f"{settings_path} top-level value is not an object")
        return

    for event, matcher, basename in EXPECTED_WIRING:
        shown = matcher if matcher else '""'
        label = f"{event}[{shown}] -> {basename}"
        cmd = _find_wired_command(settings, event, matcher, basename)
        if cmd is None:
            report.fail("wiring", f"{label}: not wired (run ./install)")
            continue
        cmd_path = Path(cmd)
        if not cmd_path.is_file():
            report.fail("wiring", f"{label}: command points at missing file {cmd}")
        elif Path(os.path.realpath(cmd_path)) != Path(
            os.path.realpath(RACECAR_ROOT / "hooks" / basename)
        ):
            report.fail(
                "wiring",
                f"{label}: wired to {cmd}, not this checkout "
                f"({RACECAR_ROOT / 'hooks' / basename})",
            )
        else:
            report.ok("wiring", label)


# ---------------------------------------------------------------------------
# Layer 3 — execution
# ---------------------------------------------------------------------------


def check_execution(report: Report) -> str | None:
    """Run the standards loader for real; verify its envelope. Returns the
    expected load token (recomputed from the baseline) either way."""
    items = session_load_standards.collect_baseline()
    token = session_load_standards.load_token(items) if items else None
    if not items:
        report.fail("execute", "baseline collect() returned nothing")
        return None

    hook = RACECAR_ROOT / "hooks" / "session_load_standards.py"
    try:
        result = subprocess.run(
            [sys.executable, str(hook)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report.fail("execute", f"{hook} failed to run: {exc}")
        return token

    if result.returncode != 0:
        report.fail(
            "execute",
            f"{hook} exited {result.returncode}: {result.stderr.strip()[:200]}",
        )
        return token
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError:
        report.fail("execute", f"{hook} emitted non-JSON output")
        return token

    context = envelope.get("hookSpecificOutput", {}).get("additionalContext", "")
    missing = [str(p) for p, _ in items if f"### {p}" not in context]
    if missing:
        report.fail(
            "execute",
            f"additionalContext missing {len(missing)} file section(s): "
            + ", ".join(missing),
        )
    else:
        report.ok("execute", f"additionalContext carries all {len(items)} files")

    if f"Load token: {token}" in context:
        report.ok("execute", f"load token planted: {token}")
    else:
        report.fail("execute", f"load token {token} absent from preamble")
    return token


# ---------------------------------------------------------------------------
# Layer 4 — context entry (best-effort)
# ---------------------------------------------------------------------------


def transcript_dir_for(cwd: Path, claude_home: Path) -> Path:
    """Claude Code names a project's transcript directory by replacing every
    path separator (and dot) in the resolved CWD with '-'. Harness-internal;
    this is the observed convention, hence layer 4 is best-effort only."""
    kebab = str(cwd.resolve()).replace("/", "-").replace(".", "-")
    return claude_home / "projects" / kebab


def check_context(report: Report, token: str | None, claude_home: Path) -> None:
    if token is None:
        report.warn("context", "no token to search for (layer 3 failed)")
        return
    tdir = transcript_dir_for(Path.cwd(), claude_home)
    if not tdir.is_dir():
        report.warn(
            "context",
            f"UNAVAILABLE — no transcript directory at {tdir} "
            "(format is harness-internal; layers 1-3 stand on their own)",
        )
        return
    transcripts = sorted(
        tdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not transcripts:
        report.warn("context", f"UNAVAILABLE — no *.jsonl transcripts in {tdir}")
        return
    newest = transcripts[0]
    if token in newest.read_text(encoding="utf-8", errors="replace"):
        # Honesty caveat: doctor's own output (which prints the token) also
        # lands in the transcript, so a found-token after doctor has already
        # run in this session is weak evidence. The strong read is the first
        # run of a fresh session, before the token has been echoed.
        report.ok(
            "context",
            f"load token found in {newest.name} (weak once doctor has "
            "already run in this session — doctor's own output also lands "
            "in the transcript; the strong read is a fresh session's first run)",
        )
    else:
        report.warn(
            "context",
            f"load token NOT in newest transcript {newest.name} — the "
            "current session may predate the token, or the baseline was "
            "not injected; start a fresh session and re-check",
        )


# ---------------------------------------------------------------------------
# --fix
# ---------------------------------------------------------------------------


def fix(skills_dir: Path) -> None:
    """Repair wiring via sync_claude_md and create missing symlinks.

    Probe before mutate: only absent symlinks are created; anything present
    but wrong is reported and left alone (same refusal as ./install)."""
    print("doctor --fix: re-running sync_claude_md ...")
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "sync_claude_md.py")], check=False
    )
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name, target in expected_skills().items():
        link = skills_dir / name
        if link.is_symlink() or link.exists():
            continue
        link.symlink_to(target)
        print(f"doctor --fix: created {link} -> {target}")


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--settings",
        help="Path to settings.json (default: $CLAUDE_SETTINGS_PATH or ~/.claude/settings.json).",
    )
    p.add_argument(
        "--skills",
        help="Path to the skills dir (default: $CLAUDE_SKILLS_PATH or ~/.claude/skills).",
    )
    p.add_argument(
        "--fix",
        action="store_true",
        help="Repair wiring (sync_claude_md) and create missing skill symlinks, then re-check.",
    )
    return p


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    claude_home = Path.home() / ".claude"
    settings_path = sync_claude_md.resolve_path(
        args.settings, "CLAUDE_SETTINGS_PATH", claude_home / "settings.json"
    )
    skills_dir = sync_claude_md.resolve_path(
        args.skills, "CLAUDE_SKILLS_PATH", claude_home / "skills"
    )

    if args.fix:
        fix(skills_dir)
        print()

    report = Report()
    print("Layer 1 — files")
    check_files(report, skills_dir)
    print("Layer 2 — wiring")
    check_wiring(report, settings_path)
    print("Layer 3 — execution")
    token = check_execution(report)
    print("Layer 4 — context entry (best-effort)")
    check_context(report, token, claude_home)

    print()
    if token:
        print(f"Expected load token: {token}")
        print(
            "Layer 5 (model conditioning) is not mechanically checkable. "
            "Ask the agent 'is racecar loaded?' — a real load reproduces "
            "the token above from context. An eval, not a proof."
        )
    print(
        f"doctor: {report.failures} failure(s), {report.warnings} warning(s) "
        f"— {'FAIL' if report.failures else 'PASS'} on deterministic layers"
    )
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
