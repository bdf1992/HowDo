# Environment reconnaissance

The procedure that settles an environment context. Read this when a context is
`reconnaissance_required`; a settled one needs none of it.

Person onboarding is a conversation because a pedagogy is not observable. This
is not a conversation with nobody — it is a pass of looking, because an
environment's affordances *are* observable. Every question below is answered by
inspection, and an answer that had to be assumed is not an answer.

## What must end up written

The route is free; the receipt is not. Each of the four evidence sections must
hold at least one real observation before the context settles.

| section | loop stage | the question |
|---|---|---|
| Available ground | Map | what exists, and what can be inspected? |
| Imposed ordering | Path | what ordering or dependencies does the environment impose? |
| Verification mechanisms | Check/Look | what independently establishes success? |
| Mutation and authority boundaries | Update | what is mutable, what is canonical, who holds write authority? |

Verification mechanisms is the load-bearing one. The loop's Look stage tests a
result against what Check predicted, and it must never take the actor's own
claim of success as the test. An environment context whose verification section
is vague makes Look unfalsifiable in exactly the way the discipline exists to
prevent.

## Observations, not conclusions

Record what is true of this environment whatever the task was.

> `pytest` is available; exit status plus the tests under `tests/` constitute
> verification.

Do not record task learning or a partial solution.

> The best way to solve this task is to patch the parser first.

The line is the same one the person context draws between observations and
identities. "Needed the failing case before the rule would stick" is usable
later; "visual learner" is not. Here: "generated files under `build/` are
rewritten by `make`" is usable; "edit `src/parser.py`" is the task.

Two reasons this matters beyond tidiness. A context carrying a partial solution
makes the treatment a solver, so any measured lift stops being a fact about the
discipline. And under a frozen context the conclusion would be reused across
trials it was never derived from.

Nothing checks this. The validator proves that the sections are populated, and
says so. Keeping the boundary is yours.

## Cost

Reconnaissance runs inside the trial and spends the trial's budget. It is
bounded by a declared cap, and the cap is part of the treatment definition — an
unbounded pass would make the treatment mean something different on every task.

Stop at the cap and settle what was observed. A partial context with an honest
gap recorded under *Reconnaissance notes* is admissible; a padded one is not.
"Could not determine whether the network is reachable" is a finding.

## Settling

`complete_reconnaissance()` writes the four sections and stamps
`reconnaissance: complete` with a fresh `context_id`. As with person onboarding,
completion is **structural**: it establishes that each section holds
non-placeholder material, never that the material is true or good.

An ephemeral context is bound to its trial at creation and dies with it. Nothing
observed here survives into another trial.
