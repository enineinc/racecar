# Drift

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Drift is the gradual divergence of a system from itself — between two places that should agree, or between what the system is and what it was meant to be. Entropy is the enemy this whole framework fights; this file is the doctrine for fighting it constantly. Terminology: [GLOSSARY.md](GLOSSARY.md).

## The asymmetry

Entropy is **monotonic and continuous**. It rises with every commit, every dependency bump, every day a doc is not re-checked against the code it describes. A defense that is **discrete and pull-triggered** — a lens a human remembers to invoke — cannot keep pace with a process that never pauses. The gap between "drift rises on every change" and "review happens when invoked" is, exactly, the drift that accumulates.

A defense counts as constant only if it is one of two things:

- **Structural** — remove the freedom to drift, so the divergence cannot occur. Highest leverage.
- **Automatic** — detect on every change, without waiting to be asked.

Manual episodic review is necessary but insufficient on its own. It is the last tier, not the first.

## Drift is frame-relative

There is no answer to "is this drift?" without "against what frame?" The same fact is drift at one canvas size and noise at another.

- At the **function** frame, a renamed variable whose callers were not updated is drift.
- Zoom to the **module** and that rename is invisible — internal, already consistent.
- Zoom to the **system** and a module that is *perfectly* internally consistent can be the drift: it no longer fits the system's intent, or it has independently grown a second model of a concept that already has a home elsewhere.

Two consequences follow, and they are the ones that matter.

**Local coherence can be global drift.** The dangerous case is not the broken link. It is the subsystem where every part passes every local check and the *whole* has diverged from its purpose — two clean `User` models built by two teams, each locally correct, together a single global drift. This is [one-home-per-rule](GLOSSARY.md#one-home-per-rule) at system scale, and no local lens can see it, because every artifact is locally clean.

**Local fixes mask global drift.** Tidying a symptom destroys the evidence that pointed to the root. Fix fourteen stale pointers one by one and you have spent the budget and erased the smell that would have said "this module moved and nobody asked whether it should have." The cleanup makes the system *look* coherent while the structural divergence is now harder to find, not gone.

### The rule

**Resolve drift at the largest frame that still explains the symptom; fix there.** Report the global root; list local symptoms as children. Never fix a local symptom before asking whether it is the surface of a global drift — the local fix is what destroys the global signal.

This extends "root causes beat surface counts" (in every lens) with the part that rule leaves implicit: the root may live at a *larger frame* than any of its symptoms, and may itself have no symptom severe enough to trip a lens. The most damaging drift routinely presents with the weakest local evidence. Severity is therefore **frame-aware**: a finding that is a Nit at the file frame can be a Blocker at the system frame. Grade it at the frame where the damage lands, not the frame where the symptom shows.

## The three tiers

Ordered by leverage. Each tier owns a frame; none substitutes for another.

**Tier 1 — Eliminate the drift surface (structural; prevention).** The cheapest drift to fix is the drift that cannot occur. Every duplicated fact, restated rule, cloned example, and copy-pasted lens scaffold is a future divergence; removing it removes the possibility, not just the instance. This is the only tier that fights *global* drift preventively — [one-home-per-rule](GLOSSARY.md#one-home-per-rule) applied at system scale keeps two subsystems from growing two models of one concept. Mechanize identity-or-pointer wherever a fact is asserted in two places; the vocabulary-identity check in [doc-coherence](../doc-coherence/README.md#mechanical-pre-pass) is the seed — generalize it. When a lens finds duplication, ranking "collapse to one home" above "sync the copies" is not optional; syncing copies is taking the loan.

**Tier 2 — Detect on every change (automatic; local, overridable).** The mechanical passes — `check_docs.py`, `import-linter`, linters, type checkers — run on every commit as local pre-commit hooks; racecar ships them in [`../templates/classic/pre-commit-config.yaml`](../templates/classic/pre-commit-config.yaml). This is the tier that makes the fight constant rather than remembered. It blocks the commit on failure, but the owner can override — **local and overridable**, not a CI gate that decides without the owner in the loop ([OWNERSHIP](OWNERSHIP.md)). The check confirms; it does not authorize.

This tier must be **purely deterministic — scripts and exit codes, zero LLM judgment in the loop.** The detector must have lower entropy than the thing it watches; a script has none, a model has plenty. An LLM in the per-change path is self-defeating on two counts: it executes the same check differently run to run, so you cannot tell a real finding from the model having a different day, and it dresses a one-line predicate in multi-step reasoning — doing simple things with complexity. Put your noisiest component in the loop meant to run constantly and silently and you have made the detector a drift source. The hook is legitimate as a script-runner and forbidden as a model-invoker.

Two ceilings are non-negotiable. A per-change check sees a diff and is therefore **structurally blind to global drift** — invest here without Tier 3 and you get a system that is everywhere-locally-clean and globally rotten. And anything that needs **judgment** — semantic doc-vs-code agreement, dead-rule detection — cannot be demoted here no matter how tempting, because judgment means the LLM and the LLM does not belong in the constant loop. Those belong to Tier 3.

**Tier 3 — Periodic global sweep (manual; the system frame).** The lens, reframed from "review this diff" to "sweep the standing tree for the drift the per-change tiers structurally cannot catch": semantic divergence where doc and code are each well-formed but disagree, dead rules, homes that lost their enforcement, two subsystems converging on one concept. This is where global drift is caught, which is why piling up Tier 2 checks can never replace it. Trigger on **time or change-volume** — weekly, or every N commits — because entropy is a function of both, not either alone.

This is the only tier where LLM judgment belongs, and even here it is **fed by deterministic pre-filtering**: the ledger and the mechanical-pass output narrow the model to the residue that genuinely needs judgment, rather than turning it loose on the whole tree to reinvent — sloppily, at complexity — what a script already does exactly. Match the tool to the task: deterministic checks for what a predicate can decide, judgment only for what it cannot.

## The ledger (the clock)

Drift accumulates silently in the corners no one points the lens at, and the framework has no way to know which corners those are. The fix is a **drift ledger**: for every rule-home and every doc that describes code, record the commit SHA or content hash it was last verified against. On each sweep, anything whose *subject* changed since its last verification floats to the top.

This is the difference between hoping you point the lens at the right file and the system handing you a ranked queue of where the rot is most likely. A clock plus a coverage map. Without it, "constant" is aspirational — you are still relying on memory to locate drift, and memory is precisely what entropy defeats.

## What this is not

This doctrine detects and surfaces; it does not authorize. Every tier reports to the owner, who decides what to fix and when. Automating *detection* to run constantly does not move *responsibility* off the owner — see [OWNERSHIP](OWNERSHIP.md). A green ledger is confirmation, not a merge gate.
