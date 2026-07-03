# Commits

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Rules for commit messages in this repo. Apply without deviation when authoring or suggesting a commit.

## Format

Conventional Commits: `<type>(<optional scope>): <description>`

- Lowercase type and description.
- No trailing period on the subject.
- Imperative mood. "add", not "added".
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Breaking changes: append `!` after the type or scope (`feat(api)!: …`) and include a `BREAKING CHANGE:` footer.
- A change that does not fit a conventional type is a signal to stop and ask, not to invent one.

## Version home

Exactly one per repo, resolved per [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md) §8: the library pyproject's `[project].version` where a `[project]` table exists; a root `VERSION` file only where none does (a docs/standards repo with nothing to publish). If both exist, that is a packaging finding — propose deleting `VERSION` — not a sync task. Never maintain the same version in two files.

## Bump from commit type

Deterministic mapping from the commit's conventional type to the semver bump:

| Commit type | Bump |
| ----------- | ---- |
| breaking (`!` after type/scope, or `BREAKING CHANGE:` footer) | major |
| `feat` | minor |
| `fix`, `perf` | patch |
| `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore`, `revert` | none |

Pre-1.0 (major = 0): breaking maps to a **minor** bump; the `!` / `BREAKING CHANGE:` marker still appears in the message. Going to 1.0.0 is a deliberate owner decision, never automatic.

One bump per commit, decided by the highest-impact change in the diff. A staged diff that mixes a `feat` with unrelated `docs` takes the `feat` bump — or better, gets split into two commits.

## Valid version increments

Compare new vs. old version, parsed as `major.minor.patch`. Exactly one of:

| Bump  | Delta    | Result                                                  |
| ----- | -------- | ------------------------------------------------------- |
| Patch | `+0.0.1` | major and minor unchanged; patch increases by 1         |
| Minor | `+0.1.0` | major unchanged; minor increases by 1; patch resets to 0 |
| Major | `+1.0.0` | major increases by 1; minor and patch reset to 0        |

Any other delta is invalid. Refuse to write the commit message and name the valid bump that was likely intended.

## Version bumps in commits

When the version home is part of the diff:

- Do not use a separate `chore(bump)` commit. The subject describes the actual change.
- Append a trailing line to the body: `Bump version to X.Y.Z.` — with the period.

## Enforcement

`scripts/check_version_bump.py` gates the type-to-bump rule at the commit-msg stage: a commit whose type maps to a semver bump (feat, fix, perf, or a breaking change) fails when the version home is unchanged between the index and HEAD. It asserts only that a bump happened, not that the magnitude is correct; the valid-increment rule above is racecar-commit's to apply. Non-bumpable types pass without a bump.

## References

- Git `SubmittingPatches` (canonical for many open-source projects): <https://git-scm.com/docs/SubmittingPatches/2.41.0>
- Conventional Commits v1.0.0: <https://www.conventionalcommits.org/en/v1.0.0/>
