# When a benchmark task is allowed to count

A benchmark task earns the authority to be evidence the same way a skill earns
capability: by demonstration, recorded, before it is relied on. An unqualified
task in the set does not merely add noise — it adds *bias*, and in a known
direction.

Two failure modes motivate the whole procedure:

- **A task that cannot be solved at all.** Broken fixture, missing dependency,
  impossible instruction. It scores 0 in every arm, contributes no information,
  and silently shrinks the effective sample while the task count says otherwise.
- **A task that passes without being solved.** A verifier checking that a file
  exists, that the process exited zero, that output is non-empty. It scores 1 in
  every arm and dilutes any real effect toward zero.

Both look like ordinary tasks in an aggregate score. Neither is detectable after
the pilot without the trials that would have detected it beforehand.

---

## The procedure

Run per task, before the task is committed to any study, and recorded whether it
passes or not. A rejected task is part of the record; deleting rejections turns
the committed set into a selected set.

### 1. Pin the task

Record `suite`, `suite_version`, `task_id`, `task_version`, and a digest of the
task definition as it stood. Harbor's definitions change. A task id is a name,
not an identity, and two studies citing `hb-0042` a year apart may not be citing
the same task.

### 2. Oracle run — can it be solved?

Execute a known-good solution **5 times**. All 5 must pass.

Five rather than one because a task that passes 4/5 is not a solvable task with
a flake; it is a task whose verifier or fixture is nondeterministic, and that
nondeterminism will land in the study as within-task variance attributed to the
treatment.

The oracle is a *solution*, not the model. This step qualifies the task and the
harness, not the organism, so it does not depend on the M−1 configuration and
does not need to be repeated when the organism changes.

### 3. No-op run — must it be solved?

Execute a no-op agent — one that starts, does nothing, and exits — **3 times**.
All 3 must fail.

A single no-op pass disqualifies the task outright. It means the verifier
accepts the initial state, so the task measures nothing, and it will drag the
measured effect toward zero in both arms.

### 4. Verifier type

Record `deterministic` or `judge`.

A judge-scored task may be **research_only**: it can inform the census, the
acquisition rule, and exploratory analysis. It may never certify capability or
advance a level, at least through M3. The judge configuration has changed across
Harbor eras, so a judge-scored number is not comparable across time even against
itself.

### 5. Infrastructure flakes

Container failures, network timeouts, and runner losses during qualification are
counted separately from oracle failures — an OOM is not evidence that the task
is unsolvable.

But they are counted. If more than **20%** of qualification attempts are
infrastructure errors, the task is rejected for flakiness. A task that fails to
execute one run in five will consume trials and produce exclusions, and every
exclusion is a place where a decision about which trials count gets made after
the data is visible.

### 6. Outcome

Derived from the counts, never asserted:

| Outcome | Meaning |
|---|---|
| `qualified` | Oracle 5/5, no-op 3/3 failed, deterministic verifier, flake rate under cap. May certify. |
| `research_only` | Same, but a judge verifier. Informs research; never certifies. |
| `rejected` | Any of the above unmet. The reason is recorded and the task is excluded from the study. |

The whole record is digested, and that digest is the
`task_qualification_digest` every receipt carries. A trial citing a task
qualification is citing the exact counts that granted the authority, not a claim
that qualification happened.

---

## What this does not establish

- **That the oracle solution is a good one.** It shows the task is solvable, not
  that it is solvable in a way that resembles the work the study cares about.
- **That the task is discriminating.** A task both arms pass 100% of the time is
  qualified and useless. Screening for floor and ceiling effects is M0.0's job,
  on the measured pass rates, and is separate from qualification.
- **That the verifier tests the right thing.** The no-op run rules out a
  verifier that accepts *nothing being done*. It does not rule out a verifier
  that accepts the wrong thing being done.
- **That qualification survives a Harbor upgrade.** It does not. A new
  `suite_version` or `task_version` requires re-qualification, and the digest is
  how a later reader notices that it was not re-run.
