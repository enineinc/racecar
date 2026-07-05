# ADR: Identity, credentials, and tokens for a secured racecar server

Status: Accepted (2026-07-04). Owner: Vishal.
Extends: [`../AUTH.md`](../AUTH.md) (the auth rail). Implemented by
[`racecar-secure-server`](../../secure-server/SKILL.md); consumed by
[`GENERATION.md`](../GENERATION.md) (the resource-surface rail).

This record is framework-neutral doctrine and it is deliberately repeatable: every racecar
project that closes its surfaces (a battery-trading engine, a meter-ETL library, a telemetry
lake, a returns model) faces the same identity and token questions, so the answer is decided
once here rather than re-litigated per repo. A project does not invent an identity model; it
instantiates this one.

---

## 1. In plain language (read this first)

Picture the system as a building with a front desk and a set of machines inside.

- **One guest list.** There is exactly one list of people, called `auth.User`. If you are not
  on the list, you do not exist to the system. Everything about a person hangs off their single
  row on this list.
- **A master on/off switch per person.** Each person has a switch called `is_active`. ON means
  they can use the building. OFF means they cannot, at all. A brand new person is added with the
  switch OFF, and someone has to turn it ON on purpose. Two people are on the list from the very
  start with the switch already ON: `root` (the admin, number 1) and `vishal` (number 2). More
  people get added later, and each of them starts OFF.
- **Two ways to prove who you are at the front desk.** The strong way is to tap a physical
  security key (a YubiKey). While those keys are still being handed out, there is a temporary
  second way: type a username and password. The password door only exists when a setting turns
  it on, and even then it only works for a person whose switch is ON.
- **Tickets to use the machines.** Logging in at the desk does not by itself let you run the
  machines (the API). For that you carry a ticket, called a token. There are two kinds, and this
  is exactly the GitHub model:
  1. a ticket the desk prints for you when you log in (an OAuth token), and
  2. a reusable pass you make yourself for your own scripts and robots (a personal access token,
     the same idea as a GitHub API key).
  Both are just long random strings. A machine never trusts the string on its own; it checks it
  against the desk before letting you in.
- **The switch controls everything.** If a person's master switch is flipped OFF, every one of
  their tickets stops working right away and they can no longer log in. One switch, the whole
  person.

None of this is invented. It is how GitHub, GitLab, and most large platforms are built: one
user record, a profile hanging off it, many keys and many API tokens hanging off it, and a
single active flag that turns the person on or off. The rest of this document writes those same
rules down precisely, so an implementation can be checked against them.

---

## 2. Context

`AUTH.md` sets the end state: a surface is closed by default, a human authenticates at a **FIDO2
hardware key**, and the surface honors only an **opaque OAuth bearer token** validated by
introspection. That end state does not change. Two forces require the identity model underneath
it to be written down and extended, and both recur in every secured racecar project:

1. **Keys are not yet distributed.** A team must do real work before every member holds a
   hardware key. A human needs a way to authenticate in the interim. The answer must be
   transitional (retired when the keys land), off by default, and unable to weaken the hardware
   key end state when it is off.
2. **Surfaces require a token on every call, and pipelines need a carryable one.** The REST and
   MCP surfaces refuse an unauthenticated request. A downstream pipeline the team wires needs a
   durable, revocable credential to present. The OAuth authorization-code plus PKCE exchange is
   correct for an interactive client but heavy for a script. A **personal access token** is the
   standard, GitHub-shaped answer.

Because both forces are universal to "a racecar library with closed surfaces," the identity and
token model is canon, not per-project glue.

---

## 3. Decision (summary)

1. **`auth.User` is the sole identity of record.** There is no parallel or standalone user
   store. Every credential and every token references a user by key.
2. **`Profile` is `OneToOne(User)`**, carrying enrichment (contact, preferences, display
   attributes). It is orthogonal to authentication: it never gates a login and a login never
   reads it.
3. **Credentials and tokens are `ForeignKey(User)`, many per user:** `WebAuthnCredential`
   (hardware keys), `Token` (personal access tokens), and the OAuth access tokens owned by
   `django-oauth-toolkit`.
