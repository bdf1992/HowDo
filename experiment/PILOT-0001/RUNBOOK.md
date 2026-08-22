# PILOT-0001 — runbook

The point of this document is that **nobody makes a decision while the study is
running.** Every choice worth making was made in `PREREGISTRATION.md`; every
choice left here is mechanical. If executing a step requires judgement, that is
a defect in the preregistration, and the fix is to stop and amend it — with a
deviation-register entry — rather than to decide well in the moment.

Read `PREREGISTRATION.md` first. This is the how; that is the what.

---

## Before anything runs

Each of these gates has a mechanical answer. A `no` stops the run.

1. **Organism frozen?**

   ```bash
   python -c "
   import sys; sys.path.insert(0, 'experiment')
   from evidence import load_organism
   print(load_organism('experiment/M-1/ORGANISM.lock.json').fingerprint)"
   ```

   A traceback means M−1 is not finished. Do not hand-write a lock file to get
   past this.

2. **Preregistration frozen at Stage B?**

   ```bash
   python -c "
   import sys; sys.path.insert(0, 'experiment')
   from evidence import preregistration_digest
   print(preregistration_digest('experiment/PILOT-0001/PREREGISTRATION.md'))"
   ```

   A `PreregistrationError` lists what is still undeclared. It is not a
   formality: a confirmatory receipt citing an unfrozen preregistration is
   uninterpretable later.

3. **Every committed task qualified?** Each task id in the Stage B set has a
   qualification record whose `outcome` is `qualified` — not `research_only`,
   not `rejected` — and `verify_qualification()` returns True for it.

4. **Power gate passed?** MDE computed from M0.0's variance at the Stage B trial
   count, and MDE ≤ δ\*. If not, the study does not run. See the preregistration;
   the response is to fix the measurement, not to lower δ\*.

5. **Analysis code committed?** Written, committed, and demonstrated to recover
   a known effect from synthetic data — before any real trial exists.

6. **Treatment commit recorded?** The SHA of `TREATMENT.md`'s commit, and the
   content digest of the skill bytes the agent will actually load. A commit
   identifies a tree; a working tree can differ from it.

## Harbor commands

Verified against `harbor-framework/harbor@39b8587`. `harbor run` is an alias for
`harbor job start`.

**Qualify the pool — no model inference, so do this first.** Every
`terminal-bench` 2.0 task ships a `solution/solve.sh`, so the oracle agent can
run across the whole pool in hours rather than the weeks a screening pass costs.

```bash
harbor run --dataset terminal-bench==2.0 --agent oracle  --n-attempts 5 --jobs-dir runs/qualify-oracle
harbor run --dataset terminal-bench==2.0 --agent nop     --n-attempts 3 --jobs-dir runs/qualify-noop
```

Then fold the two into qualification records:

```bash
python -c "
import sys; sys.path.insert(0, 'experiment')
from harness import qualify_task
# one call per task, oracle_results and noop_results read from the jobs dirs
"
```

**A measured run.**

```bash
harbor run \
  --dataset terminal-bench==2.0 \
  --agent <scaffold> --model <organism> \
  --n-attempts <trials per task> \
  --agent-timeout-multiplier <declared> \
  --n-concurrent <declared> \
  --jobs-dir runs/<stage>
```

Two flags are treatment parameters rather than conveniences.
`--agent-timeout-multiplier` scales every task's cap; declared once and
identical across arms it is legitimate, changed mid-study it invalidates the
arm. `--n-concurrent` must not exceed what M−1 accepted as stable.

**Why the multiplier matters more than it looks.** Across the 89 tasks the agent
timeout is median 15 min, p90 60 min, max 200 min — one worst-case sweep is 41.5
hours. A failing agent does not stop early, it works until its cap, and the
pilot's organism is expected to fail often. Cost is therefore timeout-bound
rather than throughput-bound, and the multiplier is the largest single lever on
how long the study takes.

## Per trial

