# Adversarial notes — v0.8.0

The runtime is a small protocol kernel, not a complete trust system. v0.8 makes the durable-context lifecycle structurally checkable while keeping the agency modifier above the execution kernel.

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
| "not now" recorded as a refusal | separate states: `deferred` leaves the offer open, `declined` closes it |
| declined context reopened by deferring | refused; a decline is an answer, not a postponement |
| deferred context onboarded later | settles into the lineage the deferral opened; `context_id` preserved |
| settlement attempted on the shipped template | `TemplateContextError`; a template has no lineage to settle |
| template forked as if it were a lineage | refused; instantiate with `ensure_context()` |
| template marker carried into the instantiated store | stripped; the store opens at `context_id: pending` |
| template's self-description carried into the instantiated store | stripped; no store claims in prose that it cannot be settled |
| settlement attempted on a context inside the skill payload | `PayloadContextError`; template left untouched |
| install or update run over a settled store | `ensure_context()` never overwrites an existing store |
| store deliberately pointed inside the payload | `install.py` refuses before copying anything unless `--shared` opts in |
| unmarked context inside the payload settled | `PayloadContextError`; only a declared `scope: shared` store is admitted there |
| `scope` key absent or blank | read as `user`; genericness is never inferred |
| build noise present in the working tree at install time | excluded from the payload |
| install directory name drifts from the skill's declared `name:` | `--verify` fails |

## Enforced experiment-adapter invariants

Experiment layer, not the discipline: these hold for `experiment/` and the
`context_kind` hook it needs, and none of them is part of the 0.8.0 release
surface.

| Attack | Adapter response |
|---|---|
| person context relabelled `context_kind: environment` | `invalid`; the required metadata keys differ and the evidence sections do not overlap |
| environment context relabelled `context_kind: person` | not ready; `onboarding` is missing and person evidence is absent |
| person evidence reused to settle an environment context | `reconnaissance_required`; the headings themselves are disjoint |
| `complete_onboarding()` aimed at an environment context | `ContextKindError` |
| `complete_reconnaissance()` aimed at a person context | `ContextKindError` |
| unrecognised `context_kind` | `invalid` rather than silently treated as a person |
| ephemeral context read by a later trial | `expired`; a reused volume surfaces as a state, not as contamination |
| ephemeral context read with no trial asserted | `invalid`; a relation cannot answer with an operand missing |
| ephemeral context with no `trial_id` | `invalid`; ephemerality without a binding is unverifiable |
| one trial settling another trial's context | refused |
| one trial closing another trial's context | refused; the file is preserved |
| settlement attempted on a frozen or read-only context | `FrozenContextError` |
| frozen context declared immutable on a writable file | `describe_frozen()` reports the filesystem, not the frontmatter |
| unsettled context frozen as if it were ground | refused |
| persistent accumulating context used in a pilot trial | `PilotAdmissibilityError`; later trials would inherit earlier trials' information |
| person context carried into a benchmark trial | `PilotAdmissibilityError`; no arm of the pilot carries a pedagogy |
| reconnaissance marker flipped with sections left blank | `reconnaissance_required` |
| `Skill(foo) + Environment(bar)` digested as `Environment(foo) + Skill(bar)` | different digests; role and kind are committed separately |
| two-operand resolution digested as a three-operand one | different digests; arity is committed |
| operand identity crafted to impersonate the serialization | different digests; every value is a quoted string in a typed structure |
| resolution operands reordered after the fact | `verify_resolution()` fails |
| canonicalization rules changed without notice | `resolution_version` is inside the hashed payload |

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
- **Store lifetime is the host's, not the module's.** `payload_root()` decides a *location* question — is this file in the part of the install that gets replaced — which is decidable in one session. Whether a store outside the payload survives a reboot, a container reset, or an ephemeral home directory is not observable from inside the process that writes it: a successful write to a discarded filesystem is byte-identical to a durable one. A host whose entire filesystem is scratch will pass every check here and still lose the context. That is declared, not enforced.
- Context completion proves a **structural receipt**, not the truth of a learning claim. LongHow + user settlement remain the semantic boundary.
- Rename/new-basename forks are detectable from the file itself. A byte-for-byte copy of an entire settled installation under the same filenames is not distinguishable without an external installation identity/custody mechanism; this release does not pretend otherwise.
- **Reconnaissance records observations, not conclusions — as a rule, not a check.** The structural validator proves an environment context's sections are populated. It cannot tell "pytest is the verifier here" from "the best way to solve this task is X", and the second would make the treatment a solver rather than a discipline. Documented in `experiment/PILOT-0001/reconnaissance.md`; enforced by review.
- **A frozen context's read-only mount is the harness's, not the module's.** `freeze_context()` drops the file to read-only permissions and publishes a digest, so a change is detectable afterwards. Preventing the change requires the mount.
- The agency modifier is intentionally not implemented as a brittle pronoun parser. The skill binds the actor from language/context; the execution kernel remains domain-neutral.

These boundaries keep the reference system small enough to audit. Closing them requires host identity, isolation, authenticated evidence, or policy infrastructure rather than more prose in the kernel.

## Lifecycle attacks

- **declined persists** — `decline_onboarding()` produces `declined`; later inspection does not return `onboarding_required`.
- **ready cannot be re-completed** — `complete_onboarding()` refuses a ready context so `context_id` cannot churn.
- **onboarding text is one-line** — CR/LF in onboarding evidence is flattened before persistence.
- **structural, not semantic** — evidence bullets prove only minimum shape; truth and quality remain a human judgment.
