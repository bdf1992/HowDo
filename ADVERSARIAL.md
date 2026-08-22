# Adversarial notes — v0.9.0

The runtime is a small protocol kernel, not a complete trust system. v0.9 makes a request's declared I/O portable and issues the domain artifact the discipline had only ever described, while keeping the agency modifier above the execution kernel.

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

## Enforced first-run notice invariants

The plugin ships one `SessionStart` hook, and `SKILL.md` refuses to load the
discipline uninvited. Those coexist only while the hook stays a notice to the
person rather than context for the agent, so the distinction is enforced rather
than asserted. `tests/test_plugin.py::NoticeTests` is the enforcement.

| Attack | Response |
|---|---|
| hook emits `additionalContext` | no code path produces it; asserted absent from the whole payload |
| hook speaks after a decline | silent — only `missing` and `onboarding_required` print |
| hook speaks after a deferral | silent, same rule; a postponement is an answer |
| hook nags a settled context | silent |
| quiet path emits `{}` and is read as context | quiet path writes zero bytes |
| hook instantiates the store as a side effect | reads only; store absent afterwards |
| malformed store breaks every session start | caught; exits 0 silently |
| hook hard-codes a path that moves on update | must use `${CLAUDE_PLUGIN_ROOT}` |
| a second hook joins on another event | only `SessionStart` may be declared |
| installer note and hook note drift apart | one source, `howdo.notice`; equality asserted |

## Declared boundaries

The notice reaches whatever the host does with `systemMessage`. If a host ever
routed that into model context, the boundary would move without this repository
changing — the guarantee is "we never emit `additionalContext`", not a claim
about what a host does with what we do emit. `claude plugin details` reporting
the hook as harness-only is the current corroboration, not a contract.

## Enforced request-contract invariants

Optional runtime surface. These hold for `runtime/howdo/contract.py`, and the
kernel invariants above are unchanged by it: a contract's rules compile into
ordinary `Check` objects and go through the same gate.

| Attack | Contract response |
|---|---|
| contract loaded onto a host that lacks a required capability | `bind` returns `Unsupported` before anything resolves |
| consequential contract bound to a read-only host | refused at bind |
| consequential contract shipped with no declared result shape | refused at construction |
| consequential contract leaning on a gate the host happens to supply | refused; at least one precondition rule must travel with it |
| host-supplied checks used to replace the contract's own | additive only; the contract's rules always apply |
| clause operand that cannot serialize | refused; a contract that only runs here is not portable |
| unknown operator, or an unknown key in a loaded contract | refused rather than dropped |
| operand supplied to an operator that reads none | refused; an ignored field looks load-bearing |
| contract declaring a canonical version this host does not know | refused rather than partially read |
| rules reordered after the fact | different digest |
| inputs or expected values that do not match the declared shapes | refused at resolve, before admission |
| result that does not match the declared shape | residual routes to `contract`, not `postcondition` |
| shape residual used to mask an invariant residual | invariant outranks it; `settle` keeps refusing |
| `True` accepted where an integer was declared | refused; a flag is not a count |
| declared inputs mutated after the resolution was built | snapshotted at `Request` construction |

## Enforced issuer and index invariants

An issuer is a way to manufacture ground, so most of these are refusals. Optional
runtime surface; the kernel invariants above are unchanged.

| Attack | Issuer response |
|---|---|
| artifact issued from a plan rather than a run | no constructor takes one; `issue_from_run` requires a resolution and its residual |
| residual from a different run supplies the example | refused; the residual must belong to that resolution |
| contract describing a route the run did not take | refused; contract path must match the resolved path |
| artifact issued with no map | refused; a path with no map is untestable |
| artifact declared `grounded` with no observation | refused at construction |
| artifact left `untested` while claiming an observation | refused at construction |
| residual that did not match used to ground an artifact | refused; the route is reported in the error |
| edited artifact inheriting its predecessor's grounding | `revise` drops it to `untested` and clears the observation |
| different content issued over an existing artifact | refused; a revision is required to supersede |
| artifact file edited outside the issuer | refused on load; the stored content digest no longer matches |
| grounding an artifact treated as editing it | content digest excludes lineage, so promotion is not a new artifact |
| `Jira.Workflow` and `jira.workflow` forking one concern into two | refused; the concern is slug-constrained |
| artifact issued into the skill payload | refused; the next install would discard it with no error raised |
| index trusted as a second source of truth | rebuilt from the artifacts on every read |
| index deleted or corrupted | a rebuild, not a loss |
| one unreadable artifact costing the whole index | reported in the view; the rebuild still terminates |
| grounded artifact loaded into a drifted paradigm | `staleness()` reports the revision gap the kernel cannot see across storage |

## Enforced emitter invariants

Emission installs something. These hold for `runtime/howdo/emit.py`.

