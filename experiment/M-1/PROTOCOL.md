# M−1 — Execution envelope protocol

Status: `next`. Blocks M0.0 and M0.1.

M−1 exists to answer one question: **is there an execution configuration whose
behaviour does not change underneath the study?** Everything measured later is
a difference between two arms. A difference the machine produces on its own —
because a longer context tipped the model into offload, because thermal
throttling arrived at trial 40, because a truncation silently shortened a
prompt — is indistinguishable from a treatment effect after the fact.

This is not a performance tuning exercise and the goal is not the fastest
configuration. It is the configuration that is *boring*: the one whose
resource curve, failure rate, and speed are the same at trial 200 as at
trial 1.

M−1 ends by writing exactly one file, `ORGANISM.lock.json`, and every later
receipt carries its digest. A trial that cannot name the organism it ran on is
not evidence.

---

## What is varied

The probe is a grid. Every cell is one combination of:

| Factor | Levels |
|---|---|
| Quantization | `Q4_K_M`, `Q8_0` |
| Context cap | 8k, 16k, 32k, and the largest cap the configuration admits |
| Offload split | fully resident on GPU; partial, at the largest split the hardware allows |
| Concurrency | 1 trial at a time; the highest concurrency intended for the pilot |

Quantization is a probe output, not an input assumption. Weights fitting VRAM
is not the property that matters — weights **plus** KV cache **plus** runtime
buffers **plus** real context **plus** harness workload, under an envelope that
does not shift, is.

## What is held constant

Anything varying here would make a cell uninterpretable, so all of it is fixed
before the first run and recorded in every row:

- Model family, parameter count, and the exact weight file
- Inference runtime build (commit or release tag), and its build flags
- Sampling settings, including whether decoding is greedy
- Hardware: GPU, VRAM, CPU, system RAM, storage class
- OS, kernel, and GPU driver version
- Harbor version and the harness configuration
- The probe task set and the exact prompts issued

## The probe task set

Drawn from Harbor tasks that are **explicitly excluded from PILOT-0001**. A
configuration tuned against tasks the pilot will later score is a configuration
selected on the outcome.

The set must include:

1. The longest-horizon candidate task available. A context cap that truncates
   it turns `horizon: long` into a measurement of the cap rather than of the
   model, and that failure is invisible in aggregate scores.
2. At least one task that writes substantial output, so KV growth is exercised
   in both directions.
3. At least one task the model is expected to fail. Failure paths take
   different execution routes and have their own resource profile.

## What counts as stable

A cell is **stable** only if, across `R` repeats of the whole probe set (`R`
declared before running, minimum 3):

- **No offload transition mid-run.** The resident/offloaded split is the same
  at the end of a run as at the start. One transition disqualifies the cell —
  it means the envelope has a cliff inside the operating range, and the pilot
  will cross it on some unlucky task.
- **No truncation.** Zero prompts or completions clipped by the context cap.
  Truncation is a silent treatment change: the H1 arm carries more context, so
  it hits the cap first, so the treatment gets quietly weakened exactly where
  it should be strongest.
- **No hard failures.** Zero OOM, zero runtime crash, zero harness timeout.
- **Peak VRAM within 5% across repeats**, and peak system RAM likewise.
- **Throughput coefficient of variation ≤ 0.15** on both prompt and generation
  rate. A wider spread does not disqualify the configuration outright, but it
  is carried into M0.0 as a known variance source and it raises the minimum
  detectable effect.

Determinism is **recorded, not required.** Run one greedy-decoding cell twice
on identical input and record whether the output bytes match. Many runtimes are
nondeterministic under batching. If this configuration is, that is a variance
source M0.0 must estimate rather than a defect to fix here — but discovering it
in M0.0 without knowing it was possible would waste the milestone.

## What is recorded, per cell, per repeat

Every row carries all of it. A partial row is discarded rather than patched.

**Identity**
- `model_file`, `model_sha256`, `model_parameters`, `quantization`
- `runtime_name`, `runtime_version`, `runtime_commit`, `runtime_build_flags`
- `harbor_version`, `harness_config_digest`

**Configuration**
- `context_cap`, `gpu_layers`, `offload_split`, `batch_size`, `concurrency`
- `sampling` — temperature, top-p, top-k, seed, repeat penalty, and whether
  decoding is greedy

**Hardware**
- `gpu_model`, `gpu_vram_total`, `cpu_model`, `system_ram_total`
- `os`, `kernel`, `driver_version`

**Observed**
- `peak_vram_bytes`, `peak_system_ram_bytes`
- `prompt_tokens_per_second`, `generation_tokens_per_second`
- `wall_clock_seconds` per trial, recorded as a distribution and not a mean
- `offload_transitions` — count, with the trial index of each
- `truncation_events` — count, with the trial index of each
- `failures` — each one typed: `oom`, `runtime_crash`, `harness_timeout`,
  `context_truncation`, `verifier_infrastructure`, `other` with a note
- `determinism_check` — `identical`, `divergent`, or `not_run`

## Hours per 100 trials

The first-class output. It sizes every later milestone and decides whether the
pilot is a three-day loop or a three-week one.

Derive it from **end-to-end trial wall clock on the probe set**, including
harness startup, verifier execution, and teardown — never from token rates. A
configuration generating 40 tok/s and spending 90 seconds per trial in container
setup is a slow configuration, and the tok/s number will hide that.

Report the median and the p90, not the mean. The p90 is what a batch of 100
actually costs, because the long tail is where the timeouts live.

## Outcome

One of three.

**A stable cell exists.** Freeze it. Write `ORGANISM.lock.json` with every
identity, configuration, and hardware field above, plus the observed envelope
it was accepted on and the hours-per-100-trials figure. Its digest is the
organism fingerprint every receipt carries. The file is written once and never
edited; a changed machine means a new lock file and a new fingerprint, and
receipts under the two are not pooled.

**No cell is stable.** The pilot does not run. This is a real result and it is
recorded as one. Lowering the stability bar to obtain a configuration converts
an unmeasurable setup into a measurement that reports noise as signal.

**A cell is stable but too slow.** Record hours-per-100-trials and take it to
the M0.0 power gate. If the trial count needed for the minimum detectable
effect cannot be run in the available time, PILOT-0001 is underpowered before
it starts, and the honest move is to shrink the question rather than the
sample.

## Producing the lock file

`ORGANISM.template.json` is the shape. Fill every field — placeholders are
refused — and validate:

```bash
python -c "
import sys; sys.path.insert(0, 'experiment')
from evidence import load_organism
print(load_organism('experiment/M-1/ORGANISM.lock.json').fingerprint)
"
```

The printed digest goes into every receipt as `organism_fingerprint`. The
loader refuses a lock file with an unfilled field, because a fingerprint over
placeholders is a fingerprint that certifies nothing while looking exactly like
one that does.
