# PILOT-0001 — results

> Copy to `RESULTS.md` when the run completes. Fill top to bottom and do not
> reorder: the preregistered result is stated before anything exploratory is
> written down, so the exploratory work cannot shape how the primary result is
> phrased.

## Provenance

| | |
|---|---|
| Preregistration digest (Stage B) | |
| Organism fingerprint | |
| Treatment commit | |
| Receipt log digest | |
| Analysis commit | |
| Seeds (permutation / bootstrap) | |
| Collection window | |

All receipts carry one organism fingerprint and one preregistration digest. If
they do not, say so here and stop — the run is two runs.

## Integrity

| Check | Result |
|---|---|
| Receipts failing `verify_receipt()` | |
| Trials collected vs Stage B schedule | |
| Exclusion rate, H0 / H1 | |
| Exclusion ceiling (10%) respected | |
| Task ids outside the committed set | |
| Corrections appended | |

## Preregistered result

**Outcome: GO / STOP / INCONCLUSIVE** — as computed by `decide()`, not as read
off the numbers.

| | |
|---|---|
| Primary endpoint (mean per-task H1 − H0) | |
| 95% interval | |
| δ\* | |
| Permutation p-value | |
| Committed tasks analysed | |

One sentence stating what this outcome means for the programme, in the
preregistration's own words.

### Secondary endpoints

| | H0 | H1 |
|---|---|---|
| Task-level wins / losses / ties | | |
| Harm rate at δ\* (reported, not a gate) | | |
| Reconnaissance outcomes (complete / over budget / failed) | | |
| Median wall clock per trial | | |
| Median total tokens per trial | | |

### Deviations

Every entry from the preregistration's deviations register, or "none".

---

## Exploratory

> Everything below was not preregistered. It cannot change the outcome above,
> and no claim here is evidence for the programme continuing. It exists to
> generate hypotheses for a later study, and every line should read as one.

### Compute confound

H1 spends reconnaissance tokens H0 does not. Any token-matched or
covariate-adjusted comparison goes here, clearly labelled, with the reminder
that `TREATMENT.md` already declares PILOT-0001 cannot attribute an effect among
the treatment's components.

### Breakdowns

Per-domain, per-modality, per-horizon. Note the number of tasks behind each
cell; most will be too few to say anything.

### Trajectory observations

Anything noticed while reading trajectories. Impressions, not findings.

---

## What this does not establish

Restated for anyone reading only this file:

- The person-derived half of How Do is absent from every arm. A null falsifies
  this treatment, not the discipline.
- Tasks were screened to those a raw agent finds neither trivial nor
  impossible. The figure above is an effect on that set, not on Harbor Index.
- Any effect is unattributed among the treatment's components.
