# Plan: rebuild the walls

The three construction flaws (heavyweight detectors, emergent seams, self-exemption) are one problem at the middle elevation: the bricks are well-laid and the house is well-designed, but the walls were assembled by improvisation. This plan rebuilds them with the rigor already present in the parts.

The first execution pass (a parallel agent workflow) built the **scaffold**: a `RepoContext` keystone, a rule registry over both heavyweight checkers, self-lint to zero, and negative-space fixtures. But the two decompositions were conservative, a registry wrapped over the unchanged audit bodies, so the files grew (check_packaging 1324 to 1446, check_cli_commands 1137 to 1336) and `too-many-lines` was suppressed with a disable rather than dissolved. That is a scaffold, not the finished wall. This pass finishes it.

The finishing move tried: a **thin entry file** (stable invocation) over a sibling **implementation package** (`<stem>_rules/`, auto-shipped by one home, `sync_scripts.delivered_files`), so `too-many-lines` vanishes by construction. This was done for both checkers, then measured: the split ADDED ~944 lines (the two checkers +663, plus a 281-line keystone) for the same audits, no new checking. **`check_cli_commands` was reverted** to a single file with one honest `too-many-lines` disable (it bought the least and was pure ceremony). `check_packaging` kept its split (it is the heavier file and reuses the keystone). The lesson, recorded: package-decomposing an already-function-decomposed checker relocates complexity and adds per-file ceremony; the default is one file plus an honest disable, and a split must earn its keep.

## TODO

### 3 - move checker applicability into tested Python
- Prio: P2
- Depends: none
- Updated: 2026-06-22

What: move checker applicability (when the CLI audit runs, when the Django check runs) out of `racecar.mk` shell `if [ -n "$(find ...)" ]` into Python where it is tested. The old item 3 had a second half, "wire a shared role map so the surfaces-vs-CLI conflict closes by construction"; that is foreclosed. `repo_context` (the shared role map) was deleted as dead, so each detector owns its own role view, which is simpler and was never actually in conflict in practice.
Why: applicability logic still lives untested in Make. Minor hygiene, not load-bearing.
Status: not started (the role-map half is closed by the repo_context deletion; only this remains).

### 5A - do NOT broadly decompose the other checkers
- Prio: P3
- Depends: none
- Updated: 2026-06-22

What: dropped. The plan was to apply the thin-entry + impl-package pattern to the other large checkers (`check_brief` 731, `check_surface_orchestration` 529). The `check_cli_commands` revert is the evidence against it: the split adds ceremony for the same logic. Leave these as single files with an honest `too-many-lines` disable. Only split a checker if it crosses a real maintainability threshold (multiple unrelated concerns genuinely fighting in one file), not to satisfy a line-count lint.
Why: the decomposition over-reached. A framework whose doctrine is "the detector must have lower entropy than the thing it watches" should not grow its detectors to silence a configurable threshold.
Status: closed (decided against).

## PLAN

`check_packaging` is decomposed (92-line entry + 14 modules); `check_cli_commands` was decomposed then reverted to one file + honest disable. `repo_context` was deleted: its role-map keystone had zero consumers, and its 55 live helper lines went back to surfaces, their origin. The decomposition appetite is spent, deliberately, and the one speculative abstraction is gone.

- **3**, reduced to its surviving half: move `racecar.mk` shell applicability into tested Python. The other half (a shared role map for the surfaces-vs-CLI seam) is closed; deleting `repo_context` foreclosed it, and the two detectors never actually conflicted in practice.
- **5A** is closed (decided against): no broad decomposition.

No critical path remains. Only item 3 (the applicability move) is open, and it is minor hygiene.

## Completed

Both passes, verified independently (242 tests green, pylint 10.00/10 across the full set, doc gate clean, adopter round-trip delivers and runs):

- **2B** - `check_packaging` done right: a thin entry (92 lines) plus a sibling package of one audit per module (`check_packaging_rules/`, 14 modules), composed by a plain `run_all` that calls each check in order. The registry ceremony (a `Rule` protocol, a `_Ctx` carrier, eleven `_rule_*` adapters of which eight were pure pass-throughs, a `RULES` list) was removed; the one shared fact (the library pyproject parsed once, read by two later checks) is now a local variable. `too-many-lines` is dissolved by construction, no disable. `sync_scripts.delivered_files` auto-ships the `<stem>_rules/` sibling across sync, the scaffolder, and the staleness hook; the entry invocation, Makefile contract, and tests are untouched.
- **2C - reverted.** `check_cli_commands` was split the same way, then rolled back to a single 1209-line file with one honest, rationale'd `too-many-lines` disable, after measuring that the split added ceremony for the same audits. The `delivered_files` mechanism is generic, so the revert needed no sync change (no sibling package, nothing extra shipped). This is the corrected reading of the 250ft criticism: the answer to "the files grew" was not "split them," it was "stop adding code"; one honest disable on a working file beats a package of ceremony.
- **1 / 2A - built, then deleted as dead.** The `RepoContext` keystone (`repo_context.py`) was meant to let checkers share one role classification. Nothing consumed the role map: `check_cli_commands` was reverted before it could be wired, and no other checker used it. A panoptic review found the module was ~80% dead (the `build_context` / `RepoContext` / `roles` product had zero consumers; only ~55 lines of source-root helpers were used, by surfaces alone, having been extracted from surfaces in the first place). Deleted; the helpers went home to surfaces. Net ~-330 lines. The lesson: a keystone with one foundation under it is not a keystone.
- **0 / 4** - self-exemption closed: racecar's own scripts (and the touched hook) pass pylint at 10.00/10, wired into `make check` via a `lint` target. The two `too-many-lines` disables the first pass left are now gone, dissolved by 2B/2C.
- **2D** - small lint findings cleared across the script set.
- **6** - negative-space fixtures added across the checker tests, guarding the absence-case blind spot that produced three bugs this session. (The `repo_context` fixtures were deleted with that module; the shape absence-cases they covered are also held by `test_check_packaging`.)
- **shape gap** - `manage.py` (not a bare `server/` dir) is the Django marker, fixed in `detect_shape`, `racecar.mk`, and `init`, with the gap layouts added to the coherence matrix.
