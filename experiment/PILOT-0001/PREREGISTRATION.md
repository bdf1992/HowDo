# PILOT-0001 — preregistration

Status: **unfrozen.** Four values are still undeclared — the variance ceiling
for task selection, δ\*, the reconnaissance budget, and the harm-rate ceiling.
Each is marked below with a proposal and the reasoning behind it, in a bracketed
`DECLARE` block. `evidence/preregistration.py` refuses to compute a digest while
any such block remains, so no confirmatory trial can cite this document until a
person has decided. The two Stage B fields and the freeze records are marked the
same way and are settled later, in the order described next.

This is the artifact the gate reads. Its digest goes into every confirmatory
receipt as `preregistration_digest`, which is what makes "the commitments in
force when this trial ran" a recoverable fact rather than a memory.

## Two-stage freeze

The study cannot be fully specified before M0.0, and the parts that can be
must not wait for it — deciding the analysis after seeing the variance is the
failure this document exists to prevent.

- **Stage A — frozen before M0.0 runs.** Question, hypotheses, endpoints,
  analysis method, δ\*, reconnaissance budget, exclusion rules, stopping rule.
  Nothing here may be changed by anything M0.0 reveals.
- **Stage B — filled from M0.0's output, frozen before M0.1 collects a single
  confirmatory trial.** The committed task set and the trials-per-task-per-arm
  count. Both are consequences of measured variance, not judgements about it.

Each stage records the date it was frozen and the digest at that moment. A
Stage B fill changes the digest; receipts collected before and after are
distinguishable, and no confirmatory trial predates the Stage B freeze.

---

## Question

Does running the How Do loop with per-trial environment reconnaissance change
the rate at which a fixed 12B organism completes qualified Harbor tasks under
deterministic verification, compared with the same organism given the same task
and budget and no discipline?

## Hypotheses

- **H0 (control).** Raw agent. No skill document, no context, no reconnaissance.
- **H1 (treatment).** How Do plus per-trial environment reconnaissance, as
  frozen in `TREATMENT.md`.

H2 (frozen environment context) is a separate hypothesis and does not run here.

Null: the per-task pass rate is the same in both arms. This pilot is
**existential, not mechanistic** — it asks whether a signal exists, not which
part of the treatment produced it.

## Fixed by reference

Not restated here, because a restatement can drift from the thing it restates:

| What | Where | Bound by |
|---|---|---|
| Treatment definition | `TREATMENT.md` | commit SHA, recorded at Stage A freeze |
| Organism | `../M-1/ORGANISM.lock.json` | `organism_fingerprint` |
| Task authority | `../TASK-QUALIFICATION.md` | `task_qualification_digest` per task |
| Evidence contract | `../evidence/RECEIPT.md` | `receipt_version` |

## Task set — Stage B

**Selection rule, frozen at Stage A.** A task enters the committed set if and
only if all of the following hold, evaluated on M0.0's screening runs:

1. It is `qualified` under `TASK-QUALIFICATION.md` — deterministic verifier,
   oracle 5/5, no-op 3/3 failed, flake rate under cap. `research_only` tasks are
   excluded from the confirmatory set entirely.
2. Its measured H0 pass rate in M0.0 is strictly between 0 and 1. A task at the
   floor or the ceiling in the control arm carries no information about a
   difference and only inflates the denominator.
3. Its M0.0 within-task variance does not exceed `<<DECLARE: variance ceiling —
   proposed: exclude any task whose H0 pass rate SD across repeats exceeds 0.35,
   i.e. a task that is effectively a coin flip against itself. Reasoning: such a
   task contributes variance without contributing signal, and at the sample
   sizes available it can single-handedly widen the interval past δ\*.>>`

**Screening bias, declared.** Rule 2 selects on the control arm's performance.
This is deliberate — a floor-and-ceiling screen has to use *some* arm — and it
biases toward tasks where H0 is mid-range, which is where a treatment effect is
easiest to see. The pilot therefore estimates the effect **on tasks a raw agent
finds neither trivial nor impossible**, not on Harbor Index as a whole. Any
figure reported must carry that qualifier.