| Attack | Emitter response |
|---|---|
| untested artifact emitted as an installed skill or workflow | refused without an explicit override |
| override used to ship a draft as settled ground | the output is stamped `Untested` in both formats |
| grounding presented as correctness in the generated skill | the body says one confirming run, not best route |
| concern that cannot project to a legal skill name | refused; not silently truncated or mangled |
| skill name longer than the specification's 64 characters | refused |
| description over the specification's 1024 characters | truncated at the cap |
| generated description broad enough to load on any question in the domain | carries "not a general-purpose helper" and "not by itself a reason to load it" |
| angle brackets reaching frontmatter from an intent or concern | stripped; they can inject instructions into a system prompt |
| directory name drifting from the skill's `name` | `write_skill` owns the layout; the caller cannot choose it |
| quotes, backticks, `${...}` or backslashes in a map breaking the generated script | values are emitted as JSON literals; a parser check covers it |
| generated workflow loading a module | none is emitted; a script containing `import()` fails before a run starts |
| description or compatibility containing `: ` emitted as a plain scalar | quoted; an unparseable frontmatter block fails packaging outright rather than degrading |
| a Claude Code extension field emitted on the portable path | the default `spec` target is restricted to the six fields the specification accepts |
| consequential artifact left auto-invocable as a Claude Code skill | `disable-model-invocation: true`, the documented case for a workflow with side effects |
| `compatibility` over the specification's 500 characters | refused |
| unknown emission target | refused rather than silently treated as portable |
| an existing skill or workflow silently replaced | refused without `overwrite=True` |

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
`context_kind` hook it needs, and none of them is part of the 0.9.0 release
surface.

| Attack | Adapter response |
|---|---|
| pilot adapter reaches end users by sitting in `runtime/` | `install.py` copies `runtime/`; the adapter is not there, and an install test imports the installed package in a clean interpreter and finds no pilot API |
| installed skill points at a directory it does not ship | no payload file names `PILOT-0001`; the kind hook that remains is generic |
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
| receipt asserts `certifies: true` on a judge-scored trial | refused at write time and rechecked at verification, so a recomputed digest does not help |
| result refiled as infrastructure noise after the fact | `failure_class` is refused on `pass` and `fail` and required on `error` and `excluded` |
| confirmatory trial cites no preregistration | refused; it is an exploratory trial wearing the word |
| trial log accepts receipts in any order | `append_receipt()` refuses a non-increasing `run_sequence_index` per experiment |
| a wrong receipt edited or deleted | corrections append against its digest; the original is never touched |
| trajectory stored as a filesystem path or inline text | refused; custody references must be sha256 content addresses |
| control arm reports reconnaissance, or a treatment arm reports none | refused; the arm and the recon outcome must agree |
| qualification record edited to promote a rejected task | `verify_qualification()` recomputes the outcome, not just the digest |
| judge-scored task certifies capability | derived outcome is `research_only`; certification is unreachable |
| preregistration digested while a commitment is still a proposal | refused, and the refusal lists what is open |
| organism lock fingerprinted from an unfilled template | refused; every required field is checked, not just the first |
| observed envelope changes the organism fingerprint | it is excluded from the hashed payload by construction |
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
- **A host's capabilities are declared, not authenticated.** `bind` proves a contract was not loaded somewhere it says it cannot run. It does not prove the host told the truth about what it can do, and it cannot: the same class of boundary as the caller-supplied comparator.
- **A contract binds the declaration, not the executor.** It states what the operation must make observable; whether the executor pursues that or something else is caught at Look, not at the door. A contract makes the lie checkable, not impossible.
- **The clause set is closed on purpose.** A predicate it cannot state has to ship as a host-supplied `Check`, and that check does not travel with the contract. The contract's own rules still gate the operation, so the portable floor holds while the local ceiling does not — but a contract whose real gate is local is portable in form only, and nothing here detects that.
- **The portable target cannot restrict who invokes a skill.** `disable-model-invocation` is a Claude Code extension, and emitting it on the path that goes to claude.ai or the Skills API fails packaging with a hard error. So a consequential artifact rendered for that target says so in its body and nothing enforces it. Prose in a skill body is an instruction, not a permission boundary.
- **An emitted skill is a projection, and drifts the moment the artifact moves.** Nothing tracks what was emitted or re-emits it: `emit` is stateless by design, in the same spirit as the index being rebuilt rather than stored. An installed skill whose domain-how has since been revised will keep being loaded, and only re-emission fixes that.
- **A generated workflow can state Look's discipline but cannot enforce it.** The kernel structurally withholds the executor report from the observer; a script can only instruct an agent not to read it back. That instruction is prose in a prompt, and an agent may ignore it.
- **An issued artifact is structurally grounded, not correct.** `ground()` proves a residual matched on one run. It does not prove the map is good, the path is the best one, or that the concern was worth an artifact — the same boundary `onboarding: complete` already declares one level up. Ablation across runs is the semantic test, and it is not in the runtime.
- **Staleness is reported, not enforced.** `staleness()` answers when asked. Nothing refuses a stale artifact at load, because whether a revision gap invalidates a given artifact is a domain judgment the kernel has no basis to make.
- **A minted artifact compounds what a spoken one did not.** A bad HowDo used to cost one answer. An issued one pre-loads every later run on that concern, so the `untested` marker and the index's status filter are load-bearing rather than decorative. Nothing prevents an agent from reading a `grounded` artifact whose grounding run was itself misconceived.
- The agency modifier is intentionally not implemented as a brittle pronoun parser. The skill binds the actor from language/context; the execution kernel remains domain-neutral.

These boundaries keep the reference system small enough to audit. Closing them requires host identity, isolation, authenticated evidence, or policy infrastructure rather than more prose in the kernel.

## Lifecycle attacks

- **declined persists** — `decline_onboarding()` produces `declined`; later inspection does not return `onboarding_required`.
- **ready cannot be re-completed** — `complete_onboarding()` refuses a ready context so `context_id` cannot churn.
- **onboarding text is one-line** — CR/LF in onboarding evidence is flattened before persistence.
- **structural, not semantic** — evidence bullets prove only minimum shape; truth and quality remain a human judgment.
