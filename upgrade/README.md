# Upgrade — bring a repo in line with racecar, with nuance

Accessed via [`../README.md`](../README.md) / [`../CLAUDE.md`](../CLAUDE.md). If you arrived here directly, read that first.

This is the **nuanced upgrade** procedure: take an existing project and move it toward current racecar without assuming everything already in the repo is wrong. A naive upgrade treats the standard as truth and the repo as deviation, then clobbers. This one does not. The existing repo is a set of decisions, not a pile of mistakes, and some of those decisions are better than racecar's defaults or are legitimate in a context racecar does not know.

Distinct from [`racecar-normalize`](../normalize/SKILL.md), which is the mechanical floor: sync the canonical check scripts, run every checker, report every finding. Upgrade *drives* normalize and then adds the judgment layer normalize deliberately lacks: it decides, per divergence, what the divergence *means* and who should change.

## The one rule: every divergence gets one of three verdicts

For each place the repo differs from current racecar, classify before you act. The burden of proof sits on **Conform**, never on the repo.

- **Conform** — the divergence is drift or accident, and base is strictly better here. Bring it to base. (A stale check script, a missing `arch` step, a pylint disable that drifted, a packaging shape that is simply wrong.)
- **Declare** — the divergence is intentional and defensible. **Preserve it, and record it** in the structured override home so it is explicit and survives every future upgrade. (A project that genuinely needs an extra dev tool, a non-canonical module name with a reason, a target the project added.) Declared divergence is not a violation; undeclared divergence is the drift racecar fights.
- **Escalate** — the divergence reveals that racecar's default is *wrong* or over-broad. The standard changes, not the repo. Emit it as a racecar-improvement finding and leave the repo alone. This is the falsification loop made first-class: real repos are how racecar's assertions get scoped (the proving-ground direction, project → racecar).

If you cannot tell which verdict applies, that is a question for the owner, not a default to Conform. Defaulting to Conform is the naive failure this skill exists to prevent.

## The override home

Declared divergences live in the project's library pyproject under `[tool.racecar.overrides]`, the same `[tool.racecar.*]` namespace as `[tool.racecar.faces]`. One machine-readable home, so an upgrade is a deterministic function of `base + declared overrides` and re-running it is idempotent. The project's `README` / `CLAUDE.md` *renders or points at* that home for humans; it never keeps a second hand-maintained copy (two homes for one fact is Tier-1 drift).

```toml
[[tool.racecar.overrides]]
target = "Makefile"          # file or canon key the project diverges on
what   = "adds a `bench:` target"
why    = "domain benchmark suite; no racecar equivalent"
```

Until the mechanical fold (a synced `racecar.mk` base plus override composition) ships, `[tool.racecar.overrides]` is the **record of intent**: it makes re-porting deterministic and auditable, and it is what an undeclared-divergence check will gate against. State that limit plainly; do not pretend the fold is automatic yet.

## Procedure

Detect-first, judge-second, owner-authorized, idempotent.

1. **Detect mechanically (no judgment yet).** Three sub-steps; do them in order and do not skip the verify.

   **1a. Copy the canonical checks into the repo, then VERIFY they landed.** Run the exact command (this is what `racecar-normalize` and `make sync-scripts DEST=<repo>` wrap):

       python3 <racecar>/scripts/sync_scripts.py --dest <repo> --templates

   Then confirm before going on: `ls <repo>/scripts/check_*.py` must list the synced checks (`check_packaging`, `check_upward_imports`, `check_cli_commands`, `check_face_orchestration`, `check_docs`, `check_subsystem_docs`, `check_todo_format`, `check_claude_shape`, `check_file_placement`, `check_brief`). **A skipped or misdirected copy is the silent failure that breaks every later step** — the scripts the Makefile invokes would not exist. If they are not present, the copy did not run; fix the `--dest` path and re-run before proceeding.

   **1b. Run the checkers** from `<repo>` (`--root <repo>` or from inside it) for the gap list: `check_packaging`, `check_docs`, `check_subsystem_docs`, `check_cli_commands`, `check_face_orchestration`.

   **1c. Diff the config.** Run `python3 <racecar>/scripts/check_config_drift.py --root <repo>` to see exactly how the repo's `Makefile` and `.pre-commit-config.yaml` differ from `templates/classic/` (it normalizes the per-project shape variables so they are not reported as drift). It is racecar-run-only — it needs `templates/classic/`, so it runs from the racecar checkout, not the adopter.

   The union of 1b and 1c is the **divergence set**. This step assumes nothing about right or wrong; it only finds *where* the repo differs.
