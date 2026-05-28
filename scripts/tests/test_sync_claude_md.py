"""Tests for scripts/sync_claude_md.py.

The script mutates ``~/.claude/CLAUDE.md`` and ``~/.claude/settings.json``
on the consumer's machine. These tests redirect both targets into tmp_path
via the ``--claude-md`` and ``--settings`` CLI flags and assert:

  - First run on an empty target creates the pointer block and the two
    hooks.
  - Re-run is idempotent (no further mutation reported).
  - Existing user content in CLAUDE.md outside the managed BEGIN/END
    markers is preserved across both first run and re-run.
  - Existing unrelated hooks in settings.json under the same matcher
    are preserved; only racecar's two hooks are upserted.
  - Hook identification by basename means a stale absolute path (e.g.
    racecar checkout moved) is rewritten in place rather than appended.
  - ``--dry-run`` prints the would-be output and does not touch disk.

Run with:
    pytest scripts/tests/test_sync_claude_md.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "sync_claude_md.py"


def _run(
    claude_md: Path,
    settings: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--claude-md",
            str(claude_md),
            "--settings",
            str(settings),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _load_settings(path: Path) -> dict:
    return json.loads(path.read_text())


def _racecar_hook_count(settings: dict, event: str, basename: str) -> int:
    count = 0
    for matcher_entry in settings.get("hooks", {}).get(event, []):
        for hook in matcher_entry.get("hooks", []):
            if hook.get("command", "").endswith(basename):
                count += 1
    return count


def test_first_run_creates_pointer_and_hooks(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    result = _run(claude_md, settings)
    assert result.returncode == 0, result.stderr

    text = claude_md.read_text()
    assert "<!-- BEGIN racecar pointer (managed) -->" in text
    assert "<!-- END racecar pointer (managed) -->" in text

    parsed = _load_settings(settings)
    assert _racecar_hook_count(parsed, "PreToolUse", "compound-command-allow.sh") == 1
    assert _racecar_hook_count(parsed, "PostToolUse", "claude_racecar_hook.sh") == 1


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    _run(claude_md, settings)
    md_after_first = claude_md.read_text()
    settings_after_first = settings.read_text()

    result = _run(claude_md, settings)
    assert result.returncode == 0
    assert "already up to date" in result.stdout

    assert claude_md.read_text() == md_after_first
    assert settings.read_text() == settings_after_first


def test_existing_user_content_in_claude_md_is_preserved(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"
    user_content = "# My personal CLAUDE.md\n\nMy own rules.\n"
    claude_md.write_text(user_content)

    _run(claude_md, settings)

    text = claude_md.read_text()
    assert "# My personal CLAUDE.md" in text
    assert "My own rules." in text
    assert "<!-- BEGIN racecar pointer (managed) -->" in text


def test_existing_unrelated_hooks_are_preserved(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {"type": "command", "command": "/path/to/my-own-hook.sh"}
                            ],
                        }
                    ]
                }
            }
        )
    )

    _run(claude_md, settings)

    parsed = _load_settings(settings)
    bash_matcher = next(
        m for m in parsed["hooks"]["PreToolUse"] if m["matcher"] == "Bash"
    )
    commands = [h["command"] for h in bash_matcher["hooks"]]
    assert any(c.endswith("my-own-hook.sh") for c in commands)
    assert any(c.endswith("compound-command-allow.sh") for c in commands)


def test_stale_racecar_hook_path_is_rewritten_in_place(tmp_path: Path) -> None:
    """If the racecar checkout moved, the hook command path should be rewritten,
    not appended — identification is by basename, not full path."""
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Read",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "/old/path/hooks/claude_racecar_hook.sh",
                                }
                            ],
                        }
                    ]
                }
            }
        )
    )

    _run(claude_md, settings)

    parsed = _load_settings(settings)
    assert _racecar_hook_count(parsed, "PostToolUse", "claude_racecar_hook.sh") == 1
    read_matcher = next(
        m for m in parsed["hooks"]["PostToolUse"] if m["matcher"] == "Read"
    )
    commands = [h["command"] for h in read_matcher["hooks"]]
    assert all("/old/path/" not in c for c in commands)


def test_session_load_standards_hook_wired_on_all_four_matchers(
    tmp_path: Path,
) -> None:
    """The standards-loader SessionStart hook must be present on startup,
    resume, clear, and compact matchers — that is the contract that makes
    racecar's README + shared/*.md show up in every session boundary."""
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    _run(claude_md, settings)

    parsed = _load_settings(settings)
    session_start_entries = parsed["hooks"]["SessionStart"]
    matchers_with_loader = {
        entry["matcher"]
        for entry in session_start_entries
        if any(
            h["command"].endswith("session_load_standards.py")
            for h in entry.get("hooks", [])
        )
    }
    assert matchers_with_loader == {"startup", "resume", "clear", "compact"}


def test_session_load_and_history_coexist_on_compact_matcher(
    tmp_path: Path,
) -> None:
    """The standards-loader and the HISTORY.md reconciler both live on
    SessionStart(compact). Neither should evict the other."""
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    _run(claude_md, settings)

    parsed = _load_settings(settings)
    compact_entry = next(
        m for m in parsed["hooks"]["SessionStart"] if m["matcher"] == "compact"
    )
    basenames = {h["command"].rsplit("/", 1)[-1] for h in compact_entry["hooks"]}
    assert "session_load_standards.py" in basenames
    assert "session_compact_history.py" in basenames


def test_session_discover_cli_hook_wired_on_all_four_matchers(
    tmp_path: Path,
) -> None:
    """The CLI-discovery SessionStart hook must be present on startup,
    resume, clear, and compact matchers — same coverage as the standards
    loader, so the audit tree is re-injected after /clear and compaction."""
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    _run(claude_md, settings)

    parsed = _load_settings(settings)
    session_start_entries = parsed["hooks"]["SessionStart"]
    matchers_with_discover = {
        entry["matcher"]
        for entry in session_start_entries
        if any(
            h["command"].endswith("session_discover_cli.py")
            for h in entry.get("hooks", [])
        )
    }
    assert matchers_with_discover == {"startup", "resume", "clear", "compact"}


def test_session_load_and_discover_coexist(tmp_path: Path) -> None:
    """Both SessionStart hooks must coexist on every shared matcher —
    one loads standards, the other injects the CLI audit. Neither
    evicts the other when both target the same matcher."""
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    _run(claude_md, settings)

    parsed = _load_settings(settings)
    for matcher_name in ("startup", "resume", "clear", "compact"):
        entry = next(
            m for m in parsed["hooks"]["SessionStart"] if m["matcher"] == matcher_name
        )
        basenames = {h["command"].rsplit("/", 1)[-1] for h in entry["hooks"]}
        assert "session_load_standards.py" in basenames, matcher_name
        assert "session_discover_cli.py" in basenames, matcher_name


def test_dry_run_does_not_write_disk(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"

    result = _run(claude_md, settings, "--dry-run")
    assert result.returncode == 0
    assert "<!-- BEGIN racecar pointer (managed) -->" in result.stdout
    assert not claude_md.exists()
    assert not settings.exists()
