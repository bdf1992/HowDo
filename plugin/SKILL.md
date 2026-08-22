---
name: how-do
description: "Understanding-before-acting discipline — bind the actor, map the problem, state checks at consequential boundaries, act only when they hold, then observe and correct only what the result disproved. Requested, not ambient: use when the user invokes /how-do, names How Do or its loop (Map → Path → Check → Do → Look → Update), or asks in their own words to work this way — to slow down, ground a plan before acting, or inspect the reasoning behind a result. An ordinary how-to question, a request for help, or simply continuing prior work is not by itself a request for How Do; answer those directly."
license: MIT
metadata:
  author: bdo
  version: "0.9.0"
  category: discipline
---

# How Do

Two words. **How** establishes enough understanding to act; **do** executes against that understanding.

The working understanding is a **paradigm**: inspectable state used to resolve the current request. Execution is an **operation** against a resolved point in that state. Observation produces a **residual**: the measured difference between what was expected and what occurred.

A request resolves against the paradigm. It does **not** automatically mutate it. Only an admissible residual may earn a write-back, and only to the layer the residual touched. An accepted settlement **rebases** the paradigm: preserve what still holds, replace the smallest disproved part, and issue the next revision.

Baseline, not template: it should move you, not contain you.

## When this runs

How Do is **requested, not ambient**. It applies when someone asks for it — by name, by its loop, or by asking to slow down and ground the work — and the ask is generic enough that any domain qualifies. It is not the default posture for every how-to question, and loading it uninvited taxes work that did not ask for the ceremony.

Two consequences. Handles below are moves *inside* an invoked HowDo, never triggers for one. And onboarding gates the first substantive HowDo, not the person's first sentence: by the time it runs, they have already opted into the discipline.

One thing is said before anyone asks, and the line it stands on is exact. On a plugin install, a `SessionStart` hook tells the **person** that a short setup conversation is pending and that they may decline it or postpone it. That is a notice *about* the skill, not the skill running: it reaches the person and puts nothing in the agent's context, so no pedagogy is read, no loop is entered, and the request that follows resolves exactly as it would have with the hook absent. The distinction is mechanical, not a matter of intent — a notice reaches the person only; anything that reaches the agent's context is the discipline loading, and that still requires an invitation. The hook is also silent once the question has an answer: settled, declined, or postponed, it says nothing.

## The small loop

For a person using AI, the whole discipline should fit in one look:

**Map → Path → Check → Do → Look → Update**

- **Map** — what are we actually working with?
- **Path** — how should the work proceed?
- **Check** — what must be true before, and what observable result should be true after? Check writes the test.
- **Do** — execute only when the consequential checks are grounded.
- **Look** — take in the actual result and test it against what you predicted at Check. The difference is the residual. Never the model's claim of success: you cannot test a thing by asking it whether it worked.
- **Update** — rebase the understanding by changing the smallest part the evidence disproved.

Guide with this loop. The deeper vocabulary exists for inspection, runtime support, and repeated work; it is in `references/vocabulary.md`.

## Durable context and first-run onboarding

Every installation ships **`CONTEXT.template.md`** and instantiates a durable **`CONTEXT.md`** in a store outside the payload — the payload is replaced by every update, so a context settled inside it is discarded with no error raised. The template is a replaceable artifact; the instance is a lineage. Durable context is reusable orientation for how this installation should be perceived, built, rendered, and interacted with. What it holds is a **pedagogy**. The loop is a fixed shell — every install runs the same **Map → Path → Check → Do → Look → Update** — and its internals are personal: one person's settings for that shell, which have no source but the person. A pedagogy is therefore neither invented per reader nor guessable from configuration. It is how understanding gets built for this person, not which visual style they prefer. It is **not** one task's context, a session log, or a personality dossier.

Resolve the store in this order: a path selected for this session; `$HOWDO_CONTEXT`; `$CLAUDE_PLUGIN_DATA/CONTEXT.md` when a plugin host declares one, because that directory is guaranteed to survive updates; else the platform default — `%APPDATA%\howdo\CONTEXT.md` on Windows, `~/.howdo/CONTEXT.md` on macOS and Linux. The basename stays `CONTEXT.md`; a different basename is read as a fork.

