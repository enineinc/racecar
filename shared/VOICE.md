---
pnode: [../README.md]
---

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
- No em-dashes in prose. Use a comma, colon, parentheses, or period. This is a voice convention, not a mechanically gated rule: apply it to human-facing prose (Markdown, docstrings, commit messages) and leave machine-readable content alone. The em-dash reads as a tell of unedited machine text, which is the reason to keep it out; the en-dash and the `--` sentence dash are the same tell and the same fix, but none of the three is worth a checker, because the mechanical gate cost more in false positives (a `--` is a CLI option and a POSIX end-of-options marker far more often than a sentence dash) than the drift it caught.
- No hedging when the evidence is clear. If you are not sure, say you are not sure and stop there.
- Do not ask the reader to do emotional labor. No "sorry to say" or "I hate to point out."

The rules above are voice conventions, applied by the writer and caught in review. None is mechanically gated: the one prose checker racecar shipped (a dash gate) was retired because its false-positive rate exceeded its value. See `CHANGELOG.md`.
