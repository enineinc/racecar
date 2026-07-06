---
pnode: [../README.md]
---

# Operational discipline

Accessed via [`../README.md`](../README.md), the human storefront. Agents receive this file force-loaded via `CLAUDE.md` and do not read README.

Operational discipline for agent execution — applies during review-lens analysis ([`../arch-coherence/README.md`](../arch-coherence/README.md), [`../doc-coherence/README.md`](../doc-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md)), where reads, greps, and test runs are expensive, and during general implementation work. Tool calls are not locally cheap; cost compounds across the conversation. State-changing tool calls compound worse — a wrong probe wastes a turn, a wrong mutation wastes recovery.

## Rules

Ordered from independent (universal precondition for any action) to dependent (presumes a workflow already in flight).

1. **Check before mutate.** Before any state-changing action — `pip install`, `mkdir`, `kill`, `createdb`, `git branch -D`, `npm install` — run the cheap non-destructive probe first (`python -c "import X"`, `pip show X`, `ls`, `pgrep`, `psql -l`, `git branch --list`). If the probe says the action is unnecessary or unsafe, skip or ask. Non-destructive intelligence beats destructive intelligence: a probe that returns "already there" costs one turn; a mutation that clobbers a venv, a database, or an in-flight branch costs the rest of the session.

2. **Parallel independent reads.** When checking N unrelated files or symbols, issue all reads and greps in a single assistant turn. Serial only when each lookup informs the next.

3. **Audit before fix.** When tests fail or a refactor breaks call sites, grep for the full set of broken patterns first. Report the inventory before making any change. No fix-the-first-occurrence-then-rerun loops.

4. **Group failure modes before fixing.** On a multi-failure test run, cluster failures by root cause first. Do not fix the first failure and rerun. Five tests failing from one shared cause get fixed once, not five times.

5. **Script mechanical changes.** Three or more identical-shape edits is a script (Python or `sed`), applied once, verified once. Not an `Edit`-tool loop. Identical-shape means the change can be expressed as one pattern; if each edit needs its own judgement or its own commit message, the loop is correct.

6. **The test suite is not a debugger.** Use targeted runs (single test, single file, single module) to iterate. Reserve the full suite for confirming completion, not for searching the failure space. If you find yourself rerunning the full suite to see what changed, you are debugging through it — stop, read the failure, narrow the run.

## Completion-claim rules — guardrails on declaring "done"

Rules 1-6 apply during execution. Rules 7-12 apply at the seam between
work and reporting back. They exist because tests passing, agents
returning, and dashboards reading green are evidence of activity, not
proof of correctness. The pattern they prevent: declaring something
done that isn't, on the strength of activity rather than verification.

7. **Never claim done without the production-path command and its exit
   code.** Before marking any feature, stage, or fix `done` in a
   CHANGELOG, plan file, status report, or user-facing message,
   identify the user-facing command that exercises this work
   (typically `python -m <pkg>` or equivalent), run it against
   realistic data (not the synthetic-fixture path the tests use), and
   paste the exact command and its exit code in the doc. No exit code
   → no `done`. Test-pass alone is not equivalent — tests can and do
   route around production paths (see rule 11).

8. **Agent workaround keywords are stop signals.** When reading any
   agent or subagent report, the phrases "open-coded", "worked
   around", "pivoted to", "skipped because", "marked xfail",
   "instead of fixing", "deferred for later", "couldn't ... so I ..."
   mean *the agent encountered a real bug and built around it*. Each
   is a finding to surface, not a solve to accept. The corresponding
   plan row stays `needs_review`; the bug becomes part of the next
   user turn, not part of the completion summary. There is no version
   of these phrases that is allowed to silently advance the plan.