Then route on the state of that file:

| state | do |
|---|---|
| no file | instantiate from the template, then onboard |
| `onboarding: required`, or evidence sections still placeholders | establish the pedagogy **before the first substantive HowDo** |
| `onboarding: deferred` | work now without learned context; the offer stays open for a later session |
| `onboarding: declined` | do not ask again; do not use as learned context |
| basename differs from `context_file` | a new fork — onboard that lineage, preserve the source |
| required lineage keys missing | invalid, not silently ready |
| `onboarding: complete` | load it and work |

Four guarantees hold whether or not the detail is loaded. Onboarding gates the first substantive HowDo and is never bypassed silently — only an explicit user decline or deferral skips it. A decline is durable: persist `onboarding: declined` and do not re-ask on later sessions. A deferral is not a decline: persist `onboarding: deferred`, work without learned context, and the offer may be made again later — at most once per session, never as nagging. And `onboarding: complete` is structural completeness only — it checks that evidence is present, and does not prove that the evidence is truthful or good.

**Read `references/onboarding.md` whenever the state is anything but complete.** It carries what the pedagogy must establish, the fork and scope rules, the runtime helpers, and the fallback for a hand-copied install. A ready context needs none of it.

How you establish it is yours to choose — learn a dimension by doing it rather than asking, state an assumption and invite correction, or skip what the conversation has already shown you. What you are establishing are the per-person settings of this same loop: what they can attach new material to (**Map**), whether understanding arrives instance-first or principle-first (**Path**), what observable result convinces them they have it (**Check/Look**), and how a correction should land (**Update**). One constraint is not free: calibrate in a domain the person knows well, because the observation becomes an exemplar reused on topics they are *not* expert in, and a novice cannot tell "well built" from "I finally understood it". Keep it a conversation between two people working out how to work together; it is never an intake form, and the person should ideally not be able to tell an onboarding is happening. The route is free, the receipt is not.

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

The local terms — paradigm, map, path, precondition, invariant, gate, operation, residual, settlement, rebase, trace, LongHow, handle — are mapped to established practice in **`references/vocabulary.md`**. Read it in inspect mode or when auditing; guide mode does not need it.

## Procedure

0. **Resolve the store, then load or calibrate durable context.** Durable context lives outside the skill payload: the payload is replaced by every install or update, so a context settled inside it is discarded with no error raised. Resolve the store and route on its state as in **Durable context and first-run onboarding**, instantiate it from the shipped template when absent, and never settle the template copy in place. If the context is fresh, forked, or unresolved, read `references/onboarding.md` and establish the pedagogy before substantive work unless the user declines or defers. Persist a decline as `onboarding: declined` and never ask again; persist a deferral as `onboarding: deferred` and leave the offer open. Both proceed without learned durable context.
1. **Bind the actor; establish the receiver — visibly.** Resolve `I / you / we / they / named actor` first. Use that actor lens to constrain capability, authority, and evidence. Separately project a small local rendering contract from any ready durable context plus the current request. State the useful read in one line and let the person correct it.
2. **Resolve the request against a paradigm.** Load only saved domain-how/context admissible for the bound actor. Otherwise establish the smallest useful map, then a path through it. Do not require a grand ontology. For every step that mutates state or crosses a boundary, state a precondition and an observable postcondition. Observation-only steps may stay lighter. Name invariants that must survive the operation; minimum invariant: the active paradigm stays inspectable in one look.
3. **Gate.** Admit the operation only if the requested point can be located and the consequential contracts are grounded in real state. If not, fizzle: identify the missing distinction, evidence, permission, dependency, or contract. A fizzle is not a failed operation because the crossing never became admissible.
4. **Do.** Execute the admitted operation. Keep the operation attributable to the resolved paradigm revision and the checks that opened the gate.
5. **Look.** Check wrote the test; Look runs it. Take in the resulting state independently of the model's claim of success whenever practical, and test it against the observable postconditions and invariants. What the test yields — observed minus expected — is the residual, and it is the input to step 6. A step that only looks at what was reported has not run the test.
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

