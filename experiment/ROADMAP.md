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

Each milestone has an issue: [#8](https://github.com/bdf1992/HowDo/issues/8) M−1, [#9](https://github.com/bdf1992/HowDo/issues/9) M0, [#10](https://github.com/bdf1992/HowDo/issues/10) M0.0, [#11](https://github.com/bdf1992/HowDo/issues/11) M0.1. The four undeclared values block [#11](https://github.com/bdf1992/HowDo/issues/11) and need no hardware.

---

## Next actions — ordered

Prioritised by what unblocks the most, not by what is most interesting. The
first three need no hardware and no compute; they are declarations, and every
measurement downstream is uninterpretable without them.

| # | Action | Kind | Unblocks | State |
|---|---|---|---|---|
| 1 | Declare δ\* — the smallest effect worth acting on | decision | M0.0 power gate, M0.1 endpoint | proposed 0.10, awaiting sign-off |
| 2 | Declare the reconnaissance budget cap | decision | H1/H2 arm definition | proposed 8k tokens / 12 calls, awaiting sign-off |
| 2b | Declare the task variance ceiling and the harm-rate ceiling | decision | Stage A freeze | proposed, awaiting sign-off |
| 3 | Write `PILOT-0001/PREREGISTRATION.md` | writing | the Gate; `preregistration_digest` in M0 | written; unfrozen pending 1, 2, 2b |
| 4 | Run the M−1 envelope probe | hardware | M0.0, M0.1, hours-per-100-trials | protocol written; probe not run |
| 5 | Rest of the receipt schema (M0) | code | M0.1 ingestion | done except Harbor ingestion |
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

## M−1 — Execution envelope · `next` · [#8](https://github.com/bdf1992/HowDo/issues/8)

Prove one exact local configuration can repeatedly run representative Harbor
tasks without memory, offload, or context behaviour changing underneath the
study.

- [x] **Protocol written** — `M-1/PROTOCOL.md`. What varies, what is held
      constant, what counts as stable (declared before the probe runs), what is
      recorded, and the three outcomes including "no stable cell exists".
- [x] **Lock file is executable** — `M-1/ORGANISM.template.json` plus
      `evidence/organism.py`. The fingerprint is computed from the
      configuration and refuses a lock with any field left unfilled; the
      observed envelope is recorded but excluded from the digest.
- [x] **Probe set chosen** — six named tasks stratified across the measured
      timeout distribution (10–200 min cap, 2–8 GB container, four categories),
      committed as excluded from the pilot before the probe runs.
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

## M0 — Receipt · `partial` · [#9](https://github.com/bdf1992/HowDo/issues/9)

Append-only evidence receipt, Harbor ingestion, artifact custody, immutable
fingerprints. No XP, no levels, no skill graph.

- [x] **Resolution block frozen** — `experiment/evidence/resolution.py`.
      Ordered operands, resolver attribution, canonicalization version,
      collision-resistant digest. See `CROSSINGS.md` for why this is the only
      part of a crossing that gets stored.
- [x] **The contract is written** — `evidence/RECEIPT.md`. Nine sections, the
      reason each field cannot be recomputed, and an explicit list of what the
      code does *not* enforce so the gap is visible rather than assumed closed.
- [x] **The rest of the receipt** — `evidence/receipt.py`. Experiment,
      benchmark, environment, organism, treatment, resolution, outcome,
      resources, custody. `experiment_id`, `preregistration_digest`,
      `analysis_class`, `condition_label` and `run_sequence_index` are
      required; a confirmatory trial with no preregistration in force is
      refused, and the append refuses an out-of-order sequence index because
      interleaving is only checkable from the order actually recorded.
- [x] **`task_qualification_digest` is a required field**, and the procedure
      that produces it is written and executable — `TASK-QUALIFICATION.md`
      plus `evidence/qualification.py`. Oracle 5×, no-op 3×, verifier type,
      a 20% infrastructure-flake cap, and an outcome derived from the counts
      rather than asserted.
- [x] **Trajectories and artifacts are content addresses.** A path or an inline
      payload is refused; receipts are the hot path for every projection.
- [x] **Certification is derived, not written.** Deterministic verifier,
      confirmatory run, passing result — recomputed at verification time, so a
      hand-edited receipt fails even with its digest recomputed to match.
- [x] **Corrections append.** A wrong receipt is corrected by an entry naming
      its digest and the reason; the original stays.
- [ ] `organism` block wired from a real `ORGANISM.lock.json` (needs M−1).
- [x] **Committed analysis** — `analysis/pilot0001.py`, written before any
      trial exists and shown to recover a known effect from synthetic data.
      Task-level permutation test and bootstrap, seeded, zero dependencies.
      Writing it early paid immediately: it caught two defects in the drafted
      stopping rule (see `CHANGELOG.md`).
- [x] **Sizing note** — `PILOT-0001/SIZING.md`. Tasks buy more precision than
      trials do, because the task is the unit of analysis.
- [x] **Results template** — `PILOT-0001/RESULTS.template.md`, preregistered
      result before exploratory work, by document order.
- [x] **Harbor ingestion** — `experiment/harness/`. `ingest.py` maps a Harbor
      `TrialResult` to a receipt, `blobs.py` is the content-addressed store,
      `qualify.py` folds oracle and no-op runs into a qualification record. No
      runner was rebuilt: Harbor owns execution and this is the seam.
- [x] **Trial schedule** — `harness/schedule.py`. Round-based rather than a
      flat shuffle, so the arms are balanced after every round and drift across
      the run hits both equally. Generated once, persisted with a digest,
      resumable by sequence index, and refusing both an overwrite and a resume
      under changed parameters.
- [x] **Post-collection checks** — `harness/checks.py`. The runbook's step 2 as
      code: every receipt verifies, one organism and one preregistration
      throughout, no stray analysis class, unique sequence indices, exclusions
      under the ceiling per arm, only committed tasks, every receipt matching
      the trial the schedule planned, and no dangling correction.
- [ ] Wire the seam to a real Harbor job on the target machine (needs M−1).

## M0.0 — Noise floor · `blocked` on M−1 · [#10](https://github.com/bdf1992/HowDo/issues/10)

Repeatedly run the unchanged organism over ~20 tasks. Estimate within-task and
across-task variance, infrastructure error rate, cost, duration.

- [ ] Variance estimate per task and across tasks.
- [ ] Screen for tasks off the floor and ceiling. On a 12B a large share of
      `terminal-bench` 2.0's 89 tasks will sit at 0/5 in both arms, collapsing
      effective n well below the task count. The pool is 89, not a larger
      index: see `PILOT-0001/SIZING.md`.
- [ ] **Power gate.** Compute the minimum detectable effect from the measured
      variance and compare it to δ\*. If MDE > δ\*, PILOT-0001 returns
      INCONCLUSIVE by construction — fix the measurement before spending the
      trials, not after.

## M0.1 — Falsification pilot · `blocked` on M−1, M0, M0.0 · [#11](https://github.com/bdf1992/HowDo/issues/11)

H0 (raw) against H1 (HowDo + per-trial reconnaissance), same organism, same
budget, interleaved.

- [x] **`PILOT-0001/PREREGISTRATION.md` is written** — question, hypotheses,
      one primary endpoint, four secondary endpoints, task-selection rule with
      its screening bias declared, randomization and interleaving, analysis
      method with seeds, exclusions with a ceiling, a deviations register, and
      **GO / STOP / INCONCLUSIVE** where INCONCLUSIVE is explicitly not a soft
      GO. Frozen in two stages: everything M0.0 must not influence is Stage A;
      the task set and trial count are Stage B, filled from M0.0's output.
- [x] **`PILOT-0001/RUNBOOK.md` is written** — pre-run gates, the per-trial
      lifecycle, arm scheduling, a disposition table to look up rather than
      decide, and post-collection checks ordered so integrity is verified
      before the difference is looked at.
- [ ] **Declare the four open values.** The preregistration carries each as a
      marked block with a proposal and its reasoning, and
      `evidence/preregistration.py` refuses to digest the document while any
      remains — so no confirmatory trial can cite it until a person decides:
      the task variance ceiling, δ\*, the reconnaissance budget, and the
      harm-rate ceiling.
- [ ] Collect **fresh** trials for both arms. M0.0's runs screened the task
      set; reusing them as the control is selection bias that manufactures
      lift.
- [ ] Treatment definition is frozen — see `PILOT-0001/TREATMENT.md`. The
      adapter that makes it runnable is landed.

## M0.2 — Rehearsal · `blocked` on M−1, M0

Run the whole machinery on tasks excluded from the pilot and discard the
results. See `PILOT-0001/REHEARSAL.md`.

- [x] Procedure written, with the checklist of what must be exercised.
- [ ] Executed. Needs a running harness.

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

- Reconnaissance budget cap — proposed in `PILOT-0001/PREREGISTRATION.md`, not signed off.
- δ\* — proposed at 0.10, not signed off; must be set before M0.0's power gate.
- Task variance ceiling and harm-rate ceiling — proposed, not signed off.
- Pilot task set — uncommitted; Stage B, depends on M0.0 screening.
- Whether the environment adapter's kind-awareness in `runtime/howdo/context.py`
  should move fully out of the payload. Currently the hook ships and the
  implementation does not.
