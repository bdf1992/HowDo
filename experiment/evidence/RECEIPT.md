# The evidence receipt

One trial produces one receipt. Receipts are the primary state of the whole
research programme: XP, levels, exhaustion, skill points, concern vectors,
routing weights, capability edges, and the skill graph itself are projections
over them and can be recomputed under a different theory. The receipt cannot.

That asymmetry sets the design rule. **Freeze what cannot be recovered; derive
what can.** A field belongs in the receipt if and only if it is gone once the
container exits. Everything else is a query, and putting it here would freeze a
research decision into the evidence layer where it cannot be revised.

This document is the contract. `evidence/receipt.py` enforces the parts that
are mechanically checkable; the rest is enforced by review, and the boundary
between the two is stated at the end rather than left to be discovered.

---

## Storage

An append-only JSON Lines file. One receipt per line, written once.

- **Nothing is ever edited or deleted.** A receipt discovered to be wrong is
  corrected by appending a correction that names the original's digest and the
  reason. Both remain. An analysis that silently benefits from a rewritten
  history is indistinguishable from one that does not.
- **`run_sequence_index` is strictly increasing within an experiment.** The
  writer refuses an out-of-order append. Interleaving between arms is the main
  defence against drift over a long run, and it is only checkable afterwards if
  the order the trials actually ran in is recorded rather than inferred.
- **Trajectories and artifacts are content addresses, not payloads.** Receipts
  are the hot path for every projection; a receipt carrying a megabyte of
  transcript makes every future query pay for it. The digest goes in the
  receipt, the bytes go in the blob store.

## Sections

### `experiment` — which study this trial belongs to

| Field | Why it cannot be recovered |
|---|---|
| `experiment_id` | Trials from different studies are otherwise pooled by accident |
| `preregistration_digest` | The commitments in force *when this ran*. A later edit to the preregistration must not silently reinterpret old trials |
| `analysis_class` | `confirmatory`, `exploratory`, or `rehearsal`. Decided before the run; after the fact everything looks confirmatory |
| `condition_label` | Which arm. `h0-raw`, `h1-howdo-recon`, `h2-howdo-frozen` |
| `run_sequence_index` | The order trials actually ran, which is how drift is detected |
| `trial_id` | Binds ephemeral context to this trial and nothing else |

### `benchmark` — what was attempted

| Field | Why |
|---|---|
| `suite`, `suite_version` | Harbor's task definitions change; a task id alone is not an identity |
| `task_id`, `task_version` | Same reason, one level down |
| `task_qualification_digest` | The oracle-and-no-op result that granted this task authority to count. See `TASK-QUALIFICATION.md` |

### `environment` — where it ran

| Field | Why |
|---|---|
| `image_ref`, `image_digest` | The container is part of the treatment surface, not neutral scenery |
| `environment_context_digest` | For H1/H2, which environment context was in force. Null for H0 |

### `organism` — what ran it

The block emitted by `evidence/organism.py`: `organism_fingerprint` plus the
few fields worth having inline for triage. Receipts under two fingerprints are
never pooled.

### `treatment` — what was administered

| Field | Why |
|---|---|
| `arm` | `h0`, `h1`, `h2` |
| `skill_commit` | Which commit of How Do |
| `skill_content_digest` | The bytes actually loaded. A commit identifies a tree; the digest identifies what the agent read, which is what a working tree can make differ |
| `recon_budget` | The declared cap, recorded per trial because a cap changed mid-study is a treatment change |
| `recon_used` | What the trial actually spent |
| `recon_outcome` | `complete`, `over_budget`, `failed`, or `not_applicable`. Reconnaissance failure is treatment failure, not an excluded trial |

### `resolution` — what the work context was composed of

The block emitted by `evidence/resolution.py`. Ordered operands, resolver
attribution, canonicalization version, digest. The one part of a crossing that
is stored, because it exists only while the container does. See `CROSSINGS.md`.

### `outcome` — what happened

| Field | Why |
|---|---|
| `result` | `pass`, `fail`, `error`, `excluded`. Closed set |
| `verifier_kind` | `deterministic` or `judge` |
| `verifier_exit_code` | The mechanical answer, kept separate from any interpretation of it |
| `verifier_output_digest` | The verifier's own output, in the blob store |
| `failure_class` | Required for `error` and `excluded`, refused for `pass` and `fail`. A typed cause, not prose |
| `failure_note` | Prose, optional, never load-bearing |

`certifies` is **derived, not written.** A trial certifies capability only when
it passed, under a deterministic verifier, in a confirmatory run. Judge-scored
trials inform research and never advance a level; that rule is worth nothing if
a writer can assert `certifies: true`, so the writer cannot supply the field at
all.

### `resources` — what it cost

`wall_clock_seconds`, `prompt_tokens`, `completion_tokens`, `peak_vram_bytes`.
Cost is half of the acquisition rule — pick the task nearest a 0.5 pass rate,
penalized by cost — so it is evidence rather than telemetry.

### `custody` — where the bytes are

`trajectory_digest` and `artifact_digests`. Content addresses only; a filesystem
path is refused, because a path is a claim about a machine that will be
reformatted.

---

## What the code enforces

- Required sections and required fields present, no unknown top-level sections
- `result`, `verifier_kind`, `analysis_class`, `arm`, `failure_class`,
  `recon_outcome` drawn from their closed sets
- `failure_class` required exactly when `result` is `error` or `excluded`
- `certifies` derived and refused as an input
- Confirmatory trials carry a non-empty `preregistration_digest`
- Custody references are content addresses, not paths or inline payloads
- `receipt_digest` over canonical JSON, recomputable by any later reader
- Append-only writes, with `run_sequence_index` strictly increasing per
  experiment
- Corrections reference an existing receipt's digest and never mutate it

## What review enforces

Stated here so the gap is visible rather than assumed closed.

- **That the recorded values are true.** A receipt saying `arm: h1` when the
  harness ran H0 is structurally perfect. Nothing in the file can catch it; only
  the runbook and the harness code can.
- **That `analysis_class` was decided before the run.** The field is a
  commitment, and its honesty is a property of when it was written.
- **That the trajectory digest addresses the trajectory.** Custody proves the
  bytes have not changed since they were addressed, not that the right bytes
  were addressed.
- **That an excluded trial was excluded for its declared reason.** Exclusion
  rules live in the preregistration; the receipt records which one was invoked,
  not whether invoking it was fair.
