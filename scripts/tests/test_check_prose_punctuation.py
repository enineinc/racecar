"""check_prose_punctuation: no em-dashes / en-dashes / `--` sentence dashes in prose."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import check_prose_punctuation  # noqa: E402

# ---------------------------------------------------------------------------
# the punctuation detector (pure)
# ---------------------------------------------------------------------------


def test_em_dash_is_flagged():
    hits = check_prose_punctuation.find_violations("a word — another")
    assert len(hits) == 1 and "em-dash" in hits[0][1]


def test_en_dash_is_flagged():
    hits = check_prose_punctuation.find_violations("range 0–100")
    assert len(hits) == 1 and "en-dash" in hits[0][1]


def test_double_dash_sentence_is_flagged():
    assert check_prose_punctuation.find_violations("well -- yes")
    assert check_prose_punctuation.find_violations("word--word")


def test_double_dash_at_line_end_is_flagged():
    # A `--` sentence dash whose second clause wraps to the next line: the dash sits at
    # end-of-line with no trailing space. find_violations scans line by line, so the
    # trailing-whitespace form must accept end-of-line too.
    assert check_prose_punctuation.find_violations("one-directional --")
    assert check_prose_punctuation.find_violations("one-directional --\nit fails") == [
        (1, "`--` used as a sentence dash; use a comma or period")
    ]


def test_cli_flag_is_not_flagged():
    assert check_prose_punctuation.find_violations("pass --flag to it") == []


def test_markdown_rule_and_table_separator_not_flagged():
    assert check_prose_punctuation.find_violations("---") == []
    assert check_prose_punctuation.find_violations("| ----- | ----- |") == []


def test_markdown_prose_strips_code_but_keeps_line_numbers():
    # A fenced block and an inline span are machine-readable and exempt; prose around them
    # is still scanned, and reported line numbers stay aligned with the source.
    md = "clean line\n```\ncode — dash\n```\ninline `x — y` code\nprose — here\n"
    prose = check_prose_punctuation._markdown_prose(md)
    hits = check_prose_punctuation.find_violations(prose)
    assert hits == [(6, "em-dash (U+2014); use a comma, colon, or period")]


def test_clean_prose_passes():
    assert check_prose_punctuation.find_violations("a comma, a colon: done.") == []


def test_line_numbers_are_reported():
    hits = check_prose_punctuation.find_violations("clean\nbad — here\nclean")
    assert hits == [(2, hits[0][1])]


# ---------------------------------------------------------------------------
# file handling: Markdown prose (code excluded), Python docstrings only, opt-out marker
# ---------------------------------------------------------------------------


def test_markdown_file_is_scanned(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("A sentence — with an em-dash.\n", encoding="utf-8")
    assert check_prose_punctuation.check_file(md)


def test_exempt_marker_skips_file(tmp_path):
    md = tmp_path / "generated.md"
    md.write_text(
        "<!-- racecar:prose-exempt -->\nA sentence — with an em-dash.\n",
        encoding="utf-8",
    )
    assert check_prose_punctuation.check_file(md) == []


def test_python_docstring_is_scanned_code_is_not(tmp_path):
    py = tmp_path / "mod.py"
    py.write_text(
        'x = "a code string — not prose"\n\n\ndef f():\n    """Doc — bad."""\n',
        encoding="utf-8",
    )
    hits = check_prose_punctuation.check_file(py)
    # Only the docstring on line 5 is flagged; the code string on line 1 is not.
    assert [lineno for lineno, _ in hits] == [5]


# ---------------------------------------------------------------------------
# commit-message mode
# ---------------------------------------------------------------------------


def test_commit_message_with_em_dash_fails(tmp_path):
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("feat: add a thing — and another\n", encoding="utf-8")
    assert check_prose_punctuation.main(["--commit-msg", str(msg)]) == 1


def test_commit_message_comments_are_ignored(tmp_path):
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(
        "feat: add a thing\n# a git comment — with an em-dash\n", encoding="utf-8"
    )
    assert check_prose_punctuation.main(["--commit-msg", str(msg)]) == 0


def test_clean_files_pass_via_main(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("All clean here.\n", encoding="utf-8")
    assert check_prose_punctuation.main([str(md)]) == 0
