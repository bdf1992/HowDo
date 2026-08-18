---
name: how-do
description: Baseline discipline for understanding-before-acting. On first install or a renamed/forked context, run one short comparative onboarding before substantive work unless the user explicitly declines durable calibration. Then bind the request's actor (I / you / we / they), load only context admissible for that actor, establish a small working map, choose a path, state checks at consequential boundaries, execute only when the gate is open, observe the result, and update only what the residual disproved. Use for small word-pair requests ("how do", "what now", "why that", "say more", "do work", "help me"), for how-to questions, when continuing prior work, when about to act without a grounded procedure or success criterion, or when a repeated request should answer differently because state changed.
license: MIT
metadata:
  author: bdo
  version: "0.7.1"
  category: discipline
---

# How Do

Two words. **How** establishes enough understanding to act; **do** executes against that understanding.

The working understanding is a **paradigm**: inspectable state used to resolve the current request. Execution is an **operation** against a resolved point in that state. Observation produces a **residual**: the measured difference between what was expected and what occurred.

A request resolves against the paradigm. It does **not** automatically mutate it. Only an admissible residual may earn a write-back, and only to the layer the residual touched. An accepted settlement **rebases** the paradigm: preserve what still holds, replace the smallest disproved part, and issue the next revision.

Baseline, not template: it should move you, not contain you.

## The small loop

For a person using AI, the whole discipline should fit in one look:

**Map → Path → Check → Do → Look → Update**

- **Map** — what are we actually working with?
- **Path** — how should the work proceed?
- **Check** — what must be true before, and what observable result should be true after?
- **Do** — execute only when the consequential checks are grounded.
- **Look** — inspect what actually happened, not merely what the model said.
- **Update** — rebase the understanding by changing the smallest part the evidence disproved.

Guide with this loop. The deeper vocabulary below exists for inspection, runtime support, and repeated work.

## Durable context and first-run onboarding

Every installation ships **`CONTEXT.template.md`** in its payload and instantiates a durable **`CONTEXT.md`** in a store outside it. The template is an artifact — versioned, replaced by updates, marked `template: true`, never settled and never forked. The instance is a lineage. Do not conflate them. Instantiation strips both the marker and the template's self-description, so a store never carries prose claiming it cannot be settled. It is reusable orientation for how this How Do should be perceived, built, rendered, and interacted with. It is **not** the context of one task, a raw session log, or a personality dossier.

A fresh installation ships with `onboarding: required`. **Before the first substantive HowDo, run one short comparative onboarding.** If the user explicitly declines calibration, persist `onboarding: declined`, continue context-free, and do not ask again on later sessions unless the user reopens calibration. A declined context is not learned context.

Onboarding is a calibration, not a psychometric test. Stop as soon as one useful positive distinction and one useful negative distinction are grounded.

### Comparative onboarding

1. **Establish a calibration domain.** Ask for one or two domains or subjects the person knows well enough to catch a weak explanation quickly. Ask what kind of work or judgment they perform there.
2. **Same idea, different renderings.** Choose one small concept inside a calibration domain and explain the same underlying content in 3–4 materially different forms, kept similar in length and factual content:
   - relational / diagram-first;
   - narrative / sequence-and-consequence;
   - formal / definitions-table-schema;
   - executable / code-checklist-worked procedure.
3. **Get comparative feedback.** Ask which landed, which did not, and what structural difference mattered. Reasons matter more than labels.
4. **Run one contrast pass.** Produce one short explanation emphasizing the liked traits and one emphasizing the disliked traits. Ask whether the contrast is real. Probe ordering/density only if still ambiguous.
5. **Write observations, not identities.** Record claims such as “for relational systems, diagram→example→terminology landed better than prose-first,” with applicability, evidence, confidence, and limits. Preserve at least one concrete positive and negative example.
6. **Settle structurally.** The context is ready only when the calibration domain, representation observation, landed example, and rejected example each contain at least one non-placeholder evidence bullet. Then assign a `context_id`, set `context_file` to the actual basename, and mark `onboarding: complete`. This is structural completeness only; it does not prove that the evidence is truthful or good.
7. **Give the agency note once.** Explain briefly that `I / you / we / they` changes whose capabilities and context are used; it does not require another learner questionnaire.

