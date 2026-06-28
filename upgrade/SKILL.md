---
name: racecar-upgrade
description: Bring an existing project in line with current racecar WITH NUANCE — never assuming the pre-existing repo is wrong and clobbering it. Detects every divergence from racecar mechanically (refresh canonical scripts, run the checkers, diff pre-commit against templates/classic), then gives each divergence a verdict — Conform (drift; bring to base) or Escalate (racecar's default is wrong; change the standard, not the repo) — with the burden of proof on Conform; an intentional-and-right divergence is simply kept with an in-place comment, never a central override registry. Owner-authorized, idempotent, no clobber. Optionally restructures toward lib/api/surfaces from the existing structure (the surfaces — `server/` over `src/<pkg>/api` — are owned by [`racecar-create-server`](../create-server/SKILL.md) and the library scaffold by `racecar-create-package`; upgrade reuses those, one home each). Use when asked to "upgrade this repo to racecar", "bring this project up to current racecar", "fold in the latest racecar changes", "update the Makefile/standards without clobbering my customizations", or to restructure an existing repo to the surfaces shape.
---

# racecar-upgrade — Nuanced Upgrade

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: an existing repo is a set of decisions, not a pile of mistakes. Every divergence from current racecar gets a verdict, and the burden of proof is on Conform, never on the repo:

- **Conform** — drift or accident; bring it to base.
- **Escalate** — the divergence shows racecar's default is wrong; change the standard, not the repo (the falsification loop, project → racecar).

An intentional-and-right divergence that is neither is simply **kept** — documented by one comment at its one home (the owned `Makefile`, the site in the code), never a central override registry. There is no `[tool.racecar.overrides]`; the Makefile fold (PACKAGING.md §7) absorbs build customization structurally (owned `Makefile` vs canonical `racecar.mk`, identical in every repo), so there is nothing to declare.

Detect mechanically first (drives [`racecar-normalize`](../normalize/SKILL.md) + the checkers + a template diff), classify with evidence, present for the owner's authorization, apply idempotently. Never clobbers a customized `Makefile` or pyproject — but a pre-fold *monolithic* `Makefile` is drift, not customization: `sync` drops `racecar.mk` and leaves the monolith untouched, so the canonical build sits inert beside it (`check_packaging` flags `racecar-mk-not-included`). The one Makefile action upgrade still takes is the manual fold adoption (a Conform): move canonical recipes out, add `include racecar.mk`, keep only project-specific targets. See [`README.md`](README.md) step 4. Optional structural uplift toward `lib → api → surfaces` ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §11) derives verticals from the existing structure rather than imposing a shape on working code. It also modernizes the human-facing docs as a judgment step (not a gate): propose restructuring the README to the standard shape ([`../templates/classic/README.md`](../templates/classic/README.md)) and relocate an old `docs/<repo>/` brief to `docs/summary/`.