**Fresh trials only.** M0.0's runs screened the task set. They are not reused as
the control arm. Reusing them would make the control the very sample that
selected the tasks, which manufactures lift.

**Committed task ids:** `<<STAGE-B: filled from M0.0 screening, before any
confirmatory trial>>`

## Trial allocation — Stage B

Trials per task per arm: `<<STAGE-B: computed from M0.0 variance and δ\*>>`

Equal allocation across arms. Total confirmatory trial count is fixed at the
Stage B freeze and is not extended on the basis of an interim result.

## Randomization and interleaving

- Arm order within each task is randomized, seeded, and the seed is recorded.
- Trials are **interleaved** across arms rather than run in blocks. Running all
  of H0 and then all of H1 confounds the arm with anything that drifted in
  between: a driver update, thermal state, a Harbor version bump.
- `run_sequence_index` in each receipt records the order trials actually ran in.
  `evidence/receipt.py` refuses an out-of-order append, so the interleaving is
  checkable afterwards rather than asserted.
- No interim analysis. Looking at the difference before collection completes and
  stopping when it is favourable is the most common way a null becomes a
  positive.

## Primary endpoint

**Mean per-task difference in pass rate, H1 − H0**, across the committed task
set, with the task as the unit of analysis.

Task-level rather than trial-level because trials within a task are not
independent: a task the organism cannot do fails in every trial, and pooling
trials would count that as many independent pieces of evidence.

## Secondary endpoints

Declared now so they cannot be chosen later to rescue a null.

1. **Task-level win/loss/tie count.** How many tasks improved, how many
   regressed. A mean lift built from one task improving hugely and six
   regressing slightly is a different result from a broad small gain.
2. **Harm rate.** Tasks whose pass rate is lower under H1. Load-bearing for the
   stopping rule.
3. **Reconnaissance outcome distribution.** Rates of `complete`, `over_budget`,
   and `failed`. Recon failure is treatment failure and counts in the primary
   endpoint; this endpoint says how often the treatment failed that way.
4. **Cost.** Wall clock and total tokens per trial per arm. A lift bought with
   three times the compute is a different finding from one that is free.

## Explicitly exploratory

Reported separately and labelled exploratory in any writeup. Adding these to
the confirmatory set after the fact is the failure this section exists to
prevent.

- Any per-domain, per-modality, or per-horizon breakdown.
- **The compute confound.** H1 spends tokens on reconnaissance that H0 does not,
  so an observed lift may be budget reallocation rather than discipline.
  `TREATMENT.md` already declares that PILOT-0001 cannot attribute the effect
  among components. A token-matched or covariate-adjusted comparison may be run
  afterwards; it is not the primary endpoint and cannot convert a null into a
  positive.
- Anything derived from trajectories rather than verifier output.

## Practical effect threshold

δ\* = `<<DECLARE: proposed 0.10 absolute in mean per-task pass rate. Reasoning:
reconnaissance costs real tokens and wall clock on every trial, so an effect
smaller than roughly one task in ten moving from fail to pass does not repay the
treatment at the scale the programme would need to deploy it; and below that
value the interval at any feasible n will not exclude zero, so a smaller δ\*
buys an INCONCLUSIVE rather than a finding.>>`

δ\* is a statement about what would be worth acting on. It is fixed before any
variance is known, precisely so that it cannot be lowered to meet the data.

## Power gate

Before M0.1 collects a confirmatory trial, compute the minimum detectable
effect from M0.0's measured variance at the Stage B trial count.

**If MDE > δ\*, PILOT-0001 does not run.** It would return INCONCLUSIVE by
construction, and spending the trials to discover that is worse than not
spending them. The response is to fix the measurement — more trials per task,
tighter tasks, a reduced question — not to lower δ\*.

## Reconnaissance budget

`<<DECLARE: proposed 8,000 prompt tokens and 12 tool calls per trial, whichever
binds first. Reasoning: enough to list a repository, read a build or test
configuration, and run the test command once — the observations
reconnaissance.md asks for — and not enough for the recon pass to become a
solving pass by itself. A cap set at the trial's whole budget would make H1 mean
"more attempts", and a cap too small would make recon failure the modal outcome
and the pilot a measurement of the cap.>>`

