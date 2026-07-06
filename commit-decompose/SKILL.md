---
name: racecar-commit-decompose
description: Alias of racecar-commit. Splitting a working tree into a dependency-ordered commit series is now the default behavior of /racecar-commit, which decomposes automatically when the tree holds more than one concern. This entry remains so existing invocations still resolve; it adds no behavior of its own. Prefer /racecar-commit.
---

# racecar-commit-decompose (folded into racecar-commit)

Decomposition is no longer a separate skill. [`racecar-commit`](../commit/SKILL.md) inventories the whole tree and commits it as one when it tells one story, or as an ordered series when it tells several, deciding the version bump per commit. There is one home for the procedure; this alias routes to it so old muscle memory ("decompose the working tree", "split this into commits", "how should I commit this") still lands.

Load [`commit/SKILL.md`](../commit/SKILL.md) and apply it. Everything the former decompose skill did — inventory, group-by-concern, straddle detection and feature-editing, bottom-up ordering, forward-reference checks, and the owner-committed runbook — lives there now, in Steps 1, 2, 4, and 5.