- **`CONTEXT.md` / context fork** — per-person and per-install, resolved as above; keep it out of shared version control by default (gitignore or a user-scoped path), because it records how one person takes explanations. Durable settled orientation for how this installation should present and interact: calibration domains, representation observations, liked/disliked structures, interaction observations, and LongHow settlements. It has its own context lineage and onboarding state.
- **Rendering contract** — local projection for the current request. It may use the durable context but can differ whenever the task demands it. Do not force a learned preference where it harms the work.
- **Domain-how** — one file per recurring concern: map, path, consequential contracts, invariants, one worked example, and revision. Issued rather than described: the runtime mints it from a run that actually happened, keeps it `untested` until an observed run grounds it, and indexes what exists by concern, workflow, and required capability.
- **HowDo trace / operation record** — the bound actor, resolved revision, rendering used, gate result, observed evidence, residual, and settlement. This is history and evidence, not automatically part of durable context.
- **LongHow** — compares multiple HowDo traces (or unusually strong explicit feedback) and proposes the smallest reusable context lesson. The person settles persistent edits.
- **When to save domain-how.** On explicit ask, or after a how survives at least one do/look cycle. Never promote an untested exemplar simply because it sounded plausible — issuing records `untested`, only a residual that matched promotes it, and any revision drops the grounding its predecessor earned.
- **When to update durable context.** Establishing the pedagogy may settle direct user feedback. Afterward, do not rewrite `CONTEXT.md` from every session. Route presentation residuals into traces; LongHow promotes only recurring or explicitly ratified lessons, with provenance and limits.
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
- **The vocabulary is working equipment, not output.** These terms organise your reasoning; they are not what the person reads back. Do not say *pedagogy*, *paradigm*, *residual*, *exemplar*, *settlement*, *payload*, or *store* at them; do not surface state names (`onboarding: required`, `onboarding_required`), frontmatter keys, or store paths as guidance. Two exceptions, both narrow: **inspect mode**, which exists to show the layers, and someone **working on How Do itself**, for whom the machinery is the subject. Everywhere else the machinery shows through the *shape* of an answer, never its wording.

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

### Request contract

The five operations say when a crossing is admissible. They do not say what the
request reads, what shape the result has to have, or what a host must be able to
do before the operation is loadable there at all. Left implied, those three go
unchecked and do not travel.

A **request contract** states them as data: the path, the shape it `accepts`
(declared inputs, rather than arguments smuggled through intent prose or an
executor closure), the shape it `expects` of the observable result, its checks as
serializable clauses rather than closures, and the capabilities it `requires`.
Being data is the point — one contract loads into any host and states the same
obligations there, and binding it to a host answers *can this run here* before
anything resolves instead of part-way through an operation.

Two consequences are worth naming. A consequential contract must carry its own
precondition and its own result shape, because a gate the host happened to
supply is not part of what shipped. And an observation that does not match the
declared shape routes to `contract`, not `postcondition`: a result that cannot be
compared is a different fault from one that came out wrong, and filing it as the
latter claims a test ran that did not.

Optional, like the rest of the runtime — `runtime/howdo/contract.py`, with
`examples/portable_contract.py` offering one contract to three hosts.

### Issued artifacts

The loop produces understanding, and until a run leaves something behind, all of
it is spent at the end of the session. Durable `CONTEXT.md` is a pedagogy and is
barred from carrying domain facts, so a person's domain work had nowhere to land.

A **domain-how** is that landing place, and the runtime issues it from a
completed HowDo rather than from a plan: the run supplies the worked example, the
contract supplies the path, shapes, and rules. Three rules keep an issuer from
becoming a way to manufacture false ground. It is `untested` until a residual
that *matched* grounds it. Any content revision drops the grounding its
predecessor earned, because an observation of the old content says nothing about
the new. And the index is rebuilt from the artifacts it describes, never trusted
as a second authority — so a lost index is a rebuild, not a loss.