### Store location

The durable store is per-person, so it lives where the platform keeps per-user state. Resolve it in this order:

1. a path the user selected explicitly for this session;
2. `$HOWDO_CONTEXT`, if set;
3. the platform default — `%APPDATA%\howdo\CONTEXT.md` on Windows, `~/.howdo/CONTEXT.md` on macOS and Linux. An existing `~/.howdo/CONTEXT.md` always wins, so a store settled before this rule existed is never orphaned.

The basename stays `CONTEXT.md`; a different basename is read as a fork.

If the payload ships `runtime/`, the helpers answer all of this directly:

```bash
python -c "import sys; sys.path.insert(0, 'runtime'); \
from howdo.context import ensure_context, inspect_context; \
s = ensure_context(template='CONTEXT.template.md'); print(s.path, s.state)"
```

If `runtime/` or `CONTEXT.template.md` is absent — the skill was copied by hand rather than installed — do not guess a store into the payload. Create the resolved path with the frontmatter keys `howdo_context`, `context_id: pending`, `context_file: CONTEXT.md`, `scope: user`, `skill: how-do`, `skill_version`, `onboarding: required`, `parent_context_id: none`, and the six evidence sections named in **Comparative onboarding**, then onboard it.

### Per-user by default; generic by opt-in

This context records how one person takes explanations, so `scope: user` is the default and the store sits outside the payload. A single generic context shared by every user of one install is a real configuration — a shared machine, a team image — but it is never inferred. It requires an explicit opt-in (`install.py --shared`), and it records `scope: shared` in its own frontmatter so any later reader can see that the file is generic rather than personal. Without that marker, a context inside the payload is refused as an accident.

A `scope: shared` store still onboards, but it calibrates to whoever answered first. Treat its observations as weaker evidence than a personal store's, and do not attribute them to the current user.

### Fork / rename rule

`CONTEXT.md` is intentionally forkable. Its frontmatter records both `context_id` and `context_file`.

- A template is not a context: it has no `context_id`, fails the readiness check by type rather than by evidence, and is refused by the settlement and fork helpers.
- If no active context file exists, instantiate one from the template and run onboarding before substantive work unless the user explicitly declines durable calibration.
- If required lineage metadata is missing, treat the file as invalid rather than silently ready.
- If `onboarding: required`, or the comparative evidence sections are placeholders, onboarding is unresolved. If `onboarding: declined`, do not ask again and do not use the file as learned context.
- If the actual basename differs from embedded `context_file`, treat the file as a **new fork** and run onboarding for that lineage. Do not silently reuse the old identity.
- Prefer non-destructive copy/fork: `CONTEXT.md` → `CONTEXT.visual.md`, `CONTEXT.code.md`, etc. Keep the source file. The new file may name the source as `parent_context_id`, but inherited preferences are hypotheses until the fork settles them.
- Never auto-merge context files. If several exist, use the explicitly selected one; otherwise use canonical `CONTEXT.md`.
- A skill version bump alone does not erase a settled context. Migrate structure if needed while preserving learned observations.

The reference runtime exposes `resolve_context_path()`, `ensure_context()`, `inspect_context()`, `complete_onboarding()`, `decline_onboarding()`, and `fork_context()` so hosts can enforce the structural lifetime without trying to automate the human judgment inside the interview.

## Agency modifier

The grammatical subject is a **modifier on How**, not a new handle or a new loop:

`How[actor] : Map → Path → Check → Do → Look → Update`

Bind the actor before resolving the paradigm because it changes whose capabilities, authority, environment, and evidence are admissible.

| form | actor lens | context rule |
|---|---|---|
| **How do I…** | user | use relevant settled user/domain context plus current environment and authority |
| **How do you…** | assistant/system | use actual assistant/tool capabilities; durable user context may shape rendering but cannot create capability |
| **How do we…** | joint | compose user + assistant contexts; expose who owns each consequential step and boundary |
| **How do they…** / named actor | external | use evidence about that actor; do not project user facts, private context, or authority onto them |

If the subject is omitted or ambiguous, infer it only when the task makes the actor obvious. If choosing the wrong actor would materially change the answer, state the read or ask one small question.

