---
name: racecar-upgrade
description: Bring an existing project in line with current racecar WITH NUANCE — never assuming the pre-existing repo is wrong and clobbering it. Detects every divergence from racecar mechanically (refresh canonical scripts, run the checkers, diff Makefile/pre-commit/pyproject against templates/classic), then classifies each divergence into one of three verdicts — Conform (drift; bring to base), Declare (intentional and defensible; preserve and record in [tool.racecar.overrides]), or Escalate (racecar's default is wrong; change the standard, not the repo) — with the burden of proof on Conform. Owner-authorized, idempotent, no clobber. Optionally restructures toward lib/api/faces from the existing structure. Use when asked to "upgrade this repo to racecar", "bring this project up to current racecar", "fold in the latest racecar changes", "update the Makefile/standards without clobbering my customizations", or to restructure an existing repo to the faces shape.
---

# racecar-upgrade — Nuanced Upgrade

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: an existing repo is a set of decisions, not a pile of mistakes. Every divergence from current racecar gets one of three verdicts, and the burden of proof is on the first, never on the repo:

- **Conform** — drift or accident; bring it to base.
- **Declare** — intentional and defensible; preserve it and record it in `[tool.racecar.overrides]` so it survives future upgrades.
- **Escalate** — the divergence shows racecar's default is wrong; change the standard, not the repo (the falsification loop, project → racecar).

Detect mechanically first (drives [`racecar-normalize`](../normalize/SKILL.md) + the checkers + a template diff), classify with evidence, present for the owner's authorization, apply idempotently. Never clobbers a customized `Makefile` or pyproject. Optional structural uplift toward `lib → api → faces` ([`../arch-coherence/FACES.md`](../arch-coherence/FACES.md) §11) derives verticals from the existing structure rather than imposing a shape on working code. It also modernizes the human-facing docs as a judgment step (not a gate): propose restructuring the README to the standard shape ([`../templates/classic/README.md`](../templates/classic/README.md)) and relocate an old `docs/<repo>/` brief to `docs/summary/`.
