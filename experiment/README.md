# Benchmark experiment

Not part of How Do. Nothing here is installed, nothing here is released, and
nothing here has earned a place in the skill. `install.py` copies `runtime/` and
never this directory; `tests/test_release.py` enforces that an ordinary install
contains no experiment code. If the measurement returns a null, this directory
is deleted and How Do 0.8.0 is unaffected — that is the point of keeping it
separate rather than the reason to doubt it.

## Why it exists

How Do is a discipline document, a reference runtime, and a test suite proving
the documents keep their promises. None of that establishes that the discipline
changes what an agent does. Until something measures it, every further edit to
the skill is unfalsifiable.

## Reading order

Read these in order. Each one is a precondition for the next being meaningful.

1. **`ROADMAP.md`** — milestones, status, what blocks what, and the ordered
   queue of next actions. Start here; it will tell you where the work actually is.
2. **`PILOT-0001/TREATMENT.md`** — what the treatment *is*, frozen before any
   implementation. Defines the two context kinds, the trial lifetime, the
   contamination law, and the H0/H1/H2 arms. Also states what a positive result
   would not establish.
3. **`PILOT-0001/PREREGISTRATION.md`** — the committed study: question, endpoints,
   task set, trial counts, analysis, and the GO / STOP / INCONCLUSIVE rule.
   Written before any treatment result is seen.
4. **`PILOT-0001/RUNBOOK.md`** — the exact commands and trial lifecycle, so the
   study can be executed without anyone making a decision midstream.
5. **`evidence/RECEIPT.md`** — the evidence contract: what every trial writes
   down, and which fields are frozen because they cannot be recomputed later.

Two documents sit outside that spine and are read when they apply:

- **`M-1/PROTOCOL.md`** — the execution-envelope probe that freezes the organism
  configuration every later receipt references.
- **`TASK-QUALIFICATION.md`** — what earns a benchmark task the authority to
  count as evidence.
- **`CROSSINGS.md`** — why crossings are projections over receipts rather than
  stored objects, and why only the resolution block is persisted.

## Standing constraints

- **Freeze what cannot be recovered; derive what can.** Receipts are primary
  state. XP, levels, skill points, routing weights, and capability edges are
  projections over them.
- **Raw evidence is never rewritten.** Corrections are appended.
- **Preregistration precedes confirmatory data.** Analysis chosen after seeing
  results is exploratory and must be labelled so.
- **Code here does not imply promotion.** An elegant adapter is not evidence
  that the treatment works.