4. **`is_active` is the master gate**, enforced at every point where a session is attached or a
   token is honored. Disabling a user cascades: all of that user's tokens stop being accepted and
   no new session can attach.
5. **New users are created disabled.** Enabling is an explicit, separate act. The seed is exactly
   `root` (pk 1) and `vishal` (pk 2), both enabled.
6. **Human login is hardware key always, and username/password additionally when
   `PASSWORD_LOGIN_ENABLED` is set.** The password path is transitional, throttled, audited, and
   subject to the same `is_active` gate.
7. **Two token authorities feed one acceptance function.** OAuth opaque tokens are validated by
   introspection; personal access tokens are validated by local lookup. This is the GitHub model,
   adopted on purpose, not an accident of two subsystems.

---

## 4. Formal model

### 4.1 Carrier sets

Let

- `U` be the set of user records (`auth.User` rows).
- `P` be the set of profiles.
- `W` be the set of WebAuthn credentials (enrolled hardware keys).
- `T` be the set of personal access tokens (PATs).
- `O` be the set of OAuth access tokens (owned by `django-oauth-toolkit`).
- `S` be the finite universe of scopes (for example `pkg:vertical:read`, `pkg:vertical:write`).
- `K` be the space of opaque bearer strings, `H` the space of usable password hashes, `IP` the
  space of client addresses, `Θ` a totally ordered time domain.

### 4.2 User attributes (functions on `U`)

For every `u ∈ U`:

- `id(u) ∈ ℕ`, injective (the primary key).
- `active(u) ∈ 𝔹` (the field `is_active`).
- `super(u) ∈ 𝔹` (the field `is_superuser`).
- `pw(u) ∈ H ∪ {⊥}`, where `⊥` denotes an unusable password. Define
  `usable(u) :⇔ pw(u) ≠ ⊥`.

Django creates a user with `pw(u) = ⊥` when no password is set (`set_unusable_password`), and
`check_password(x, ⊥) = false` for all `x`. This matters below: a user row can exist and still
be unauthenticable by password.

### 4.3 Relations and cardinalities

The identity law (canon): **every credential and token owner lies in `U`, and `U` is the only
identity carrier.** Concretely:

- Profile link: `profile : U ⇀ P`, a partial injective function (Django `OneToOne`, cardinality
  `0..1`). A deployment MAY promote it to total (`1..1`) by creating a profile row on user
  creation; injectivity is invariant either way, so `|P| ≤ |U|`.
- WebAuthn ownership: `owner_W : W → U`, total, many-to-one. A user holds
  `keys(u) = { w ∈ W : owner_W(w) = u }`, with `|keys(u)| ≥ 0`. Multiplicity is deliberate: a
  spare key is the recovery path (see `AUTH.md` recovery). `W` is `FK(User)`, never `OneToOne`.
- PAT ownership: `owner_T : T → U`, total, many-to-one. Each `t ∈ T` also carries
  `key(t) ∈ K`, `active_T(t) ∈ 𝔹`, `scopes_T(t) ⊆ S`.
- OAuth ownership: `owner_O : O → U`, total, many-to-one. Each `o ∈ O` carries `key(o) ∈ K`,
  `active_O(o) ∈ 𝔹`, `scopes_O(o) ⊆ S`, `exp_O(o) ∈ Θ`.

Write `owner : (T ∪ O) → U` for the common owner map (`owner = owner_T` on `T`, `owner_O` on
`O`), and `scopes`, analogously, for the common scope map.

### 4.4 Bearer liveness

`live : (T ∪ O) → 𝔹` is the per-authority validity test at the current time `now ∈ Θ`:

```
live(x) =  active_T(x)                          if x ∈ T     (local lookup)
           active_O(x) ∧ now < exp_O(x)         if x ∈ O     (introspection, RFC 7662)
```

The two authorities differ only in `live` and in where the lookup happens. `T` is resolved by a
direct database read on the Authorization Server; `O` is resolved by the surface calling
`/o/introspect` and caching the verdict for a TTL clamped to `exp_O(x) - now` (revocation-latency
bound, per `AUTH.md`). Both tokens are opaque: neither is decoded, and `live` is never inferred
from the string itself.