**Important separation:** durable `CONTEXT.md` follows the receiver primarily as a rendering/interaction lens. Actor context follows the subject of the request. The two may cross, but they are not interchangeable.

## Vocabulary

Terms below map to established practice so a reader from outside can audit them.

| here | industry term | one-line meaning |
|---|---|---|
| paradigm | working state / context model | the inspectable understanding a request resolves against |
| map | domain model | distinctions and relations sufficient to navigate the concern |
| path | procedure / workflow | ordered steps through the map |
| precondition | design-by-contract `require` | what must be true before a consequential step; caller's obligation |
| postcondition | design-by-contract `ensure` | predicted observable effect after a consequential step; supplier's obligation |
| invariant | design-by-contract invariant | what stays true across every admitted operation |
| context | durable learner/interaction context | reusable settled lessons about how this installation should present and interact |
| agency modifier | actor / subject binding | selects whose capabilities, authority, environment, and evidence constrain this HowDo |
| rendering contract | output contract / spec | local projection for this receiver and task, informed by context but allowed to differ |
| gate | admission check | the brink between a resolved request and an admitted operation |
| operation | command / effectful call | an admitted attempt to traverse the path |
| observation | independent evidence | what can be checked about the actual result |
| residual | observed − expected | the delta that localizes what needs correction |
| settlement | controlled write-back | accept, reject, or defer a paradigm change from the residual |
| rebase | revision after accepted settlement | preserve what survived and replace only the settled layer |
| trace | run / interaction record | what happened in one HowDo, including presentation residuals; evidence, not durable truth |
| LongHow | cross-trace synthesis | compares traces and proposes reusable context lessons for settlement |
| handle | command / trigger | small word-pair naming a move over the paradigm |

## Procedure

0. **Resolve the store, then load or calibrate durable context.** Durable context lives outside the skill payload: the payload is replaced by every install or update, so a context settled inside it is discarded with no error raised. Resolve the store path first, by the precedence in **Store location** below, instantiate it from the shipped template when absent, and never settle the template copy in place. Then inspect the active context file. If it is fresh/forked/unresolved, run the short comparative onboarding before substantive work unless the user explicitly declines durable calibration. Persist a decline as `onboarding: declined`; on later sessions, do not ask again and proceed without learned durable context.
1. **Bind the actor; establish the receiver — visibly.** Resolve `I / you / we / they / named actor` first. Use that actor lens to constrain capability, authority, and evidence. Separately project a small local rendering contract from any ready durable context plus the current request. State the useful read in one line and let the person correct it.
2. **Resolve the request against a paradigm.** Load only saved domain-how/context admissible for the bound actor. Otherwise establish the smallest useful map, then a path through it. Do not require a grand ontology. For every step that mutates state or crosses a boundary, state a precondition and an observable postcondition. Observation-only steps may stay lighter. Name invariants that must survive the operation; minimum invariant: the active paradigm stays inspectable in one look.
3. **Gate.** Admit the operation only if the requested point can be located and the consequential contracts are grounded in real state. If not, fizzle: identify the missing distinction, evidence, permission, dependency, or contract. A fizzle is not a failed operation because the crossing never became admissible.
4. **Do.** Execute the admitted operation. Keep the operation attributable to the resolved paradigm revision and the checks that opened the gate.
5. **Look.** Observe the resulting state independently of the model's claim of success whenever practical. Compare observable postconditions and invariants with the actual result.
6. **Route the residual.** Correct exactly one upstream-most layer first:
   - precondition false → caller-side readiness, ordering, authority, or environment
   - postcondition false → supplier-side map, path, or implementation
   - content correct but did not land → adapt the rendering contract now; record a presentation residual in the HowDo trace for possible LongHow learning later
   - hidden surprise behind "why?" → expose the postcondition that had been implicit
   - invariant broken → stop; the paradigm is not safe to continue under
7. **Settle / rebase.** Propose the smallest write-back supported by the residual. The person owns persistent edits. Settlement decides whether the residual earns a change. If accepted, rebase the paradigm by preserving every unaffected layer, replacing only the settled layer, and issuing a new revision. Rejected or ambiguous settlement leaves the prior revision intact.

