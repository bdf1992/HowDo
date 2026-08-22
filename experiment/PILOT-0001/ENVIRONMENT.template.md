---
howdo_context: "2"
context_kind: environment
template: true
context_id: template
context_file: ENVIRONMENT.template.md
skill: how-do
skill_version: "0.8.0"
reconnaissance: required
parent_context_id: none
lifetime: ephemeral
write_authority: writable
trial_id: none
---

<!-- template-only:start -->
# Shipped template — not a context

This block exists only in the shipped template. `open_trial_context()` removes
it when it instantiates a trial store, so nothing below this line describes a
template: it *is* the instance a reconnaissance pass settles.

Do not settle this file. It carries `template: true`, has no lineage to settle
into, and `complete_reconnaissance()` refuses it outright.
<!-- template-only:end -->

# How Do Environment Context

This is the environment context for one execution environment. It is **not** a
person context and cannot satisfy a person context's validator.

A person context records how one person builds understanding; it is elicited,
because a pedagogy is not observable. An environment context records
independently inspectable facts about where the work is happening; it is
obtained by looking, because an environment's affordances are observable.

## Scope

Reconnaissance records **environmental ground**: what would be true of this
environment whatever the task was. It does not record task learning, partial
solutions, or a plan for the current request.

Admissible: `pytest` is available and exit status plus the tests under `tests/`
constitute verification.

Not admissible: the best way to solve this task is to patch the parser first.

The structural validator cannot tell these apart. It proves that each section
holds non-placeholder material. Keeping the boundary is the reconnaissance
procedure's job, and a review criterion — not a check.

## Lifetime

`lifetime` and `write_authority` are independent of kind.

- `ephemeral` — bound to one trial by `trial_id`, destroyed with it. Cannot be
  read without asserting the reading trial's id.
- `frozen` — byte-identical and read-only across trials; its digest belongs in
  every evidence receipt collected under it.
- `persistent` — later research only. Prohibited during a pilot, because later
  trials would inherit information from earlier ones.

## Available ground

What exists here, and what can be inspected. Tools, runtimes, languages,
services, filesystem layout, documentation actually present. Record what was
observed and how, not what is assumed to be typical.

- pending

## Imposed ordering

Ordering and dependencies the environment imposes: what must be installed,
built, started, or generated before something else can run. Constraints of the
environment, not a plan for the task.

- pending

## Verification mechanisms

What independently establishes that something worked here: test runners, exit
statuses, linters, type checkers, health endpoints, verifier entry points. Name
the mechanism and what its success actually signals. This is the section the
loop's Look stage reads, and it is the one most worth getting right.

- pending

## Mutation and authority boundaries

What is mutable, what is canonical, and who or what holds write authority.
Read-only mounts, generated files that must not be hand-edited, protected paths,
credentials that are absent by design.

- pending

## Reconnaissance notes

Observations that do not belong in the four evidence sections: cost of the pass,
what could not be determined, what was ambiguous. Uncertainty recorded here is
worth more than a confident guess promoted into evidence.

- none yet
