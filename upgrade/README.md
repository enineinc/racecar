# Upgrade: bring a repo in line with racecar, with nuance

Accessed via [`../README.md`](../README.md) / [`../CLAUDE.md`](../CLAUDE.md). If you arrived here directly, read that first.

This is the **nuanced upgrade** procedure: take an existing project and move it toward current racecar without assuming everything already in the repo is wrong. A naive upgrade treats the standard as truth and the repo as deviation, then clobbers. This one does not. The existing repo is a set of decisions, not a pile of mistakes, and some of those decisions are better than racecar's defaults or are legitimate in a context racecar does not know.

Distinct from [`racecar-normalize`](../normalize/SKILL.md), which is the mechanical floor: sync the canonical check scripts, run every checker, report every finding. Upgrade *drives* normalize and then adds the judgment layer normalize deliberately lacks: it decides, per divergence, what the divergence *means* and who should change.

## The one rule: every divergence gets a verdict

For each place the repo differs from current racecar, classify before you act. First place the divergence on one of two axes, because the axis sets the default:

- **Canon**: the parts racecar defines as byte-identical in every repo: `racecar.mk`, the synced check scripts, the `[tool.*]` config block, the canonical pre-commit hook set. A repo cannot "decide" to differ here, because the thing is the same everywhere by construction; divergence is drift with nothing to lose. **Conform is unconditional**, no burden of proof, no nuance. (This is what makes conformance *lossless*: the fold keeps project customization in a separate home, so conforming the canon half destroys no local decision. A monolithic Makefile is canon entangled with project targets, which is why it has to be migrated, not kept.)
- **Project decision**: architecture, naming, which targets exist, business-logic shape: the parts the repo legitimately knows better than racecar does. Here the **burden of proof sits on Conform, never on the repo**, and the verdicts below apply.

The two verdicts apply on the project-decision axis:

- **Conform**: the divergence is drift or accident, and base is strictly better here. Bring it to base. (A stale check script, a missing `arch` step, a pylint disable that drifted, a packaging shape that is simply wrong.)
- **Escalate**: the divergence reveals that racecar's default is *wrong* or over-broad. The standard changes, not the repo. Emit it as a racecar-improvement finding and leave the repo alone. This is the falsification loop made first-class: real repos are how racecar's assertions get scoped (the proving-ground direction, project → racecar).

Two verdicts, not three. A divergence that is genuinely intentional and right but should not change the standard is simply **kept**: documented by one comment at its one home (the owned `Makefile`, the site in the code), never a central registry. There is no `[tool.racecar.overrides]` and no "declared divergence" ledger: a parallel list of exceptions is a second home for facts the code already states, the Tier-1 drift racecar fights. Where the structure itself absorbs intentional divergence, most of all the Makefile fold ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md) §7), where the owned `Makefile` holds project customization and the canonical `racecar.mk` (identical in every repo) holds canon, there is nothing to record at all.

If you cannot tell which verdict applies, that is a question for the owner, not a default to Conform. Defaulting to Conform is the naive failure this skill exists to prevent.

## Procedure

Detect-first, judge-second, owner-authorized, idempotent.

1. **Detect mechanically (no judgment yet).** Three sub-steps; do them in order and do not skip the verify.

   **1a. Copy the canonical checks into the repo, then VERIFY they landed.** Run the exact command (this is what `racecar-normalize` and `make sync-scripts DEST=<repo>` wrap):

       python3 <racecar>/scripts/sync_scripts.py --dest <repo> --templates

   Then confirm before going on: `ls <repo>/scripts/check_*.py` must list the synced checks (`check_packaging`, `check_upward_imports`, `check_cli_commands`, `check_surface_orchestration`, `check_docs`, `check_subsystem_docs`, `check_todo_format`, `check_file_placement`, `check_brief`), and `<repo>/racecar.mk` must exist (the canonical file, identical in every repo). **A skipped or misdirected copy is the silent failure that breaks every later step**: the scripts the Makefile invokes would not exist. If they are not present, the copy did not run; fix the `--dest` path and re-run before proceeding.

   **1b. Run the checkers** from `<repo>` (`--root <repo>` or from inside it) for the gap list: `check_packaging`, `check_docs`, `check_subsystem_docs`, `check_cli_commands`, `check_surface_orchestration`. Watch `check_packaging`'s Makefile findings specifically: `no-racecar-mk` (a pre-fold monolith), `racecar-mk-not-included` (the half-migrated state: `racecar.mk` was dropped but the monolithic `Makefile` never `include`s it, so the canonical build is inert), or `racecar.mk` `missing-file`. Each names a *fold-adoption* divergence, which 1c does not cover.

   **1c. Diff the config.** Run `python3 <racecar>/scripts/check_config_drift.py --root <repo>` to see how the repo's `.pre-commit-config.yaml` differs from `templates/classic/`. (Makefile *content* drift is not a category: under the fold the owned `Makefile` is project-specific by design and `racecar.mk` is the same canonical file in every repo, so there is nothing per-repo to diff. Fold *adoption* is a different thing (whether the repo is on the fold at all) and is caught by `check_packaging` in 1b, not here.) It is racecar-run-only: it needs `templates/classic/`, so it runs from the racecar checkout, not the adopter.

   **1d. Assert no override.** Run `python3 <racecar>/scripts/check_racecar_overrides.py --root <repo>`. It enforces the two invariants this section assumes: the repo carries no non-canon `[tool.racecar]` key (the `surface` / `roles` / `subsystem-docs` bindings are allowed; there is no local override registry such as `[tool.racecar.overrides]`), and its `racecar.mk` is byte-identical to canon (the "identical in every repo" invariant, verified rather than trusted, so a hand-edit of shape content is caught). Like 1c it is racecar-run-only. A finding here is a Conform, not an Escalate: the fix is to move customization into the owned `Makefile` and restore canon, or to raise the standard.

   The union of 1b, 1c, and 1d is the **divergence set**. This step assumes nothing about right or wrong; it only finds *where* the repo differs.