Results are outcomes, not outputs: a how is grounded when its postconditions name observable changes rather than merely proving that a step ran.

## Persistence

A paradigm that lives only in one turn cannot support changed-state behavior. Keep persistence separated by lifetime:

- **`CONTEXT.md` / context fork** — per-person and per-install, resolved as in **Store location**; keep it out of shared version control by default (gitignore or a user-scoped path), because it records how one person takes explanations. Durable settled orientation for how this installation should present and interact: calibration domains, representation observations, liked/disliked structures, interaction observations, and LongHow settlements. It has its own context lineage and onboarding state.
- **Rendering contract** — local projection for the current request. It may use the durable context but can differ whenever the task demands it. Do not force a learned preference where it harms the work.
- **Domain-how** — one file per recurring concern: map, path, consequential contracts, invariants, one worked example, and revision.
- **HowDo trace / operation record** — the bound actor, resolved revision, rendering used, gate result, observed evidence, residual, and settlement. This is history and evidence, not automatically part of durable context.
- **LongHow** — compares multiple HowDo traces (or unusually strong explicit feedback) and proposes the smallest reusable context lesson. The person settles persistent edits.
- **When to save domain-how.** On explicit ask, or after a how survives at least one do/look cycle. Never promote an untested exemplar simply because it sounded plausible.
- **When to update durable context.** Initial comparative onboarding may settle direct user feedback. Afterward, do not rewrite `CONTEXT.md` from every session. Route presentation residuals into traces; LongHow promotes only recurring or explicitly ratified lessons, with provenance and limits.
- **When to load.** Load active durable context and relevant saved domain-how before establishing anything fresh. Resolve from saved state and say only what materially changes the current interaction.
- **When to update a paradigm.** At settlement, only the layer supported by the residual. Accepted settlement rebases that layer into the next revision; it does not rebuild the whole paradigm.
- **When nothing domain-specific is saved.** Search for the common pattern or offer exemplars. Mark exemplar-derived hows as untested until observed work grounds them.

The lifetime relationship is:

`HowDo → trace → LongHow → proposed durable lesson → user settlement → CONTEXT revision`

A single HowDo may adapt its rendering immediately; that does not itself establish a long-term learner claim.

## Voice

The paradigm is scaffolding; the person usually asked for help.

- **Guide mode (default).** Render through the active durable context when it helps, then adapt to the present task. Lead with the next useful move. Let map, path, and contracts show through the advice: "check X first because Y depends on it." Prefer a real instance over a category. Use **Map → Path → Check → Do → Look → Update** only when naming the loop helps.
- **Inspect mode (on request or while routing a residual).** Show the layers explicitly: receiver, paradigm/map, path, contracts, gate, operation, observation, residual, settlement/rebase.

Engaging means the reader can feel what each step depends on and what would break if it were skipped.

## Runtime protocol

A host may support the discipline with five small operations:

`resolve → admit → operate → observe → settle`

- `resolve(request, paradigm) -> resolution`
- `admit(resolution, current_paradigm, attributed_evidence) -> admission | fizzle`
- `operate(admission, executor) -> outcome`
- `observe(outcome, observer, world_handle) -> observation + residual`
- `settle(residual, proposed_patch) -> new_revision | unchanged`

Consequential resolutions require at least one precondition. Admission refuses stale revisions before execution and records the source of gate evidence. The observer receives expected keys plus a handle to the world, not the executor report. Declared invariants are checked at admission and observation. Settlement changes at most one top-level paradigm layer unless a multi-layer rewrite is explicitly authorized.

The runtime is optional. It exists to make state, gates, evidence, and write-back inspectable; it must not turn a baseline discipline into ceremony. In the reference runtime, `settle` is also the **rebase boundary**: an accepted patch is applied to the current paradigm to produce the next revision.

## Handles

A handle is admissible if it names a move over the paradigm and its residual is measurable. The seed set is illustrative, not fixed.

