# VOCABULARY.md — review-output literals

One home for the literals every racecar lens emits. Each lens README repeats them inline (so a reviewer reading the lens does not have to follow a link to know what to write); the inlined copies are kept in lockstep by the doc-coherence vocabulary-identity check in `doc-coherence/scripts/check_docs.py`.

## Severity

Severity values are literal: **Blocker / Major / Minor / Nit**.

- **Blocker** — must be fixed before ship. Breaks a non-negotiable rule (import cycle, broken navigation, correctness or security defect).
- **Major** — ships as canonical but is wrong (layer slip, misleading claim, engineering defect that compiles but is incorrect).
- **Minor** — local defect that does not propagate (depth-plus-one leak, prose tightening, naming nit beyond a hot path).
- **Nit** — taste / polish; safe to defer.

## Verdict

Verdict values are literal: **Ship / Revise / Rework**.

- **Ship** — no Blocker, no Major; remaining findings are deferrable.
- **Revise** — Major(s) present; fixable in the same review cycle.
- **Rework** — Blocker(s) present; the artifact must be restructured before re-review.

## Mechanization

The doc-coherence pre-pass scans every markdown file for lines of the form

```
<Class> values are literal: **<literal>**.
```

and asserts that, within each class (`Severity`, `Verdict`, or any future class), every occurrence carries the same literal. Drift between the three lens READMEs (or any future README that emits findings) is caught at pre-commit, not at human prose-review time.
