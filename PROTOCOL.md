# Protocol boundary — proposed

Status: **proposal**, answering #28's questions from what the code enforces
today. Each answer is marked *enforced* (a test would fail if it broke; see
`tests/test_protocol.py`) or *proposed* (a decision this document puts up for
adoption, changeable until it is). Nothing here moves a version carrier.

## What is public protocol

*Enforced.* The public protocol is what `howdo` exports, in four groups:

- **Operation kernel** — `Paradigm`, `Request`, `Check`, `GateEvidence`,
  `Resolution`, `Fizzle`, `Admission`, `Outcome`, `Observation`,
  `ObservationContext`, `Residual`, `Settlement`; the verbs
  `resolve → admit → operate → observe → settle`; the `Route` and `Agency`
  vocabularies; `ExecutionError`. An executor failure is protocol, not an
  accident: the error outcome and its observability are part of the contract.
- **Durable context** — the `ContextState` vocabulary, `ContextStatus`, the
  kind/lifetime/authority vocabularies, `inspect_context`, `ensure_context`,
  the settlement helpers, `resolve_context_path`/`default_store_path`,
  `fork_context`, and the exceptions (`TemplateContextError`,
  `PayloadContextError`, `ContextKindError`, `ContextLockError`).
- **Request contracts** — the `contract.py` exports and `CONTRACT_VERSION`.
- **Domain artifacts** — the `domain.py`, `emit.py`, and `publish.py` exports,
  `DOMAIN_VERSION`, and the serialized domain-how record.

`tests/test_protocol.py` pins these names: removing or renaming one fails the
suite; adding is allowed.

## What hosts may replace

*Proposed.* Reference-implementation details, replaceable without a protocol
claim: id generation (`paradigm_…`, `context_…` prefixes are not protocol),
wall-clock timestamps, the lock-file and temp-file mechanics behind context
settlement (the *guarantee* — atomic replacement, stale authors refused — is
protocol; the mechanism is not), the index/catalogue storage (both are rebuilt
from artifacts, never authoritative), and the flat frontmatter parser.

## Compatibility policy

*Proposed, with the additive half enforced by test shape.*

- **Dataclass fields**: additive with a default = minor. Removing, renaming, or
  changing the meaning of an existing field = the next major (pre-1.0: a minor,
  called out in `CHANGELOG.md` as breaking). The tests assert the known field
  set is a *subset* of the actual one, so additions pass and removals fail.
- **Vocabularies** (`Route`, `Agency`, `ContextState`, contract `OPS`/`TYPES`):
  new values = minor; a consumer must treat an unknown value as a refusal, not
  a default. Removing a value = breaking.
- **Exceptions**: a new exception type is new public surface (minor). An
  existing one may gain fields, never lose them.
- **Serialized records**: governed by their own format versions, below — the
  skill release version does not version persisted artifacts.

## Persisted artifacts and their format versions

| artifact | version carrier | unknown-version behavior |
|---|---|---|
| durable context (`CONTEXT.md`) | `howdo_context` frontmatter key | **open — see below** |
| domain-how record | `version` field against `DOMAIN_VERSION` | *enforced*: refused at construction and on load |
| request contract | `version` field against `CONTRACT_VERSION` | *enforced*: refused rather than partially read; unknown keys refused |
| index / catalogue / `SUBSKILLS.md` | none | derived views, rebuilt from artifacts; no version needed |

**The open row:** `inspect_context` requires the `howdo_context` key to exist
but does not judge its value, so a future format `"3"` store would be read by
today's validator with today's rules. Proposed rule, for adoption before any
format `"3"` exists: a context whose `howdo_context` value is not one this
release knows reports `invalid` naming the version, and settlement helpers
refuse it — refusal over partial reads, matching the contract loader. This is
a behavior change to `inspect_context` and belongs to whichever release adopts
it, not to this document.

## Migration and refusal

*Proposed.* One rule everywhere: **an unknown future format is refused, never
partially read and never silently migrated.** Migration is an explicit,
lineage-preserving operation (the way `fork_context` opens a new lineage with
`parent_context_id`), performed by the release that introduces the new format.

## Settled by the RC hardening pass

- **Settlement locality**: the kernel enforces exactly *no discrepancy, no
  write* (a matched residual cannot carry a patch) plus the one-layer default.
  Mapping arbitrary domain evidence to the exact indicted layer is host-owned
  and stays so; the kernel makes no locality claim beyond top-level keys.
- **Execution failure**: `operate()` exposes it as protocol — `ExecutionError`
  carrying an attributable `Outcome` that `observe()` accepts. Not an adapter
  concern.
- **Durable-context CAS**: internal. The public surface is the settlement
  helpers; atomicity and stale-author refusal are guarantees of those helpers,
  and no expected-preimage parameter is exposed. Revisit only with a real use
  trace that the helpers cannot serve.

## Explicitly not protocol

*Proposed.* `Trace` and LongHow are skill-level practice — vocabulary the
discipline uses, not objects the runtime exports or versions. A host that
persists traces owns their format.

## What 1.0 stabilizes

Unchanged from `CONTRIBUTING.md`: 1.0 is reserved for the Skill Graph and is
not reachable by polish or packaging maturity. Everything in this document
describes the 0.x line; adopting the proposals above is a prerequisite for the
1.0 conversation, not the conversation itself.
