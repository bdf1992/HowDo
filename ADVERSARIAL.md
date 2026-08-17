# Adversarial notes — v0.6.1

The runtime is a small protocol kernel, not a complete trust system. v0.6 makes the durable-context lifecycle structurally checkable while keeping the agency modifier above the execution kernel.

## Enforced operation invariants

| Attack | Runtime response |
|---|---|
| consequential request with no expected state | `resolve` refuses |
| consequential request with no precondition | `resolve` refuses |
| stale resolution | `admit` fizzles before execution |
| check raises | fails closed |
| one admission used twice | second `operate()` raises |
| observer self-verifies from executor report argument | observer never receives `Outcome.reported` |
| invariant false before operation | admission fizzles |
| invariant false after operation | residual routes to `invariant` |
| invariant residual patched over casually | `settle` refuses without explicit override |
| stale residual settles newer revision | refused |
| multi-layer settlement by default | refused |

## Enforced context invariants

| Attack | Context response |
|---|---|
| untouched shipped template | `onboarding_required` |
| caller flips only `context_id` + `onboarding: complete` | still `onboarding_required` because comparative evidence is blank |
| required lineage marker deleted | `invalid` rather than ready |
| ready context copied to a new basename | `fork_required` |
| helper forks malformed older context missing onboarding/parent keys | required keys are inserted and new fork requires onboarding |
| fork destination already exists | refused; source and destination are preserved |
| completion helper receives placeholder evidence | refused |

## Skill-level agency attacks

These are semantic invariants rather than Python NLP rules:

- `How do you...` must resolve capability against the actual assistant/system, not the user's capability context.
- `How do we...` composes contexts but does not merge authority; consequential ownership remains explicit.
- `How do they...` may use receiver context to render the answer, but receiver context is not evidence about the external actor.
- A presentation preference must never become a capability, permission, or factual claim.

## Deliberate remaining boundaries

- A caller can still opt out of consequential contracts with `mutates=False, crosses_boundary=False`; the kernel cannot inspect hidden effects.
- A vacuous precondition can still be supplied by a dishonest caller.
- A caller-supplied comparator can still lie.
- Gate evidence provenance is recorded, not authenticated or freshness-enforced.
- Python closures can capture state outside the narrow observer argument; isolation belongs to the host.
- Context completion proves a **structural receipt**, not the truth of a learning claim. LongHow + user settlement remain the semantic boundary.
- Rename/new-basename forks are detectable from the file itself. A byte-for-byte copy of an entire settled installation under the same filenames is not distinguishable without an external installation identity/custody mechanism; v0.6 does not pretend otherwise.
- The agency modifier is intentionally not implemented as a brittle pronoun parser. The skill binds the actor from language/context; the execution kernel remains domain-neutral.

These boundaries keep the reference system small enough to audit. Closing them requires host identity, isolation, authenticated evidence, or policy infrastructure rather than more prose in the kernel.

## v0.6.1 lifecycle attacks

- **declined persists** — `decline_onboarding()` produces `declined`; later inspection does not return `onboarding_required`.
- **ready cannot be re-completed** — `complete_onboarding()` refuses a ready context so `context_id` cannot churn.
- **onboarding text is one-line** — CR/LF in onboarding evidence is flattened before persistence.
- **structural, not semantic** — evidence bullets prove only minimum shape; truth and quality remain a human judgment.