---

## 5. Authorization semantics

### 5.1 Session attach

Human authentication produces a session by the partial function
`attach : U × M ⇀ Session`, where `M = { webauthn, password, recovery }`. Attachment is defined
only when the corresponding guard holds. Let `PWL ∈ 𝔹` be the setting `PASSWORD_LOGIN_ENABLED`
and `throttled : U × IP → 𝔹` the online-guessing lockout (armed when the failure count for
`(u, ip)` reaches `N = 5` within a window `w = 900 s`).

```
guard_attach(u, webauthn) ⇔ active(u) ∧ ∃ w ∈ keys(u) : assertion_verifies(w) ∧ user_verified
guard_attach(u, password) ⇔ active(u) ∧ PWL ∧ usable(u) ∧ check_password(input, pw(u))
                                       ∧ ¬throttled(u, ip)
guard_attach(u, recovery) ⇔ active(u) ∧ (redeem_backup_code(u) ∨ redeem_tap(u))
                                       ∧ ¬throttled(u, ip)
```

The conjunct `active(u)` is common to all three. This is the single most important line in the
document: **`is_active` is checked at the moment of attach, on every method.** The password path
gets `active(u)` for free through Django's `ModelBackend.user_can_authenticate`; the WebAuthn and
recovery paths call `login()` directly and MUST therefore assert `active(u)` explicitly before
attaching. Centralize the check in one `attach_session(u, method)` so the three paths cannot
diverge.

### 5.2 Session class and token issuance

Mark each session with its method. Define the full-login set `F = { webauthn, password } ⊂ M`;
note `recovery ∉ F`. The token-issuance guard on the OAuth authorize endpoint is

```
reachable(/o/authorize, s) ⇔ method(s) ∈ F
```

A recovery session may enroll a new hardware key but never reach `/o/authorize`, so a recovery
secret is never a token-equivalent bypass. The password session is in `F` by deliberate
choice: while `PWL` holds, a password login is a full login and may mint tokens. This is the one
sanctioned relaxation of the hardware-key end state, and it is gated entirely by `PWL`.

### 5.3 Token acceptance at a surface (the `check` predicate)

A surface command declares a required scope `σ ∈ S`. For a presented bearer `b ∈ K`:

```
accept(b, σ) ⇔ ∃ x ∈ (T ∪ O) : key(x) = b ∧ live(x) ∧ active(owner(x)) ∧ σ ∈ scopes(x)
```

Error mapping (fail-closed, matching `AUTH.md`):

```
b = ∅                                              → 401  (no credential)
b ∈ O-shaped ∧ introspection unconfigured/down     → 503  (never fall open)
∃x: key(x)=b ∧ live(x) ∧ active(owner(x)) ∧ σ∉scopes(x)  → 403  (authenticated, unauthorized)
otherwise (no live, owned, in-scope token matches b)     → 401
```

Default-deny is structural: a command whose declared scope is absent from the token's scope set
is unreachable, and a command declaring no scope is unreachable to every token (`AUTH.md`).

---

## 6. Invariants

Let a system state be the tuple `(U, P, W, T, O, active, pw, ...)`. The following must hold in
every reachable state; each is mechanically checkable.

- **I1 (canon identity).** `range(owner_W) ∪ range(owner_T) ∪ range(owner_O) ⊆ U`, and
  `profile` is injective into `U`. No identity record exists outside `U`.
- **I2 (attach gate).** For every attached session `s`, `active(user(s)) = 1` held at attach time.
- **I3 (token owner gate).** `accept(b, σ) ⟹ active(owner(x)) = 1` for the witnessing `x`.
- **I4 (scope default-deny).** `σ ∉ scopes(x) ⟹ ¬accept(b, σ)` through `x`; a scopeless command
  is unreachable.
