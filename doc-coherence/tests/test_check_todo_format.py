"""Tests for doc-coherence/scripts/check_todo_format.py.

Builds a fake repo under tmp_path with a `.git` marker and federated TODO
sections, and asserts exit code + message.

Run with:
    pytest doc-coherence/tests/test_check_todo_format.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_todo_format.py"

GOOD_ITEM = """\
## TODO

### 2B — Settlement schema discovery
- Prio: P0
- Depends: 1A, none
- Updated: 2026-05-28

What: validate the schemas.

## PLAN
- 2026-06 — 2B first.
"""

ROOT_RESOLVER = """\
# TODO

## TODO
- Labels — [LABELS.md](LABELS.md#todo)

## Completed
- 2026-05-12 — 1A done
"""


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True, check=False)


def _seed(tmp_path: Path, **files: str) -> Path:
    (tmp_path / ".git").mkdir()
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return tmp_path


def test_no_todo_md_is_silent(tmp_path: Path) -> None:
    repo = _seed(tmp_path)
    result = _run(repo)
    assert result.returncode == 0


def test_well_formed_federated_passes(tmp_path: Path) -> None:
    repo = _seed(tmp_path, **{"TODO.md": ROOT_RESOLVER, "LABELS.md": "# Labels\n\n" + GOOD_ITEM})
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_missing_fields_fails(tmp_path: Path) -> None:
    body = "# Labels\n\n## TODO\n\n### 3C — Bad\n- Depends: none\n"
    repo = _seed(tmp_path, **{"TODO.md": ROOT_RESOLVER, "LABELS.md": body})
    result = _run(repo)
    assert result.returncode == 1
    assert "missing `Prio:`" in result.stdout
    assert "missing `Updated:`" in result.stdout


def test_invalid_date_fails(tmp_path: Path) -> None:
    body = "# L\n\n## TODO\n\n### 4D — Bad date\n- Prio: P1\n- Depends: none\n- Updated: 2026-13-99\n"
    repo = _seed(tmp_path, **{"TODO.md": ROOT_RESOLVER, "LABELS.md": body})
    result = _run(repo)
    assert result.returncode == 1
    assert "not a valid date" in result.stdout


def test_fenced_example_is_ignored(tmp_path: Path) -> None:
    guide = "# Guide\n\n```markdown\n## TODO\n### 9Z — fenced, no fields\n```\n"
    repo = _seed(tmp_path, **{"TODO.md": ROOT_RESOLVER, "GUIDE.md": guide})
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_root_without_todo_index_fails(tmp_path: Path) -> None:
    repo = _seed(tmp_path, **{"TODO.md": "# TODO\n\n## Completed\n- nothing\n"})
    result = _run(repo)
    assert result.returncode == 1
    assert "missing `## TODO` index" in result.stdout
