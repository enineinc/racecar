"""Mirror a template tree into an output tree, substituting placeholders.

Each template directory under arch-coherence/templates/<name>/ mirrors the target output
tree exactly: render_tree writes every file to out/<same relative path>, applying `subs`
(placeholder -> replacement) to its text. Empty files (package __init__.py) copy as empty;
*.sh files are made executable. A generator copies its static tree with render_tree, then
overlays the manifest-interpolated files (settings base, urlconf includes, per-vertical
adapters) on top -- so the template directory is a literal picture of what gets generated."""

from pathlib import Path


def render_tree(template_dir: Path, out: Path, subs: dict[str, str] | None = None) -> None:
    """Copy template_dir into out 1:1, applying `subs` placeholder substitutions per file.

    Constraints: substitution is a global str.replace over each file's text, so placeholder
    keys must be collision-proof sentinels (the __NAME__ / {name} convention) that cannot
    occur in real file content. Templates must be text (read as UTF-8); empty directories are
    not created (every package dir carries an __init__.py)."""
    subs = subs or {}
    for src in sorted(template_dir.rglob("*")):
        if not src.is_file():
            continue
        dest = out / src.relative_to(template_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text()
        for placeholder, value in subs.items():
            text = text.replace(placeholder, value)
        dest.write_text(text)
        if src.suffix == ".sh":
            dest.chmod(0o755)