The lifecycle is fixed by the contamination law in `TREATMENT.md`. Every step
happens for every trial, in this order, with no reuse between trials.

```text
1. new container from the pinned image digest
2. assert trial_id                      -- fresh, never reused
3. H1/H2 only: open ephemeral environment context bound to trial_id
4. H1/H2 only: reconnaissance, under the declared budget
5. H1/H2 only: complete_reconnaissance() -- or record the failure and continue
6. run the task under the arm's configuration
7. deterministic verifier
8. build the receipt
9. append the receipt
10. destroy the container and the context
```

Notes on the steps that go wrong quietly:

- **Step 2.** A reused `trial_id` is not a naming mistake; it makes the
  contamination check vacuous. The ephemeral context refuses a read from a
  different trial by reporting `expired`, which only works if the ids differ.
- **Step 4.** When the budget binds, stop. Record `recon_outcome:
  over_budget` and continue into step 6. Do not extend the budget for this
  trial — the cap is part of the treatment.
- **Step 5.** Reconnaissance failure is **treatment failure.** The trial
  continues, counts in the primary endpoint, and records `recon_outcome:
  failed`. It is not an exclusion.
- **Step 9.** `append_receipt()` refuses an out-of-order `run_sequence_index`.
  If it refuses, something has run out of order and the log is telling you
  before the analysis has to.
- **Step 10.** Destruction is not cleanup, it is the treatment. A container
  that survives into the next trial carries information the arms are supposed
  not to have.

## Arm scheduling

- Generate the full trial schedule **once**, before the first trial, from the
  committed task set and the seed recorded in the preregistration.
- The schedule interleaves arms. It is not regenerated mid-run, and a resumed
  run continues the existing schedule rather than making a new one.
- Persist the schedule beside the receipt log. A schedule that exists only in a
  process's memory cannot be checked against the receipts afterwards.

## When something fails

Look up the disposition; do not decide it.

| What happened | Do |
|---|---|
| Reconnaissance failed or returned nothing usable | Continue. `recon_outcome: failed`. **Counts** |
| Reconnaissance hit the budget | Continue. `recon_outcome: over_budget`. **Counts** |
| Container did not start / harness crashed / runner lost | `result: error`, `failure_class` set, **exclude and re-run** at the end of the schedule |
| Verifier itself errored on a qualified task | `result: error`, `failure_class: verifier_infrastructure`, **exclude and re-run** |
| Model produced nothing before the harness timeout | `result: fail`. **Counts** — this is the organism's behaviour |
| A receipt was written wrong | `correct_receipt()`. Never edit the log |
| Exclusions exceed 10% in either arm | **Void the run.** Fix the cause, start over |

## After collection

1. **Do not look at the difference yet.** Run the integrity checks first, so
   that what they find cannot be influenced by knowing which way it cuts.

   ```bash
   python -c "
   import sys; sys.path.insert(0, 'experiment')
   from evidence import read_receipts, verify_receipt
   rs = [r for r in read_receipts('runs/pilot-0001/receipts.jsonl') if 'correction' not in r]
   bad = [r['receipt_digest'] for r in rs if not verify_receipt(r)]
   print(len(rs), 'receipts,', len(bad), 'failing verification')"
   ```

2. **Check the run against the plan.** One `organism_fingerprint` throughout.
   One `preregistration_digest` throughout. Trial counts equal to the Stage B
   schedule. Exclusion rate under the ceiling in both arms. Every task id in the
   committed set and no others.

3. **Run the committed analysis, once**, with the recorded seeds.

4. **Read the outcome off the preregistration.** GO, STOP, or INCONCLUSIVE.
   INCONCLUSIVE is not a soft GO.

5. **Write the result.** Preregistered analysis first and clearly separated from
   anything exploratory. If the outcome is STOP, that is a finding and is
   published as one — the packaging boundary exists so that STOP costs a
   directory rather than a release.

6. **Carry the qualifier.** Any reported null falsifies this treatment on this
   organism on these tasks. The person-derived half of How Do is absent from
   every arm and is not under test.
