# PILOT-0001 — treatment definition

Status: **frozen before implementation.** This document is the contract the
adapter implements. It is not part of the How Do discipline and is not shipped
in the skill payload. See *Promotion boundary* at the end.

## Why a second context kind exists

How Do requires context before a substantive run. Its durable context is
explicitly person-derived: `CONTEXT.template.md` states that the loop's
internals "have no source but the person, which is why this file cannot be
generated," and the required evidence sections record how a particular person
builds understanding — calibration domains, representation observations,
structures that landed and did not.

A benchmark agent in a container has no person. Synthesizing a person context
for it would fabricate exactly the evidence `complete_onboarding()` exists to
require, and the check would pass: completion establishes that the sections
contain non-placeholder text, never that the text is true. A green context
certifying nothing is worse than no context.

So PILOT-0001 does not run HowDo with a fake person. It introduces a second
context **kind**.

## The two kinds

| | `person` | `environment` |
|---|---|---|
| source | elicitation, observed interaction | inspection, reconnaissance |
| records | how one person builds understanding | independently inspectable facts about the execution environment |
| settlement key | `onboarding` | `reconnaissance` |
| evidence | calibration domains; representation observations; structures that landed; structures that did not land | available ground; imposed ordering; verification mechanisms; mutation and authority boundaries |
| opt-outs | `deferred`, `declined` | none — there is nobody to ask |

The validators are disjoint. An environment context cannot satisfy the
requirements of a person context, and a person context cannot satisfy the
requirements of an environment context. Neither the metadata keys nor the
evidence sections overlap, so relabelling one as the other fails on both.

The two may eventually cross. Crossing is not in scope here.

## Kind, lifetime, and write authority are orthogonal

```text
ContextKind        person | environment
ContextLifetime    ephemeral | frozen | persistent
WriteAuthority     writable | readonly
```

Kept independent so that "environment" never silently implies "ephemeral."

### Admissible in PILOT-0001

```text
environment + ephemeral + writable      default treatment (H1)
environment + frozen    + readonly      declared treatment (H2, later)

everything else                          inadmissible
persistent                               prohibited
person                                   inadmissible in a benchmark trial
```

Person contexts are mechanically inadmissible inside a trial. That is the point:
it prevents a person context from being slipped into the organism by accident.

Persistent accumulating context is prohibited because later trials would inherit
information from earlier trials, and repeated-trial independence is the
assumption the whole 5-trial protocol rests on. It remains a legitimate research
object afterwards — it is LongHow with trials as the traces — but not here.

## Frozen means externally inspectable, not promised

`frozen` does not mean "settlement refuses." It means the immutability is a
property of the environment rather than a behaviour the agent is asked to
respect:

```text
FrozenContext {
    digest        sha256 of the frozen bytes
    source        path the freeze was taken from
    created_from  context_id of the source lineage
    byte_length
    readonly      true
}
```

The digest of the frozen context appears in every evidence receipt collected
under it. Freezing also drops the file to read-only permissions. The harness
should additionally deliver it through a read-only mount; the permission bit is
the in-band signal, the mount is the boundary. This follows the same direction
already taken with canonical skill authority: enforcement by environment, not by
instruction.

## Reconnaissance produces observations, not conclusions

Environment onboarding is a reconnaissance pass, structured on the loop:

```text
Map          what exists? what can be inspected?
Path         what ordering or dependencies does the environment impose?
Check/Look   what mechanisms independently establish success?
Update       what is mutable? what is canonical? who or what has write authority?
```

Reconnaissance records environmental ground:

> `pytest` is available; exit status plus the tests under `tests/` constitute
> verification.

It does not record task learning:

> The best way to solve this task is X.

The first is a fact about the environment that would be true whatever the task
was. The second is a partial solution, and admitting it into context would make
the treatment a solver rather than a discipline. This boundary is stated in the
procedure and in the template; it is not mechanically enforceable, and the
structural validator does not claim to enforce it.

### Reconnaissance budget

Reconnaissance is bounded by a declared cap, recorded in the receipt. An
unbounded recon pass would mean "HowDo" denotes a different treatment on a
cheap task than on an expensive one. The cap is part of the treatment
definition, not a runtime convenience.

## The contamination law

For one trial:

```text
container starts
      -> environment reconnaissance
      -> ephemeral environment context (bound to this trial id)
      -> HowDo
      -> task execution
      -> verification
      -> EvidenceReceipt
      -> container and context destroyed
```

For the next trial: new container, new reconnaissance, new context identity.
Nothing learned in trial N survives into trial N+1 except the append-only
research receipt, which lives outside the organism.

Ephemerality is asserted in-band, not assumed. An ephemeral context is bound to
a trial id at creation and cannot be read without asserting which trial is
reading it; a mismatch reports `expired` rather than returning content. A reused
volume or a recycled container therefore surfaces as a detectable state instead
of a silent contamination.

## Treatment arms

```text
H0   raw agent
H1   HowDo + per-trial reconnaissance          PILOT-0001 default
H2   HowDo + frozen environment context        later, separate hypothesis
```

H1 and H2 are not interchangeable.

- **H1** asks: can the discipline discover the environment and repay the
  reconnaissance cost inside the same trial?
- **H2** asks: given correct reusable environmental ground, does the discipline
  exploit it?

PILOT-0001 runs H0 against H1 only.

## Trial disposition

Declared before collection, because the alternative is discarding inconvenient
treatment trials after seeing them:

- **Reconnaissance fails or returns nothing usable** — the trial counts. Recon
  is part of the treatment, so its failure is treatment performance.
- **Reconnaissance exceeds its budget** — the trial counts, and the overrun is
  recorded.
- **Infrastructure failure** (container did not start, harness crashed, oracle
  flaked on a qualification-passing task) — the trial is excluded and re-run,
  and the exclusion is recorded with its reason.

## What PILOT-0001 cannot establish

Environment reconnaissance is part of the HowDo treatment. PILOT-0001 can
therefore establish whether the complete treatment produces measurable lift, but
cannot attribute that lift among HowDo's components. In particular, any observed
effect may arise partly or primarily from allocating early trajectory budget to
environment reconnaissance rather than from the other stages of the loop.

Component attribution is deferred until a treatment signal exists. The first
experiment is existential — signal: yes, no, or indeterminate — not mechanistic.

A second limit follows from the kind split: the pilot measures the loop plus
environment context. The person-derived half of HowDo is not present in any arm
and is not being tested. A null result at the gate falsifies this treatment, not
How Do as a whole, and the stopping rule must say so.

## What this contract does not establish

- That reconnaissance findings are true. The validator proves shape.
- That the recon boundary held. Observations-versus-conclusions is a
  documented rule and a review criterion, not a check.
- That the frozen mount was actually read-only in the harness. The digest in
  the receipt detects a change after the fact; it does not prevent one.

## Promotion boundary

This adapter lives on the experiment branch as the minimum required to make
PILOT-0001 honest. It is not How Do 0.9. Versions are not bumped, the shipped
discipline documents are unchanged, and the experiment directory is not part of
the install payload.

If the pilot dies at the gate, this does not get promoted because its
implementation is tidy. The branch may exist before the evidence earns the core.
