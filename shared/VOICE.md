# Voice

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first

Voice for prescriptive writing in this repo: standards and rules that precede action, and the review outputs produced by the lenses ([`../arch-coherence/README.md`](../arch-coherence/README.md), [`../doc-coherence/README.md`](../doc-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md)) that assess compliance with them. Terminology is in [GLOSSARY.md](GLOSSARY.md).

- Terse. Single-sentence claims.
- No preamble. No apology when correcting.
- Challenge premises before accepting them.
- Use domain terms without gloss. Unfamiliar terms are in [GLOSSARY.md](GLOSSARY.md).
- Name the claim, then support it (cite the file, line, or contract output).
- Numbered lists and tables over prose when scanning multiple items.
- No emojis. Ever.
- No em-dashes in prose. Use a comma, colon, parentheses, or period. The ban is on human-facing prose only; machine-readable content is exempt. That covers code embedded in prose (fenced blocks and inline code spans in Markdown, everything outside a docstring in Python) and wholly machine-generated files (the CLAUDE.md router, the generated brief, manifests). Everything a reader takes as human-written prose is in scope; nothing a machine parses is.
- No hedging when the evidence is clear. If you are not sure, say you are not sure and stop there.
- Do not ask the reader to do emotional labor. No "sorry to say" or "I hate to point out."

## Enforcement

`scripts/check_prose_punctuation.py` gates the em-dash rule (and, by extension, the en-dash and the `--` sentence dash, the two substitutes a writer reaches for once the em-dash is gone). It scans commit messages at the commit-msg stage and staged prose at the pre-commit stage: Markdown prose (fenced code blocks and inline code spans are machine-readable and skipped), docstrings only for Python (code is not prose). The commit message is always human-voiced, so it is scanned unconditionally. A genuinely machine-generated file claims the carve-out inclusively, not through a central ignore-list, by carrying the marker `racecar:prose-exempt` in any comment form; a generator emits it, and a hand-authored file cannot silently inherit it.
