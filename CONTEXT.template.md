---
howdo_context: "2"
template: true
context_id: template
context_file: CONTEXT.template.md
skill: how-do
skill_version: "0.8.0"
onboarding: required
parent_context_id: none
---

<!-- template-only:start -->
# Shipped template — not a context

This block exists only in the shipped template. `ensure_context()` removes it
when it instantiates the durable store, so nothing below this line describes a
template: it *is* the instance a person settles.

Do not settle this file. It carries `template: true`, has no lineage to settle
into, is skipped by the fork check, and is replaced by the next payload update.
`complete_onboarding()`, `decline_onboarding()`, and `fork_context()` all refuse
it outright.
<!-- template-only:end -->

# How Do Context

This is the durable, forkable context for **how this How Do installation should be perceived, built, rendered, and interacted with**.

What it holds is a **pedagogy**: how understanding gets built for this person, not which visual style they enjoy. Four things matter most — what they already know well enough to build on, whether understanding arrives instance-first or principle-first, what convinces them they have got it, and how correction should land. Rendering follows from those.

It is not the trace of one task and it is not a personality dossier. A HowDo produces a trace. LongHow may later propose durable lessons from repeated traces. Only settled lessons belong here.

This file is per-person and per-install. Keep it out of shared version control by default, because it records how one person builds understanding.

## Onboarding state

**Required before the first substantive HowDo unless explicitly declined or deferred.** Establish the pedagogy as described in `references/onboarding.md` — how you do that is yours to choose — then settle this file with what you actually observed, positive and negative. If the user declines, persist `onboarding: declined`; future sessions do not ask again and must not treat this file as learned context.

`onboarding: complete` is only structurally accepted when each required evidence section contains at least one non-placeholder bullet. This check proves shape, not truth or quality.

## Agency projection

This file primarily informs **teaching, rendering, and interaction**. It does not grant facts, capability, or authority to the actor named in a request.

`How do I / you / we / they` is an **agency modifier** on the same HowDo:

- **I** — user context may inform both rendering and relevant known user capabilities/domain familiarity.
- **you** — use assistant/tool capability context; this file still informs how the answer is rendered.
- **we** — compose user + assistant contexts and make responsibility/authority boundaries visible.
- **they / named actor** — use evidence about that external actor; do not project user capabilities or private context onto them.

No extra onboarding questionnaire is required for this modifier. Learn its practical consequences from ordinary HowDo traces.

## Calibration domains

What this person already knows well enough to build on. These are your source of analogies and worked examples — anchors for new material, not a domain where they grade your prose.

- pending

## Representation observations

How understanding actually gets built for this person: instance-first or principle-first, what sequencing makes a thing stick, what has to be in place before the next step lands. Record behaviourally useful observations with applicability, evidence, confidence, and limits — never identities such as “visual learner.”

- pending

## Structures that landed

Concrete moments where something clicked, and the reason it did. The reason is worth more than the example.

- pending

## Structures that did not land

Concrete moments where an explanation cost more than it delivered, and why. One rejected structure with a reason beats three that merely worked.

- pending

## Interaction observations

How this person wants to be corrected, how they show they have understood, and how they prefer to inspect, compare, branch, or deepen a HowDo.

- pending

## LongHow settlements

Durable lessons accepted after comparison across HowDo traces. Do not write raw session history here.

- none yet