- **I5 (fail-closed).** Introspection unconfigured or unreachable yields `503`, never acceptance.
- **I6 (recovery non-issuance).** `method(s) = recovery ⟹ ¬reachable(/o/authorize, s)`.
- **I7 (password gate).** A password attach implies `PWL ∧ active(u) ∧ usable(u)`.
- **I8 (default-disabled).** A newly created `u` with `id(u) ∉ {1, 2}` has `active(u) = 0` at
  creation. The seed `{u : id(u) ∈ {1, 2}}` (root, vishal) has `active(u) = 1`.
- **I9 (opacity).** Every element of `T ∪ O` is an opaque handle; `live` and `accept` are computed
  by lookup or introspection, never by decoding the bearer.

---

## 7. Theorems (the properties the invariants buy)

### 7.1 Disable cascade

**Claim.** For any `u ∈ U`, `active(u) = 0` implies (a) no bearer owned by `u` is accepted and
(b) no new session attaches for `u`.

**Proof.** (a) `accept(b, σ)` requires `active(owner(x)) = 1` for the witness `x` (I3). If
`owner(x) = u` and `active(u) = 0`, that conjunct is false, so no `x` owned by `u` witnesses
acceptance. (b) `guard_attach(u, m)` carries `active(u)` as a conjunct for every `m ∈ M` (I2,
section 5.1); with `active(u) = 0` no guard holds, so `attach(u, m)` is undefined. ∎

**Latency.** For `x ∈ T` the effect is immediate (local `live` read observes `active(u)` at call
time). For `x ∈ O` it is bounded by the introspection cache TTL, which is clamped to the token's
residual lifetime; set the TTL to zero for the highest-value scopes. Thus one write,
`active(u) := 0`, revokes the whole person, subject only to the OAuth cache bound.

### 7.2 Transitional safety

**Claim.** With `PWL = 0`, the password path cannot produce a session or a token, independent of
the state of `U`, `pw`, or the throttle.

**Proof.** `guard_attach(u, password)` has `PWL` as a conjunct (I7); with `PWL = 0` it is false
for every `u`. No password session attaches, so (5.2) no password-issued token exists. The
hardware-key and recovery guards do not reference `PWL`, so the end state is exactly `AUTH.md`. ∎

Corollary (the layered guarantee): production safety rests on `PWL = 0` (a config fact), not on
"there happen to be no password users" (a data fact that drifts). The data-level posture
(`∀ u : ¬usable(u)`, achieved by `set_unusable_password` after key enrollment) is a second,
independent layer, not the primary one.

### 7.3 Default-deny closure

**Claim.** A surface with no Authorization Server configured accepts nothing.

**Proof.** With introspection unconfigured, every `O`-shaped bearer yields `503` (I5), and with no
AS there is no `T` store to resolve either, so `accept(b, σ) = false` for all `b, σ`. The surface
is closed by construction, matching the cardinal rule of `AUTH.md`. ∎

---

## 8. Lifecycle

### 8.1 User active-state machine

```
            create (id ∉ {1,2})            enable (explicit)
 (absent) ───────────────────▶ disabled ───────────────────▶ enabled
            create (id ∈ {1,2}, seed)                 ◀───────
                    │                        disable (revoke)
                    └──────────────────────────────────▶ enabled
```

`active : U → 𝔹`. Creation lands in `disabled` except for the seed, which lands in `enabled`.
The `disabled → enabled` edge is a deliberate operator action (Django admin toggle or an
`enable_user` command). The `enabled → disabled` edge is revocation and triggers the cascade of
7.1.

### 8.2 Password-hash state

`usable(u)` toggles by `set_password` (to `usable`) and `set_unusable_password` (to `⊥`). The
production key-only posture is `∀ u : ¬usable(u)` after each user enrolls a hardware key; it is
enforced per user and does not follow automatically from `PWL = 0`.

### 8.3 Flag lifecycle (transition and teardown)

`PWL` is a deployment boolean, fail-safe `0`. It is set `1` only where hardware keys are not yet
present (for example a local instance seeded with synthetic data). It retires when every human
principal holds at least one key: `∀ u ∈ humans : keys(u) ≠ ∅`. Teardown removes the password
view, its route, and the `password` element of `F`, restoring the pure hardware-key end state.

---

## 9. Consequences

