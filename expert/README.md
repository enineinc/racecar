# Expert Output Mode: Resolver

A routing table. One topic for now; more may be added later.

Topic: Output discipline, terse, high-density delivery for an expert operator (lead with the result; no preamble, recap, or hedging; expand only on genuine tradeoffs; do not ask permission for authorized work)
Load: [EXPERT.md](EXPERT.md)

## Install

This is an optional overlay, separate from the main `./install`. From the racecar
checkout:

    make expert             # symlink ~/.claude/skills/racecar-expert-mode here + add a managed pointer block to ~/.claude/CLAUDE.md
    make expert-uninstall    # reverse both

Idempotent. Refuses to clobber a foreign symlink at the target path. Honors
`CLAUDE_SKILLS_PATH` / `CLAUDE_MD_PATH` overrides, like `./install`.
