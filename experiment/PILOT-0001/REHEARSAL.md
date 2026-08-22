# Plumbing rehearsal

Run the entire pilot machinery end to end **before** the pilot, on tasks that
are explicitly excluded from it, and throw the results away.

The rehearsal exists because the failures that ruin a study are almost never
statistical. They are a receipt field left null, a container that did not get
destroyed, a schedule regenerated on resume, a digest computed over the wrong
bytes. All of them are discoverable in twenty trials and all of them are
expensive to discover in a thousand.

## Rules

- **Tasks are drawn from outside the committed set**, and outside the M−1 probe
  set. A rehearsal on committed tasks contaminates them: those trials would have
  to be either used, which breaks the fresh-trials rule, or discarded, which is
  a decision about the committed set made outside the preregistration.
- **`analysis_class: rehearsal`** in every receipt. The analysis ignores
  anything that is not `confirmatory`, and the field is what makes that
  automatic rather than remembered.
- **A separate receipt log.** `runs/rehearsal/receipts.jsonl`. Never the pilot's.
- **Results are not read as evidence.** Not even informally, and especially not
  the direction of the difference. A rehearsal that produced an encouraging
  number is the single most likely reason someone later relaxes δ\*.

## Already covered without containers

`tests/test_end_to_end.py` drives the whole chain over a directory shaped like
Harbor's output: the walk, the blob store, ingestion, the append-only log, the
schedule, the audit, and the analysis, in the order a real run would. It runs in
CI on every push.

It found two things on its first execution, which is the argument for it:

- **Discovery order is not run order.** Harbor names trial directories after the
  task, so a filesystem walk returns them alphabetically while the study ran
  them interleaved. Appending in walk order hit the log's sequence rule and
  stopped the ingestion — correctly, but with an error that reads like a corrupt
  log rather than like a caller iterating wrongly. Hence
  `harness.ordered_trials()` and the mapping obligation in the runbook.
- **A size check is not a content check.** An assertion that the terminal
  recording was excluded was written against total store size, which tar's 10 KB
  block padding dominates. It would have passed while storing the recordings.

What it cannot do is prove Harbor writes what the fixture writes. That is what
the rehearsal below is for, and none of it is dispensable on account of the
synthetic pass.

## What it must exercise

Twenty trials, both arms, is enough if all of this happens at least once:

- [ ] A trial in each arm, interleaved by the real scheduler
- [ ] Reconnaissance completing normally
- [ ] Reconnaissance hitting its budget → `recon_outcome: over_budget`, trial
      continues
- [ ] Reconnaissance failing → `recon_outcome: failed`, trial continues
- [ ] A deliberately induced infrastructure error → excluded, `failure_class`
      set, re-run at the end of the schedule
- [ ] A `correct_receipt()` call against a receipt written wrong on purpose
- [ ] A resumed run, killed mid-schedule and restarted, continuing the existing
      schedule rather than generating a new one
- [ ] An ephemeral context read attempted from the wrong trial id → `expired`
- [ ] Containers confirmed destroyed between trials

## What it proves passed

- [ ] Every receipt satisfies `verify_receipt()`
- [ ] One `organism_fingerprint` across all of them
- [ ] `run_sequence_index` strictly increasing, with no gaps unexplained by
      exclusions
- [ ] The recorded schedule matches the receipts in order and composition
- [ ] Every `trajectory_digest` resolves to bytes in the blob store, and those
      bytes hash back to the digest
- [ ] The analysis runs to completion on the rehearsal log and returns a
      decision — the decision itself is discarded unread where practical

## Afterwards

Delete nothing. Keep the rehearsal log; it is the only record that the
machinery was tested, and a later reader asking "was any of this ever checked"
deserves an answer that is not a memory.