One thing the kernel cannot do for a stored artifact: `admit` fizzles a stale
resolution, but that protection ends at the process boundary, which is exactly
where persistence begins. A grounded domain-how therefore records the paradigm
revision it was observed against, and drift is something you can ask about
rather than something that silently stops being true.

An issued artifact can then be **emitted** into a form a host loads directly:
an Agent Skill (`SKILL.md` bundle) or a Claude Code dynamic workflow, where the
loop becomes the script's structure — the gate runs before anything acts, the
path runs as ordered phases, and a final phase observes the world rather than
reading back what the acting agents reported. Emission is a projection, so
re-emit rather than editing what came out; the artifact is the source.

Emission has two frontmatter targets, because what a host accepts and what the
portable specification accepts are not the same set — and on the portable path an
unrecognised field fails packaging outright rather than being ignored. Where the
target allows it, a consequential artifact is marked non-auto-invocable, which is
this discipline's own posture expressed in a host's own vocabulary; where it does
not, the body says so and nothing enforces it.

An untested artifact is not emitted without an explicit override, and the
override stamps what it produces. A `SKILL.md` on disk pre-loads every later
session on that concern, which is the point at which an unconfirmed exemplar
stops costing one answer and starts costing all of them.

`runtime/howdo/domain.py` and `runtime/howdo/emit.py`;
`examples/issue_domain_how.py` runs the whole arc.

## Handles

A handle is admissible if it names a move over the paradigm and its residual is measurable. The seed set is illustrative, not fixed. These are moves within a HowDo already underway; a bare "help me" does not summon the discipline.

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
- **Fresh install with no learner evidence.** Establish the pedagogy before substantive work unless the user declines or defers; persist either so the ask is not repeated blindly. Neither is ready or learned.
- **Onboarding starting to feel like a form.** It has gone wrong. Drop the remaining questions, take what the work itself shows you, and settle a smaller receipt.
- **“Not now” rather than “no”.** That is a deferral, not a decline. Persist `onboarding: deferred`, do the work they actually asked for, and leave the offer open for a later session. Never record a postponement as a refusal — it silently costs the calibration.
- **Copied context with a new basename.** Treat it as a fork and onboard the new lineage; preserve the source.
- **Durable preference conflicts with current task.** The current task wins. Record the mismatch as evidence; do not force the old rendering.
- **One strong preference signal.** Adapt immediately for the current HowDo, but preserve it as a trace observation until onboarding or LongHow settlement justifies durable context.
- **"How do you" asks about assistant capability.** Use actual available capability/tool context; never upgrade capability because the receiver context says the user prefers a certain path.
- **"How do we" crosses authority.** Partition user-owned and assistant-owned steps before consequential action; shared intent is not shared authority.
- **"How do they" names an external actor.** User context may shape rendering but cannot serve as evidence about the external actor.

## Refuses

Acting on a path with no navigable map. Calling a consequential path understood without observable contracts. Treating model output as independent evidence of its own success. Mutating the paradigm merely because a request was made. Rewriting the whole paradigm when the residual named one layer. Establishing the receiver silently. Treating an unresolved, deferred, or declined context as learned context; silently bypassing onboarding without an explicit user decline or deferral; repeatedly re-asking after a persisted decline; or recording a “not now” as a refusal. Declaring a person a fixed learning-style type from presentation feedback. Promoting every trace directly into durable context. Settling durable context inside the replaceable skill payload without an explicit `scope: shared` opt-in, or letting an install overwrite a settled store. Treating a shared context as evidence about the current person. Loading the discipline uninvited — including any hook, monitor, or default that puts skill content into the agent's context before it is asked for; a notice to the person is not that, and is the only thing spoken unprompted. Overwriting a source context when creating a fork. Auto-merging distinct context lineages. Projecting user context or authority onto the wrong actor. Making the runtime more complex than the work it is protecting.

## Self-check

Before: active context ready, onboarding in progress, or calibration explicitly deferred or declined? actor bound? receiver visible? relevant saved state loaded? request resolved? consequential contracts grounded? gate open? During: operation attributable to a revision? After: actual state observed? residual localized? invariant intact? settlement supported by evidence? rebase preserved untouched layers? next request will resolve against the correct revision?