**Enabled.**
- A team authenticates and works before hardware keys arrive, with the end state one config flip
  away and no protocol change.
- Pipelines carry a durable, named, individually revocable PAT (`Token`, `FK(User)`,
  `active_T`), instead of running an interactive OAuth exchange. This is the primary unlock for
  downstream integration.
- One master switch (`is_active`) governs a whole principal across every credential and token,
  with a proven cascade (7.1).
- The model is identical across racecar projects, so surface code, checks, and operator runbooks
  transfer unchanged.

**Costs (accepted).**
- Two token authorities (`O` and `T`) mean two `live` paths and two lifecycles. This is the
  GitHub shape and is intentional; the purist single-authority alternative (PAT as a long-lived
  `O` token) is rejected in section 10.
- The password path is a real, if bounded, relaxation while `PWL = 1`: a guessable secret can
  mint a token. It is contained by I7, the throttle, the audit trail, and 7.2, and it is
  transitional. Each consuming project records the live flag as dated, triggered debt.

---

## 10. Alternatives considered and rejected

- **DRF `TokenAuthentication` for PATs.** Rejected. The surfaces are plain Django adapters, not
  DRF views; adopting DRF to reuse one thin token class either forces a broad view rewrite or the
  a-la-carte authenticator hack, and drags a heavyweight dependency into the security-critical
  process. The PAT is a plain model plus one branch in `check`; the idea is portable, the
  framework is not.
- **Single token authority (PAT as a long-lived OAuth token).** Reasonable and canonical, but it
  couples PAT issuance to the OAuth grant machinery and loses the simple local-lookup path that
  makes PATs cheap for pipelines. The GitHub two-authority model is chosen for transparency and
  pipeline speed; the trade is recorded, not hidden.
- **`WebAuthnCredential` as `OneToOne(User)`.** Rejected. One key per user makes a lost key a hard
  lockout and contradicts the multi-key recovery architecture (`AUTH.md`). `FK(User)` is required.
- **A custom user model.** Rejected. `auth.User` is canon; enrichment goes on `Profile`
  (`OneToOne`). A custom user model is a large, low-value migration and breaks the "instantiate,
  do not invent" principle.
- **A DEBUG or env bypass that disables surface auth locally.** Rejected. It punches a hole in the
  fail-closed invariant (I5) and wires pipelines against an unauthenticated surface, deferring the
  token integration they exist to exercise. The password flag plus PATs give a local path that is
  still real auth.

---

## 11. How this is enforced and repeated

This ADR is instantiated by `racecar-secure-server` (it generates `auth.User`-backed
`WebAuthnCredential`, `Token`, `Profile`, the `is_active`-gated `attach_session`, the password
view behind `PWL`, and the `check` acceptance function) and consumed by `GENERATION.md` (the
surfaces validate by introspection and, for PATs, by local lookup). The mechanical gates:

- `check_surface_auth.py` (per `AUTH.md`): a surface without the auth gate, or a command without a
  scope, fails. Default-deny is a check, not a hope.
- The import-linter contract keeps the surfaces free of any import from the Authorization Server;
  they reach it only over HTTP, preserving the acyclic DAG.
- Each project that sets `PWL = 1` records it as dated, triggered debt with the teardown of 8.3.

Repeatability is the point: a new secured project does not re-decide any of section 3. It adopts
this model whole.

---

## 12. References

- [`../AUTH.md`](../AUTH.md), [`GENERATION.md`](../GENERATION.md), [`racecar-secure-server`](../../secure-server/SKILL.md).
- OAuth 2.1: RFC 6749, RFC 7636 (PKCE), RFC 7662 (introspection), RFC 7009 (revocation),
  RFC 8414 (server metadata), RFC 7591 (dynamic client registration).
- WebAuthn / FIDO2 (W3C Web Authentication), `py_webauthn`.
- Prior art for the two-authority token model: GitHub, GitLab, and comparable SaaS platforms
  (user identity plus profile plus many keys plus many personal access tokens, one active flag).

## Voice

Common voice: [../../shared/VOICE.md](../../shared/VOICE.md).
