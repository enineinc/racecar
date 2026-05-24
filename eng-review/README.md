# Engineering Review — wrapper around gstack `plan-eng-review`

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

This is a wrapper review, not a standalone lens. Racecar's pre-pass runs first, gstack's `plan-eng-review` runs next, racecar's post-pass runs last — the three steps produce one unified verdict. Racecar contributes the idiosyncratic Python/Django rules the author cares about; gstack contributes the broader architectural and execution review. Running only one of them misses concerns the other owns.

**On gstack.** gstack is a separate Claude Code skill bundle the author uses (typically installed under `~/.claude/skills/gstack-*`); `plan-eng-review` is its opinionated engineering-review skill. If gstack is not installed, only the pre-pass and post-pass run — the wrapper is then incomplete, and the final Merge-findings step reduces to just the racecar output.

Pair with [arch-coherence](../arch-coherence/README.md) for structural DAG drift and [doc-coherence](../doc-coherence/README.md) for prose hygiene.

For language-specific hygiene applied in the post-pass, see [PYTHON.md](PYTHON.md) (mindset, naming, formatting, testing, linting, Definition of Done) and [DJANGO.md](DJANGO.md) (database/performance, security).

## How to use this file

1. Load this file in full.
2. **Pre-pass (racecar).** Check hard stops first — any hit ends the review immediately. Then apply the two checks and red-flag scan. Any Blocker from the pre-pass should be fixed or annotated before step 3 — gstack's broader review drowns in noise if the fast checks are dirty.
3. **Invoke gstack `/plan-eng-review`.** Delegate the broader engineering review: architecture, data flow, diagrams, edge cases, test coverage, performance, opinionated recommendations. gstack produces its own numbered findings.
4. **Post-pass (racecar).** Apply [PYTHON.md](PYTHON.md) and [DJANGO.md](DJANGO.md) as applicable. These are the Python/Django idiosyncrasies gstack does not opine on — stubs that ship as canonical Python, tests that exercise mocks instead of code, Django N+1 patterns, access-control mixins omitted on CBVs.
5. Merge findings from all three passes. Group by defect where one judgment call resolves several mentions. Keep racecar and gstack findings distinguishable — both are evidence; neither overrides the other.
6. If all three passes trip no Blockers, say so in one line and stop.

Do not summarize the artifact. Go straight to issues.

## Pre-pass: hard stops

These are unconditional. Any one found ends the review immediately — Blocker, Rework, stop.

- Template or example files named with a leading dot (`.env.example`, `.gitignore.template`) — dotfiles are hidden. A template must be visible. Name it `env.example`, not `.env.example`.
- Template files in the project root — the root is not a sandbox for orphaned templates. Templates live in a dedicated subdirectory (`something/templates/`).

## Pre-pass: the two engineering checks