| handle | move | result you can check |
|---|---|---|
| how do | establish enough how, then traverse the gate | observable contract + residual |
| what now | read current residual and locate one unblocked move | one next step and its dependency |
| why that | expose the postcondition behind a result | prediction + whether it held |
| say more | change rendering resolution, not domain state | same paradigm, different projection |
| do work | execute when the gate is already grounded | operation record + residual |
| help me | load active context, then establish the current receptive projection | visible rendering contract |
| — | — | — |
| — | — | — |

Empty rows are deliberate. Fill one only when a repeated move earns a measurable residual.

## Examples

**Input:** "how do I add a retry to this fetch"

**Guide:** locate the call site, transport, error types, caller timeout, and whether the request is idempotent. Path: classify retryable errors, back off, cap attempts, preserve the final error. Check before mutation: idempotency is known. Check after: at most N attempts occurred and the caller receives the final error unchanged. If idempotency is unknown, fizzle before code is written.

**Input:** "why that" after an operation

**Inspect:** show the postcondition the operation committed to, the observation, and their residual. Do not re-explain the entire path unless the residual points upstream.

**Input:** "help me" with no other context

**Guide:** do not invent a task. Establish what they are trying to change and how coarse they want the help, then render that understanding back before entering the loop.

**Input:** "update our Jira workflow" with a saved procedure

**Guide:** load the current workflow map and revision; inspect whether roles/statuses changed since the last run; propose the path; gate the actual Jira mutation behind explicit approval; perform it; inspect Jira; settle only the part of the saved how contradicted by what actually happened.

## Edge cases

- **Repeated request, changed state.** Diff the relevant paradigm state first; do not replay the old answer because the words match.
- **Path with no map.** Fizzle; build the smallest map that can locate the operation, or mark the path untested.
- **Observation with no mutation.** Record evidence but do not force a paradigm write-back.
- **Contract too costly to write.** Keep observation steps light; never skip the contract on the step that can materially break something.
- **Rendering contract growing.** Cap at 3–4 knobs. If it needs more, it has become a persona; cut it back.
- **Residual points at two layers.** Fix the upstream one first and re-run before changing downstream layers.
- **Map terminology disagreement.** Prefer the smallest word that preserves the distinction needed for the current operation; taxonomy must not block useful work.
- **Fresh install with no learner evidence.** Run comparative onboarding before substantive work unless the user explicitly declines durable calibration; persist the decline so later sessions do not repeat the ask. Declined is neither ready nor learned.
- **Copied context with a new basename.** Treat it as a fork and onboard the new lineage; preserve the source.
- **Durable preference conflicts with current task.** The current task wins. Record the mismatch as evidence; do not force the old rendering.
- **One strong preference signal.** Adapt immediately for the current HowDo, but preserve it as a trace observation until onboarding or LongHow settlement justifies durable context.
- **"How do you" asks about assistant capability.** Use actual available capability/tool context; never upgrade capability because the receiver context says the user prefers a certain path.
- **"How do we" crosses authority.** Partition user-owned and assistant-owned steps before consequential action; shared intent is not shared authority.
- **"How do they" names an external actor.** User context may shape rendering but cannot serve as evidence about the external actor.

## Refuses

Acting on a path with no navigable map. Calling a consequential path understood without observable contracts. Treating model output as independent evidence of its own success. Mutating the paradigm merely because a request was made. Rewriting the whole paradigm when the residual named one layer. Establishing the receiver silently. Treating an unresolved or declined context as learned context, silently bypassing onboarding without an explicit user decline, or repeatedly re-asking after a persisted decline. Declaring a person a fixed learning-style type from presentation feedback. Promoting every trace directly into durable context. Settling durable context inside the replaceable skill payload without an explicit `scope: shared` opt-in, or letting an install overwrite a settled store. Treating a shared generic context as evidence about the current person. Overwriting a source context when creating a fork. Auto-merging distinct context lineages. Projecting user context or authority onto the wrong actor. Making the runtime more complex than the work it is protecting.

## Self-check

Before: active context ready, onboarding in progress, or calibration explicitly declined? actor bound? receiver visible? relevant saved state loaded? request resolved? consequential contracts grounded? gate open? During: operation attributable to a revision? After: actual state observed? residual localized? invariant intact? settlement supported by evidence? rebase preserved untouched layers? next request will resolve against the correct revision?