Recorded in every receipt as `recon_budget`, with `recon_used` beside it. A cap
changed mid-study is a treatment change and invalidates the arm.

## Analysis

- **Statistic:** mean across tasks of (H1 pass rate − H0 pass rate).
- **Test:** permutation test on arm labels, permuted **within task**, 10,000
  permutations, seeded and recorded. Assumption-light and matched to the
  design; under the null, arm labels within a task are exchangeable.
- **Interval:** 95% confidence interval by bootstrap over tasks (not over
  trials), 10,000 resamples, seeded and recorded.
- **Multiplicity:** one primary endpoint, one test. Secondary endpoints are
  reported with intervals and are not used to declare a result.
- **Analysis code is written and committed before Stage B is frozen**, and run
  once against synthetic data with a known effect to show it recovers it. An
  analysis written after the data exists is a choice made with the answer
  visible.

## Exclusions and retries

Per `TREATMENT.md`, and repeated here because a disposition rule discovered
mid-study is not a rule:

| Situation | Disposition |
|---|---|
| Reconnaissance fails or returns nothing usable | **Counts.** Recon is part of the treatment; its failure is treatment performance |
| Reconnaissance exceeds budget | **Counts**, overrun recorded |
| Container did not start, harness crashed, runner lost | **Excluded and re-run.** `failure_class` recorded, exclusion appears in the log |
| Oracle-qualified task's verifier errors | **Excluded and re-run**, recorded |
| Model produced no output within the harness timeout | **Counts as a failure.** This is the organism's behaviour, not the infrastructure's |

Every exclusion is written to the receipt log with its class. An excluded trial
that leaves no trace is a deletion.

**Exclusion ceiling.** If more than 10% of trials in either arm are excluded,
the run is void and re-run after the cause is fixed. Above that rate the
remaining sample is a selected one.

## Outcomes

Declared before collection. Exactly one applies.

**GO.** The 95% interval on the primary endpoint excludes zero, its lower bound
is at least δ\*, and the harm rate does not exceed `<<DECLARE: proposed 20% of
committed tasks regressing. Reasoning: a treatment that lifts the mean while
breaking one task in four is not deployable, and discovering that only in M2
would waste the branch milestone.>>` → the effect is real and large enough to
justify the skill-graph infrastructure. Proceed to M1.

**STOP.** The interval includes zero and its upper bound is below δ\*, **or**
the harm rate exceeds the ceiling. → *Stop the skill-graph infrastructure work
and return to How Do itself.* A clean null is an accepted result and is
published as one. This is the branch that the whole programme is arranged to
make survivable: the roadmap, the packaging boundary, and the promotion rule all
exist so that STOP costs a directory rather than a release.

**INCONCLUSIVE.** The interval spans δ\* — the effect may be large enough or may
be nothing, and this run cannot tell. → Not a soft GO. Fix the measurement and
re-run, or narrow the question. Infrastructure work does not proceed on an
INCONCLUSIVE.

## What a null falsifies, and what it does not

A null falsifies **this treatment**: the How Do loop plus per-trial environment
reconnaissance, on a 12B organism, on tasks a raw agent finds neither trivial
nor impossible, under deterministic verification.

It does not falsify How Do. The person-derived half of the discipline — the
durable context, the pedagogy, the calibration that `CONTEXT.template.md` says
cannot be generated — is **absent from every arm of this study**. It is not
tested here and cannot be, because a benchmark agent has no person. Any
reporting of a null that omits this qualifier is misreporting it.

Nor does a null establish that the discipline is useless to a human user. It
establishes that this treatment did not move this measure on this organism.

## Deviations register

Any departure from this document after the Stage A freeze is appended here with
its date, its reason, and the digest of the version it departs from. A deviation
is not a defect; an unrecorded deviation is.

_None recorded._

## Freeze record

| Stage | Frozen on | Digest |
|---|---|---|
| A | `<<STAGE-A: not yet frozen>>` | `<<STAGE-A: not yet frozen>>` |
| B | `<<STAGE-B: not yet frozen>>` | `<<STAGE-B: not yet frozen>>` |