1. **Scope honesty of names.** Do module names, function names, and API surfaces describe what the thing does — not what format it handles, not what incidental file it lives in, not what infrastructure it happens to use today? Canonical rules and worked examples live in [PYTHON.md §2 Naming](PYTHON.md#2-naming) (module naming, function naming, underscore discipline, type-hint discipline). For the same rule applied to document labels and sections, see [doc-coherence](../doc-coherence/README.md#the-five-document-checks), check 2.

2. **Operational traceability.** Does this artifact map to a concrete outcome? If it is a tool, is there a runbook that tells someone how to operate it? A feature without an operational home is debt, not value.
   - A new endpoint with no dashboard, no alert, no ownership note.
   - A CLI command with no entry in the `--help` catalog and no doc that says when to run it.
   - A migration script with no record of who owns rollback.

## Pre-pass: red flags — engineering

Scan for these. One line each.

- Dead code, contract-only stubs that nothing calls.
- Skeletons that would not lint — unused variables, functions with only a docstring body shipping as canonical.
- Untested code paths presented as canonical.
- Naming that hides function — modules named for the file type they parse instead of the concept they represent.
- Premature abstraction — one caller, three layers of indirection.
- Mutable defaults, hidden global state, implicit initialization.
- Error messages that name a symptom instead of a cause.
- Tests that exercise the mock, not the code.
- Comments that narrate the next line instead of explaining the decision.
- Type hints that lie — `Dict[str, Any]` for a known schema.
- Magic numbers without provenance — where did 4096 come from.
- Catch-all `except` that swallows the signal.
- Configuration scattered across code paths when one would do. (For config scattered across *files*, use [arch-coherence](../arch-coherence/README.md).)

## Post-pass: Python / Django idiosyncrasies

After gstack has run, load [PYTHON.md](PYTHON.md) and [DJANGO.md](DJANGO.md) and apply them to the artifact. These files carry the opinions gstack does not hold: naming rules beyond "scope honesty," formatter-as-canonical, no-inline-suppression, Django service-layer patterns, N+1 prevention, access-control mixins. Surfaces here tagged `[post]`.

## Mental models

**Least-privilege data access.** A module that has access to data it does not need for its primary job is a boundary leak, even if nothing breaks today. Isolate data as strictly as logic. If function `f` only needs `user.id`, do not hand it the whole `user` object.

**Opine, do not describe.** A review takes a position. Good review: "do X" or "do not do Y." Bad review: "X is a pattern that exists." Describing is easier and less useful.

## Decision patterns — engineering

- **Prefer the fewest moving parts.** Three modules that each do one thing well beat one module with three modes. Complexity shows up where it is needed, not everywhere.
- **Name the concept, not the implementation.** Canonical rule: [PYTHON.md §2 Naming](PYTHON.md#2-naming).
- **No shortcuts when the correct solution exists.** If the right fix takes longer, do the right fix. Workarounds accrete; clean fixes compound.
- **Compound fixes over workarounds.** A workaround is a high-interest loan. A clean fix is an investment. Do not take loans unless the building is on fire — and when you do, file the repayment issue before closing the PR.
- **Challenge the premise.** Half of bad work is the correct execution of the wrong thing. Audit the *why* before the *how*.
- **When in doubt, delete.** Dead code, half-built abstractions. Removing them is almost always the cheapest improvement available. Add back only on demand.

## Feedback format

- Numbered list. One defect per numbered entry; multiple occurrences of the same defect become indented children under one root.
- Tag each entry with the pass that caught it: `[pre]`, `[gstack]`, `[post]`. Downstream readers can tell which layer owns the finding.
- Each entry: `[pass-tag] File/Topic — severity — one-sentence description`.
- Severity values are literal: **Blocker / Major / Minor / Nit**. An engineering defect is Blocker when it breaks correctness or security; Major when it ships as canonical but is wrong; Minor/Nit otherwise. These are defaults; frame can override them — grade at the frame where the damage lands ([../shared/DRIFT.md](../shared/DRIFT.md#drift-is-frame-relative)).
- No preamble. Start with entry 1.
- End with a single verdict line. Verdict values are literal: **Ship / Revise / Rework**.

Example (shape only — substitute the artifacts under review):

```
1. [pre] MODULE_A/parser.py — Major — Module named for the format (`yaml_parser`). The job is config loading; YAML is incidental. Rename to `config.py`.
2. [gstack] MODULE_B/handler.py:42 — Major — Handler couples auth check to transport-layer concerns; missing service-level boundary.
3. [post] MODULE_C/models.py:18 — Major — `datetime.now()` used in a Django model; use `django.utils.timezone.now()` per DJANGO.md §1.
4. [pre] tests/test_api.py — Minor — Test asserts that the mocked client was called rather than that the response body is correct.

Verdict: Revise. 1, 2, 3 before ship; 4 next pass.
```

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).

## Invocation

> Load `eng-review/README.md`. Run the pre-pass (two checks + red flags), invoke gstack `/plan-eng-review`, then apply `eng-review/PYTHON.md` or `eng-review/DJANGO.md` as applicable. Emit one merged numbered list tagged `[pre]`/`[gstack]`/`[post]`, verdict at the end.

> Using `eng-review/README.md`, wrap gstack's review with racecar's Python/Django hygiene pass.

If all three passes trip no Blockers, say so in one line and stop.