2. **Classify each divergence (the nuance).** For each, investigate *why* it exists before deciding: read the surrounding code, `git log` / `git blame` the line, the project's own README / CLAUDE, any comment. Assign Conform / Declare / Escalate **with the evidence that justifies it**. Never conform a divergence you have not explained.
3. **Present the plan; the owner authorizes.** Show the three buckets with reasoning. The owner ratifies per item ([`../shared/OWNERSHIP.md`](../shared/OWNERSHIP.md): tooling confirms, the owner authorizes). Nothing is applied on inferred consent.
4. **Apply, idempotently.** Conform → bring to base. Declare → preserve the divergence and write the `[tool.racecar.overrides]` record. Escalate → write the racecar-improvement finding; the repo is untouched. A second run recognizes declared overrides and re-surfaces only genuinely new drift.
5. **Structural uplift toward `lib → api → faces` (opt-in phase, equally nuanced).** Only if the project wants it. Follow [`../arch-coherence/FACES.md`](../arch-coherence/FACES.md) §11, but derive the verticals from the *existing* structure rather than imposing a cathedral on a one-file tool. Map current modules to roles (`lib`/`api`/face); where names are non-canonical and intentional, declare them in `[tool.racecar.faces]` rather than renaming working code. Respect the single-face `api == lib` collapse. Use `check_face_orchestration` (advisory) as the guide, not a gate: a non-classifiable vertical is a conversation, not an order.
6. **Modernize the human-facing docs (judgment, not a gate).**
   - **README.** There is no README checker by design — gating on section presence is theater (the same reason the faces wall came down). So review the repo's README against the standard shape in [`../templates/classic/README.md`](../templates/classic/README.md): a one-paragraph value prop, then who-what → Getting Started → Using → when/where/why, with `## Contributing` / `## License` closers. Propose a restructure for the owner to approve; **reorder and reframe the repo's *actual* content and voice — never invent claims or import boilerplate.** A README that diverges intentionally is fine; this is a proposal, never enforced.
   - **Brief.** If a knowledge brief sits at the old `docs/<repo>/<REPO>.md` path, move it to `docs/summary/<REPO>.md` (the current convention; `check_brief` only looks there) and update any in-repo references to the old path. If no brief exists, skip. Regenerate it with `/racecar-llm-summary` only if the owner wants it current, not as part of the move.
7. **Verify.** `make check` / `lint-imports` / the checkers come back green, or the remainder is *declared* or *escalated*, never silently skipped. A silent skip is the no-silent-omission violation ([`../shared/OPERATIONAL.md`](../shared/OPERATIONAL.md)).

## What it is not

- Not a clobber. It never overwrites a customized `Makefile` / pyproject; it reconciles them.
- Not a one-way service. Escalate exists because the repo can be right and racecar wrong.
- Not fully mechanized yet. The divergence detection leans on the existing checkers plus an explicit template diff; the classification is judgment fed by that deterministic floor (discrete-first, LLM-last); the auto-fold (`racecar.mk` + override composition) and the undeclared-divergence gate are the named companion builds, not claimed as present.

## Voice

Common voice: [`../shared/VOICE.md`](../shared/VOICE.md).

## Invocation

> Load `upgrade/README.md`. Upgrade this repo toward current racecar. Detect divergence mechanically first, then classify each as Conform / Declare / Escalate with evidence, present the buckets for my authorization, and apply idempotently. Do not assume anything pre-existing is wrong; the burden of proof is on conforming.

> Using `upgrade/README.md` §5, restructure this repo toward `lib → api → faces` from its existing structure, declaring intentional non-canonical names rather than renaming working code.
