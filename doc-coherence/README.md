# Documentation Coherence — Update Protocol & Review Lens

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Covers the full documentation update workflow: the **update protocol** (what to do when editing a doc) and the **review lens** that validates the result (what to check before shipping the change). Pair with [arch-coherence](../arch-coherence/README.md) for the architectural DAG and [eng-review](../eng-review/README.md) for code-level hygiene.

## Update protocol

When updating any documentation file, apply these operations in order:

1. **PRESERVE** — Keep content that is still correct and relevant. Do not delete working documentation.
2. **ADD** — Write missing content: new features, new modules, new CLI flags, new architectural decisions.
3. **UPDATE** — Fix content that is incorrect: wrong function names, outdated descriptions, stale architecture.
4. **DELETE** — Remove content that is no longer relevant: references to removed functions, dead code paths, obsolete design decisions.
5. **REVIEW** — Apply the review lens below. No doc update ships without it.

## How to use the review lens

1. Load this file in full.
2. Run the **[mechanical pre-pass](#mechanical-pre-pass)** by invoking `scripts/check_docs.py` (command below). Bookkeeping drift — broken links, stale section numbers, drifted vocabulary, enforcement labels that no longer match the rule — surfaces first and collapses into a single root rather than inflating the report into a thousand cuts.
3. Apply the **five document checks**, in order. If an earlier check fails, later checks are often moot — fix upstream first.
4. Scan the **document red flags**.
5. Group findings by defect where one judgment call resolves several mentions.
6. For architectural / DAG violations → [arch-coherence](../arch-coherence/README.md). For code hygiene → [eng-review](../eng-review/README.md).
7. If the artifact passes the pre-pass, all five checks, and trips no red flags, say so in one line and stop.

Do not summarize the artifact. Go straight to issues.

## Mechanical pre-pass

Bookkeeping checks that run before the prose checks. Cheap, deterministic, catch the drift a section renumber or file move silently introduces. Implemented by [`scripts/check_docs.py`](scripts/check_docs.py); invoke it from the project being reviewed — the script walks up from CWD to find `.git` (fallback: CWD), auto-discovers top-level directories, and needs no configuration. It runs against any repo that adopts this lens, not just racecar.

```
# From inside this repo
make check-docs

# From a project with the skill installed at ~/.claude/skills/racecar-doc-coherence/
python3 ~/.claude/skills/racecar-doc-coherence/scripts/check_docs.py
```

Exit 0 is clean. Drift findings print one per line with file and line number; collapse them into a single root rather than inflating the report into a thousand cuts.

Five checks, three of them mechanized:

1. **Link resolution** *(mechanized).* For every `[text](path)` in a `.md` file, resolve the path against the filesystem. Every target must exist; every `#section-slug` must match a heading in the target file. A file move without a link audit is the classic source.
2. **Section-number citations** *(mechanized).* For every `FILENAME.md §N` cited in a non-markdown file (scripts, Makefile, `*.toml`, `*.yaml`), verify the target has a heading at that number. An optional directory prefix (`<dir>/FILENAME.md §N`) disambiguates when the same basename lives under multiple directories.
3. **Vocabulary identity** *(mechanized).* Every line of the form ``<Class> values are literal: **<literal>**`` must agree with every other instance of the same class across the repo's markdown. Catches drift between sibling READMEs that each repeat the same output vocabulary inline — see [`../shared/VOCABULARY.md`](../shared/VOCABULARY.md) for racecar's canonical block. The rule is identity, not existence: a class declared in only one place is fine.
4. **Example self-verification** *(reviewer).* Any canonical example embedded in a doc that names real files, sections, or line numbers must match current state — or be genericized so it cannot drift. Treat the example as an artifact under the lens.
5. **Doc-vs-enforcement agreement** *(partially mechanized via check 2).* For every script, linter, CI hook, Makefile target, or pre-commit entry that claims to enforce a named rule, the doc at that name must exist and say the same thing with the same label. Mismatches are one defect across N pointers, not N independent defects.

## The five document checks

1. **Cogency.** Do the artifact's claims, examples, and definitions agree with each other and with the system they describe?
   - A doc that defines a term one way in §2 and uses it differently in §5 fails cogency.
   - A spec that claims no migration is needed, then includes a migration step, fails cogency.
   - An example that illustrates a rule by violating it fails cogency.

2. **Scope honesty.** Do the labels match the content, and does the location match the role?
   - A file titled CODE.md that is ninety percent Python is really PYTHON.md.
   - A section titled "Testing" that only discusses unit tests is really "Unit Testing."
   - A doc claiming "language-agnostic" that names `__init__.py` in its core sections has misstated its scope.
   - A framework artifact at the repo root while its siblings live in `shared/` — the location disagrees with the role.

3. **File naming.** Does the filename describe function rather than format or incidental container?
   - `yaml_config.md` names the format; the thing it specifies is a config schema — rename `config_schema.md`.
   - `utils.md` for a doc entirely about date parsing is really `dates.md`.
   - A test file named after its subject (`test_billing.py`) passes; named after the framework (`test_django.py`) fails.

4. **Rule testability.** Can a reader fail or pass each rule on its own, without asking the author what was meant? Rules you cannot fail are not rules; they are aspirations.
   - "Write clean code" — cannot be failed.
   - "Strict validation" — what input fails strict?
   - "Reject inputs larger than 1 MB" — can be failed.
   - "Modules are named for what they do, not the format they handle" — can be failed.

5. **One-home-per-rule.** Every rule lives in exactly one canonical place. Pointers from other docs, glossaries, enforcement scripts, Makefile help, and pre-commit hook names resolve to it — they do not restate it.
   - The naming convention appears in full in two different standards files. Pick one. The other links.
   - A script labeled "enforces §4" when the rule now lives at §3. The pointer lies; fix the pointer the moment the rule moves.

## Mental models

**Resolver pattern.** Short routing tables beat long content dumps. When a file grows past a screen, it is probably an index disguised as content. A resolver says "for X, see A; for Y, see B" — it does not explain X, and it does not preview X's contents in the pointer line either. Enumerating a subset of A ("— tools P, Q, R — see A") clones content into a second home that drifts whenever A changes, serves no reader — the one who cares clicks through, the one who doesn't shouldn't be skimming an inventory — and creates a maintenance debt for zero value.

**Abstract-concrete split.** Axioms live separate from implementation. Do not fake generality by sprinkling specific examples into an abstract file — the file loses its abstraction without gaining grounding. If the examples are load-bearing, the file is concrete — rename it.

**Docs are not scratchpads.** Every shipped artifact is a read-only reference a teammate can load cold and use. TODOs, "temporary" notes, and half-built sections belong in draft branches, not merged files.

**Duplication is drift.** Two homes for the same rule means two places it will diverge. Pick one. Cross-reference the other. A codebase with duplicated rules is not "documented twice" — it is "documented zero times reliably."

**Opine, do not describe.** A review, a rule, and a runbook all take positions. Good doc: "do X" or "do not do Y." Bad doc: "X is a pattern that exists." Describing is easier and less useful.

**Root causes beat surface counts.** Fourteen broken cross-references after one file move is one issue, not fourteen. Eleven downstream labels invalidated by one section renumber is one issue, not eleven.

## Red flags — documents

Scan for these. One line each.

- Broken cross-references — `[text](path)` where the target does not resolve.
- Missing cross-references when a concept spans files.
- Duplicate concerns across files — the same rule living in two homes.
- Scope mismatch — file labeled X, content is Y.
- Directory-level mismatch — framework artifact outside the directory its siblings share.
- File named for format or incidental container instead of function.
- Forward references buried at the end of important sections.
- Pointers that describe instead of prescribe — "this is referenced from X" instead of "reference this from your X."
- Labels that overclaim — "language-agnostic" for content that is clearly one language's shape.
- Enforcement artifacts (scripts, Makefile help, pre-commit names) labeled with a section number the rule no longer lives under.
- Canonical examples citing real files, sections, or line numbers without being re-verified in the same edit.
- Vague, untestable rules — "strict validation," "handle appropriately," "where reasonable."
- Aspirational language masquerading as rules — "we strive to," "should be," "is generally."
- Project-specific leaks in generic docs — hardcoded domain examples where an abstract principle belongs.
- Jargon without definition — terms used as if self-explanatory.
- Examples that contradict the rule they illustrate.
- Low signal-to-noise — prose that has to be skimmed before the how-to surfaces.
- Manual toil — rules that require remembering instead of linting or automation.
- Docs updated alongside a diff that clearly does not implement what they now claim.

## Decision patterns — documents

- **Read the topology before reporting.** Load the full artifact and every file it cross-references before making a single judgment. A finding that looks valid in a two-paragraph window often inverts when the surrounding structure is visible. Local maxima are not findings.
- **Evidence over vibes.** Cite the file and line.
- **Merge when duplication; split when concerns diverge.** Two files with overlapping rules should be one. One file with two unrelated concerns should be two.
- **Pointers don't preview.** A line routing to §N should route and stop. Previewing clones a subset of §N into a second home that drifts every time §N changes.
- **Challenge the label.** If a file is labeled generic but eighty percent of it assumes one specific tool, the label is the bug. Rename before refactoring.
- **Prefer actionable over aspirational.** A rule is something you can fail.
- **Name the claim, then support it.** State the assertion plainly. Then cite the evidence.
- **Roll up before reporting.** If one fix resolves N mentions, report one root with N children.
- **Challenge the premise.** Half of bad work is the correct execution of the wrong thing.
- **When in doubt, delete.** Dead copy, stale guidance, half-built sections. Removing them is almost always the cheapest improvement available.

## Feedback format

- Group findings by root cause. One root per numbered block; children listed beneath as indented occurrences. If a single fix resolves N mentions, the root gets one number and the N surface points become indented children.
- Each root: `File/Topic — severity — one-sentence description`.
- Severity values are literal: **Blocker / Major / Minor / Nit**. Broken navigation and stale enforcement labels default to Blocker/Major; misleading claims default to Major; prose tightening defaults to Minor/Nit.
- No preamble. Start with root 1.
- End with a single verdict line. Verdict values are literal: **Ship / Revise / Rework**.

Example (shape only — substitute the artifacts under review):

```
1. Root: file reorg without link audit — Blocker — Files moved into subdirs; relative paths in movers and neighbors were not updated.
   - FILE_A.md:5 — same-dir link to FILE_B.md; FILE_B.md is in ../dir2/.
   - FILE_A.md:56 — same pattern; five more occurrences.
   - FILE_C.md:7 — same pattern from the sibling directory.
2. Root: FILE_B.md section renumber — Major — Section N moved to N+2; downstream labels did not follow.
   - SCRIPT.py:2 — docstring cites old §N.
   - Makefile:41 — help text cites old §N.
   - .pre-commit-config.yaml:24 — hook name cites old §N.
3. FILE_A.md §M — Major — Rule "strict validation" is untestable. Rewrite as a failable predicate (e.g. "reject inputs larger than 1 MB").
4. FILE_C.md — Nit — Resolver row descriptions vary from 4 words to 15 words.

Verdict: Revise. Root 1 blocks navigation; root 2 is the next-priority fix; issue 3 next pass.
```

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).

## Invocation

> Load `doc-coherence/README.md`. Run `make check-docs` (in-repo) or `python3 ~/.claude/skills/racecar-doc-coherence/scripts/check_docs.py` (skill install) first for the mechanical pre-pass, then review the attached doc for cogency, scope honesty, file naming, rule testability, and one-home-per-rule. Group findings by root cause.

> Using `doc-coherence/README.md`, run the script to catch the mechanical drift the prose checks can't see, then audit the result for issues the script doesn't.

If the artifact passes the mechanical pre-pass, all five checks, and trips no red flags, say so in one line and stop.
