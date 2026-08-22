# Benchmark experiment — roadmap and status

The experiment exists because How Do has no measurement. At 0.8.0 it is a
discipline document, a reference runtime, and a test suite that proves the
documents keep their promises — none of which establishes that the discipline
changes what an agent does. Every further edit to the skill is unfalsifiable
until something measures it.

Ordering principle: **the experiment that can kill the program runs early, at
the smallest scale that can see an effect.** Infrastructure is sized to what
the pilot shows, not to what the design anticipates.

Status legend: `done` · `partial` · `next` · `blocked` · `later`

---

## Next actions — ordered

Prioritised by what unblocks the most, not by what is most interesting. The
first three need no hardware and no compute; they are declarations, and every
measurement downstream is uninterpretable without them.

| # | Action | Kind | Unblocks | State |
|---|---|---|---|---|
| 1 | Declare δ\* — the smallest effect worth acting on | decision | M0.0 power gate, M0.1 endpoint | undeclared |
| 2 | Declare the reconnaissance budget cap | decision | H1/H2 arm definition | undeclared |
| 3 | Write `PILOT-0001/PREREGISTRATION.md` | writing | the Gate; `preregistration_digest` in M0 | not started |
| 4 | Run the M−1 envelope probe | hardware | M0.0, M0.1, hours-per-100-trials | next |
| 5 | Rest of the receipt schema (M0) | code | M0.1 ingestion | partial |
| 6 | Settle the payload asymmetry | decision | release hygiene at 0.9 | open |

Why this order:

1. **δ\* before anything measures.** The power gate is a comparison against
   δ\*, so an undeclared δ\* means M0.0 cannot return a verdict — only a
   variance number with no decision attached. Declaring it after seeing the
   variance is how an underpowered study becomes a positive result.
2. **The recon cap is part of the treatment, not a runtime setting.** Uncapped
   reconnaissance makes H1 mean something different on every task, and the
   frozen `TREATMENT.md` cannot describe an arm whose size is decided at run
   time.
3. **Pre-registration is the artifact the Gate reads.** It costs no compute and
   is the single largest reduction in the program's degrees of freedom. Its
   binding field is `STOP`. It must also carry the qualifier that a null here
   falsifies this treatment and not the discipline, because no arm carries the
   person-derived half.
4. **The envelope probe is the true blocking pre-requisite for measurement**,
   and the only item on this list that requires the local machine.

Items 1–3 are prerequisites for 4 being worth running: an envelope probe whose
hours-per-100-trials cannot be checked against a committed trial count only
measures the machine.

---

## M−1 — Execution envelope · `next`

Prove one exact local configuration can repeatedly run representative Harbor
tasks without memory, offload, or context behaviour changing underneath the
study.

- [ ] Probe Q4_K_M and Q8_0 across 8k/16k/32k+ context; record peak VRAM, RAM,
      tok/s, prompt throughput, offload events, failures.
- [ ] Emit **hours per 100 trials** as a first-class output. It sizes every
      later milestone and decides whether the pilot is a three-day or six-day
      loop.
- [ ] Confirm the long-horizon tasks fit under the chosen context cap. A cap
      that truncates them turns `horizon: long` into a measurement of the cap.
- [ ] Freeze the winning configuration as the organism fingerprint.

Quantization is decided by the probe, not assumed. Weights fitting VRAM is not
the property that matters; weights + KV cache + runtime buffers + real context
+ harness workload under a stable envelope is.

## M0 — Receipt · `partial`

Append-only evidence receipt, Harbor ingestion, artifact custody, immutable
fingerprints. No XP, no levels, no skill graph.

- [x] **Resolution block frozen** — `experiment/evidence/resolution.py`.
      Ordered operands, resolver attribution, canonicalization version,
      collision-resistant digest. See `CROSSINGS.md` for why this is the only
      part of a crossing that gets stored.
- [ ] The rest of the receipt: benchmark identity, environment identity,
      organism, harness, behavioural substrate, trial, judged evidence,
      resources, analysis.
- [ ] `experiment_id` + `preregistration_digest` + `condition_label` +
      `run_sequence_index`. Without these, confirmatory and exploratory trials
      are indistinguishable later, and the interleaving cannot be checked.
- [ ] `task_qualification_digest` — the oracle-5x / no-op result that granted a
      task authority. A benchmark earns authority the way a skill earns
      capability.
- [ ] Trajectories and artifacts as content-addressed digests into a blob
      store, not inline. Receipts are the hot path for every projection.
