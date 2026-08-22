---
howdo_context: "2"
template: true
context_id: template
context_file: CONTEXT.template.md
skill: how-do
skill_version: "0.9.0"
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

The pedagogy is the **Map → Path → Check → Do → Look → Update** loop itself: a fixed shell, identical in every install. Its internals are personal and have no source but the person, which is why this file cannot be generated. What it holds are one person's settings for that shell: what they can attach new material to (Map), whether understanding arrives instance-first or principle-first (Path), what observable result convinces them they have it (Check/Look), and how a correction should land (Update).

Those settings are learned from their **preference for, and critique of, how information was presented — judged by whether it built understanding**, not by whether they enjoyed it.

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

Domains or subjects the person knows well enough to judge quickly whether an explanation actually built understanding. That judgement is the instrument, and it is only available where they are already expert. These are also what new material can be anchored to.

- pending

## Representation observations

What their preference and critique revealed about how information has to be presented for understanding to be built: instance-first or principle-first, what sequencing makes a thing stick, what has to be in place before the next step lands. Record behaviourally useful observations with applicability, evidence, confidence, and limits — never identities such as “visual learner.”

- pending

## Structures that landed

Concrete examples of explanation structures the person preferred, and what made them useful for understanding. The reason is worth more than the example.

- pending

## Structures that did not land

Concrete examples of explanation structures the person rejected or found costly, and why. One critique with a reason attached beats three structures that merely worked.

- pending

## Interaction observations

How this person wants to be corrected, how they show they have understood, and how they prefer to inspect, compare, branch, or deepen a HowDo.

- pending

## LongHow settlements

Durable lessons accepted after comparison across HowDo traces. Do not write raw session history here.

- none yet