9. **Numbers that should be equal across agents must be checked.**
   When multiple agents (or one agent's multiple reports) emit counts
   for analogous things — tuples per batch, rows per dataset, files
   per stage, percentile counts per output — compare them before
   accepting any as `done`. A discrepancy of more than ~10% on
   analogous reports is a stop condition. "They're just different"
   without a *specific* reason that survives a second look is the
   wrong answer; surface to the user.

10. **Doc invariants need test code.** Any falsifiable property stated
    in a `CLAUDE.md`, ADR, or in-tree contract doc — "all X emit Y",
    "every Z preserves W", "the output schema is always P" — must have
    a corresponding test assertion that reads the source-of-truth
    constant and verifies the property. Golden / snapshot / regression
    tests are *evidence of current state*, not enforcement of
    invariants; they lock whatever was captured, including bugs. When
    writing a doc invariant, write the test in the same change. When
    auditing existing invariants, the audit question is: does a test
    exist that would fail if this invariant is violated? If not, the
    invariant is aspirational — either add the test, or mark the doc
    line as aspirational.

11. **Tests that route around production are bugs.** If a test imports
    a helper or open-codes a loop because the direct production path
    "fails" or "doesn't work yet," the production path is broken. The
    test author's choices are: surface the production bug as the
    finding, or mark the test `needs_review` / `xfail`. They are not:
    declare the surrounding plan row `done` because the test happens
    to pass. Smells to recognize when reviewing test code: open-coded
    loops mirroring an existing production function, helper modules
    that "set up" data the production path would have set up itself,
    comments like "called directly because X raises" or "open-coded
    because run_all_specs aborts." Each one is a finding.

12. **Banned completion vocabulary.** In any user-facing document or
    message, do not use "bulletproof", "production-ready", "100%
    complete", "fully covered", "comprehensive", "0 broken", or "no
    regressions" without exact command output backing each. These
    words are vibes, not claims. Substitute precision: "N tests
    passing", "exit code 0 from `<exact command>`", "verified against
    `<exact data state>`". The precision substitute survives review;
    the vibe word doesn't. If you find yourself typing a banned word
    about your own work, treat it as a self-stop signal — replace it
    with the falsifiable claim or delete it.

## Why this matters for review work

The lenses read broadly. Every serial grep, every redundant test run, every unbatched tool call multiplies against the size of the codebase under review. A review that should take one inventory pass and one report becomes a reread loop, and the owner pays in tokens and wall time for nothing.

State-changing actions multiply worse. A probe that returns "already installed" is a one-turn correction; a destructive action against the wrong target is unrecoverable inside the conversation.

## Failure modes to recognize

- Treating each tool call as locally cheap. A 50-second test run feels like one unit; eight of them is the same task done badly.
- Mutating without probing. Reaching for `pip install` or `mkdir` when `pip show` or `ls` would have settled the question in one turn.
- Verifying each step instead of committing to a multi-step plan. Useful for novel work, wasteful for mechanical work.
- Defaulting to serial tool calls when in doubt. If the calls are independent, parallel is the rule.
- Following the smell, not the cause. Five tests failing from one shared cause get fixed once, not five times.

### Completion-claim failure modes

- **Counting completions instead of reading values.** "35 goldens captured" is activity; "35 goldens all produce 456 tuples" is verification. The first is what got reported; the second is what mattered.
- **Treating agent reports as proxies for production.** An agent reports `done` based on the tests it ran. The production CLI path may still be broken. Rule 7 is the antidote.
- **Accepting workarounds because they pass.** A test that open-codes a production loop passes by definition — it never calls the broken code. Green status is meaningless if the production path was sidestepped.
- **Pinning bugs with goldens.** Goldens lock current behavior. If the current behavior is wrong, the goldens enshrine the wrong behavior as the contract. Rule 10 is the only protection.
- **Vibe words as claims.** "Bulletproof" is a vibe. "2168 tests pass; `python -m gfem.radiant run --all` exits 0" is a claim. The first is unverifiable; the second is.
- **Celebrating coverage when invariants drifted.** "100% of specs have goldens" tells you nothing about whether the goldens enforce the documented contracts. Coverage of mechanics ≠ coverage of correctness.