2. **Classify each divergence (the nuance).** For each, investigate *why* it exists before deciding: read the surrounding code, `git log` / `git blame` the line, the project's own README / CLAUDE, any comment. Assign Conform / Escalate, or keep-with-comment, **with the evidence that justifies it**. Never conform a divergence you have not explained.
3. **Present the plan; the owner authorizes.** Show the buckets with reasoning. The owner ratifies per item ([`../shared/OWNERSHIP.md`](../shared/OWNERSHIP.md): tooling confirms, the owner authorizes). Nothing is applied on inferred consent.
4. **Apply, idempotently.** Conform → bring to base. Escalate → write the racecar-improvement finding; the repo is untouched. Intentional-and-right → keep it, with one in-place comment. A second run re-surfaces only genuinely new drift. The Makefile fold makes this automatic: `racecar.mk` is the canonical file copied verbatim (identical everywhere; it self-detects the shape), and a Makefile *already on the fold* (a thin `include racecar.mk` plus project targets) is left alone.

   **The one Makefile action upgrade must still take is fold adoption (a Conform).** `sync` drops `racecar.mk` but never touches the existing `Makefile`, so a pre-fold monolith ends up beside an inert `racecar.mk` nothing includes, and `check_packaging` flags this `racecar-mk-not-included` (or `no-racecar-mk` if sync has not run yet). This is **not** "the owned Makefile, leave it alone"; it is drift, and base is strictly better. Migrate by hand: move the canonical recipes out of the `Makefile` (they now live in `racecar.mk`), add `include racecar.mk`, and keep only the genuinely project-specific targets and variable overrides. Never clobber a customized recipe: a project target stays; a *canonical* target verbatim-equal to `racecar.mk`'s is removed because the include now supplies it. Re-run `check_packaging`: green, or the remaining Makefile divergence is kept-with-comment in the owned `Makefile`.
5. **Structural uplift toward `lib → api → surfaces` (opt-in phase, equally nuanced).** Only if the project wants it. Follow [`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §11, but derive the verticals from the *existing* structure rather than imposing a cathedral on a one-file tool. Map current modules to roles (`lib`/`api`/surface); where names are non-canonical and intentional, declare them in `[tool.racecar.roles]` (a positive architecture manifest, not an exception list) rather than renaming working code. Respect the single-surface `api == lib` collapse. Use `check_surface_orchestration` (advisory) as the guide, not a gate: a non-classifiable vertical is a conversation, not an order. The heavier move under this uplift is owned elsewhere, one home: the surfaces (`server/` over `src/<pkg>/api`) by [`racecar-create-server`](../create-server/SKILL.md) ([`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md)). Reuse it rather than reimplementing it.
6. **Modernize the human-facing docs (judgment, not a gate).**
   - **README.** There is no README checker by design: gating on section presence is theater (the same reason the surfaces wall came down). So review the repo's README against the standard shape in [`../templates/classic/README.md`](../templates/classic/README.md): a one-paragraph value prop, then who-what → Getting Started → Using → when/where/why, with `## Contributing` / `## License` closers. Propose a restructure for the owner to approve; **reorder and reframe the repo's *actual* content and voice; never invent claims or import boilerplate.** A README that diverges intentionally is fine; this is a proposal, never enforced.
   - **Brief.** If a knowledge brief sits at the old `docs/<repo>/<REPO>.md` path, move it to `docs/summary/<REPO>.md` (the current convention; `check_brief` only looks there) and update any in-repo references to the old path. If no brief exists, skip. Regenerate it with `/racecar-llm-summary` only if the owner wants it current, not as part of the move.
7. **Verify.** `make check` / `lint-imports` / the checkers come back green, or the remainder is *kept-with-comment* or *escalated*, never silently skipped. A silent skip is the no-silent-omission violation ([`../shared/OPERATIONAL.md`](../shared/OPERATIONAL.md)).

## What it is not

- Not a clobber. It never overwrites the owned `Makefile` or pyproject; it reconciles them. (`racecar.mk` *is* overwritten, but it is canonical content identical in every repo, not yours; your customization lives in the owned `Makefile`.)
- Not a one-way service. Escalate exists because the repo can be right and racecar wrong.
- Not fully mechanized. The divergence detection leans on the checkers plus a pre-commit template diff; the classification is judgment fed by that deterministic floor (discrete-first, LLM-last). The Makefile fold (`racecar.mk` identical in every repo, self-detecting the shape from the layout; [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md) §7) removes Makefile *content* divergence as a category, but fold *adoption* (migrating a pre-fold monolith onto the fold) is a manual upgrade step, caught by `check_packaging` and applied in step 4. There is no override-composition step, because there are no overrides.

## Voice

Common voice: [`../shared/VOICE.md`](../shared/VOICE.md).

## Invocation

> Load `upgrade/README.md`. Upgrade this repo toward current racecar. Detect divergence mechanically first, then classify each as Conform / Escalate with evidence (keep an intentional-and-right divergence in place with a comment), present for my authorization, and apply idempotently. Do not assume anything pre-existing is wrong; the burden of proof is on conforming.

> Using `upgrade/README.md` §5, restructure this repo toward `lib → api → surfaces` from its existing structure, declaring intentional non-canonical names in `[tool.racecar.roles]` rather than renaming working code.