- [ ] Harbor ingestion. Do not rebuild a runner; Harbor already owns execution.

## M0.0 — Noise floor · `blocked` on M−1

Repeatedly run the unchanged organism over ~20 tasks. Estimate within-task and
across-task variance, infrastructure error rate, cost, duration.

- [ ] Variance estimate per task and across tasks.
- [ ] Screen for tasks off the floor and ceiling. On a 12B a large share of
      Harbor Index tasks will sit at 0/5 in both arms, collapsing effective n
      well below the task count.
- [ ] **Power gate.** Compute the minimum detectable effect from the measured
      variance and compare it to δ\*. If MDE > δ\*, PILOT-0001 returns
      INCONCLUSIVE by construction — fix the measurement before spending the
      trials, not after.

## M0.1 — Falsification pilot · `blocked` on M−1, M0, M0.0

H0 (raw) against H1 (HowDo + per-trial reconnaissance), same organism, same
budget, interleaved.

- [ ] Write `PILOT-0001/PREREGISTRATION.md`: question, primary endpoint,
      secondary endpoints, committed task ids, trials per task per condition,
      treatment commit SHA, control, organism fingerprint, analysis method,
      δ\*, and **GO / STOP / INCONCLUSIVE**. Written before any treatment
      result is seen.
- [ ] Declare the reconnaissance budget cap. Unbounded recon makes the
      treatment mean something different on every task.
- [ ] Collect **fresh** trials for both arms. M0.0's runs screened the task
      set; reusing them as the control is selection bias that manufactures
      lift.
- [ ] Treatment definition is frozen — see `PILOT-0001/TREATMENT.md`. The
      adapter that makes it runnable is landed.

## Gate

If HowDo produces no detectable useful lift, or harms enough tasks that no
credible transferable signal remains: **stop the skill-graph infrastructure
work and return to How Do itself.** A clean null is accepted evidence.

Read the null correctly. The pilot measures the loop plus environment context.
The person-derived half of How Do is absent from every arm, so a null falsifies
this treatment, not the discipline.

## M1 — Census · `later`

Only after signal exists. Index enough tasks to understand where the effect
came from, with Domain / Concern / Environment / Modality annotations informed
by actual trajectories rather than imagination.

## M2 — Branch · `later`

One evidence-derived skill mutation. Parent versus child against triggering
tasks, an untouched holdout, and regressions.

## M3 — Derived progression · `later`

Fit XP, levels, exhaustion, and skill points **over accumulated receipts**.
Version the progression function so the whole history can be recomputed under
another constitution.

## M4 — Autonomous search · `later`

Six workers, Harbor executing. Workers may append evidence and create candidate
branches; promotion authority stays mechanically separated — enforced by
repository and filesystem authority, not by prompt instruction.

---

## Standing rules

These came out of the design and apply across milestones.

- **Freeze what cannot be recovered; derive what can.** `EvidenceReceipt` is
  primary state. XP, levels, exhaustion, skill points, concern vectors, routing
  weights, and capability edges are projections over receipts.
- **Crossings are projections, not objects.** See `CROSSINGS.md`. Named
  crossings are hypotheses; only receipts instantiate one.
- **Lineage edges are stored; capability edges are derived.** `derived_from`,
  `specializes`, `applies_to`, `composes_into` are authored and immutable.
  `validated_on`, `transfers_to`, and demonstrated coupling are queries.
- **Certification comes from deterministic verifiers only**, at least through
  M3. Judge-scored tasks feed information gain, not level advancement.
- **Never baseline against a published Harbor leaderboard number.** The judge
  configuration has changed across eras — `claude-opus-5` now, `claude-sonnet-5`
  before that, a three-model ensemble before that — so published figures are not
  comparable across time. Compare only against numbers generated under one
  fingerprint.
- **Optimize information gain before score.** Until the terms are measurable,
  the acquisition rule is: pick the task whose pass rate under the current skill
  is nearest 0.5, penalized by cost.
- **The promotion boundary holds.** `experiment/` is not part of the install
  payload and nothing here is a How Do release. If the pilot dies at the gate,
  none of it gets promoted because the implementation is tidy.

## Open decisions

- Reconnaissance budget cap — undeclared.
- δ\* — undeclared; must be set before M0.0's power gate can be applied.
- Pilot task set — uncommitted; depends on M0.0 screening.
- Whether the environment adapter's kind-awareness in `runtime/howdo/context.py`
  should move fully out of the payload. Currently the hook ships and the
  implementation does not.
