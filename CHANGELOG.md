# Changelog

Versions are aligned across `SKILL.md`, `README.md`, `pyproject.toml`, and `CONTEXT.template.md`; `tests/test_release.py` enforces it.

## Unreleased

- **The envelope milestone described a probe nobody could run twice the same
  way.** M−1 said to record peak VRAM, throughput, and offload events and to
  freeze the winning configuration, which is a summary of a protocol rather than
  one. `experiment/M-1/PROTOCOL.md` now states which factors vary and which are
  held constant, defines stability *before* the probe runs (no offload
  transition mid-run, no truncation, no hard failures, peak memory within 5%
  across repeats, throughput CV ≤ 0.15), records determinism rather than
  requiring it, derives hours-per-100-trials from end-to-end wall clock rather
  than token rates, and names "no stable cell exists" as a result instead of a
  reason to lower the bar. The probe set is drawn from tasks explicitly excluded
  from the pilot, because tuning against tasks the pilot will score is selection
  on the outcome. `evidence/organism.py` makes the output executable: the
  fingerprint is computed from identity, configuration, and hardware, the
  observed envelope is recorded but deliberately not hashed, and a lock file
  with any field still a placeholder is refused — a fingerprint over an unfilled
  form certifies nothing while looking exactly like one that does.

- **The contribution rules had no lane the experiment could enter through.**
  Attack, Fix, and Skill text all require a residual from real use, and rule 8
  requires a trace that could not be served without the change — but producing
  the first trace is what the measurement work exists to do, so every research
  PR had to argue its way past rules written for a released discipline. A fourth
  lane now carries its own: treatment before implementation, preregistration
  before confirmatory data, raw evidence never rewritten, experimental code
  never implying promotion, the payload boundary enforced by test rather than
  asserted, and cross-boundary imports declared in the importing module with
  their direction. The PR shape gains `experiment` as a layer and a `Promotes:`
  line whose honest answer is almost always `no`.

- **The experiment/release boundary was a claim in a document, not a fact about
  the filesystem.** `ROADMAP.md` said `experiment/` is outside the installed
  skill, but `install.py` copies all of `runtime/`, the pilot adapter lived at
  `runtime/howdo/environment.py`, and `howdo.__init__` re-exported twelve pilot
  symbols — so every install carried the adapter and the release surface
  silently included it. The adapter moved to
  `experiment/PILOT-0001/adapter/`, the exports are gone, and the boundary is
  now enforced: `tests/test_release.py` installs into a temporary directory and
  checks that no pilot module ships, that a clean interpreter importing the
  installed `howdo` finds none of the pilot API, and that no payload file so
  much as names the pilot. Kind-awareness stays in `context.py` because
  `inspect_context()` needs it, and it is generic — it validates whichever kind
  a file declares and names no consumer.

- **A benchmark agent cannot honestly hold a person's context, so it gets a
  different kind.** `CONTEXT.template.md` says a pedagogy "cannot be generated"
  because it has no source but the person, and the required evidence sections
  record how one person builds understanding. A benchmark agent has no person,
  so synthesizing a context for it would fabricate exactly the evidence
  `complete_onboarding()` exists to require — and completion is structural, so
  the fake would pass and certify nothing. `context_kind: person | environment`
  now splits the two, defaulting to `person` when absent so every existing
  context behaves as before. The validators are disjoint: the settlement key
  differs (`onboarding` versus `reconnaissance`) and the evidence sections do
  not overlap, so relabelling one kind as the other fails on both, and each
  settlement helper refuses the other's file with `ContextKindError`. Lifetime
  and write authority are orthogonal to kind, so `environment` never silently
  implies `ephemeral`. Nothing in the shipped discipline refers to it and no
  version moved.

- **A trial's resolution is the one thing a receipt cannot recompute.** The
  benchmark experiment derives everything it can from evidence — capability
  edges, interaction claims, the skill graph itself are projections over
  receipts. Which operands were composed, in what order, by which resolver is
  not derivable: it exists only while the container does. `experiment/evidence/
  resolution.py` freezes that block and nothing more, with a digest over
  canonical JSON rather than concatenated context digests, so arity and role
  are committed and a crafted identity cannot impersonate the surrounding
  syntax. `experiment/CROSSINGS.md` records why the rest — the `×`, `-`, `/`,
  `+` vocabulary — is analysis language kept deliberately out of storage.

- **The experiment has a written progression instead of a remembered one.**
  The milestone ordering, what each one must produce, the stopping gate, and
  the open decisions lived only in discussion. `experiment/ROADMAP.md` records
  them with status, including the two documents still unwritten
  (`PREREGISTRATION.md`, the rest of the receipt) and the undeclared values
  (reconnaissance budget, δ\*) that block the pilot.

- **The installer tells the person what is being configured.** A fresh install
  printed `next  establish the pedagogy before the first substantive HowDo` — an
  instruction addressed to an agent who is not reading it, shown to a person, in
  a term nothing on their path had defined. Nothing told them what the first
  conversation is for, why it cannot be guessed, or that it can be declined or
  deferred. `install.py` now prints a `CONFIGURATION_NOTE` after the status
  block on a fresh install only, carrying all four settings and both opt-outs in
  plain ASCII; `--verify` stays terse and prints none of it, and a reinstall over
  a settled context has nothing to explain. The `next` line no longer uses the
  internal term. `QUICKSTART.md` now leads with what gets configured, mapped
  stage by stage, before the store mechanics.

- **The shell is fixed, its internals are personal, and both halves are stated
  wherever the term is introduced.** `SKILL.md` called a pedagogy "how
  understanding gets built for this person"; `references/onboarding.md` called it
  "the loop itself". Both are true, and the join was stated in one place, on the
  line a reader reaches last — so onboarding read either as an agent inventing a
  pedagogy per reader or as an impersonal config step with nothing a person could
  supply. `SKILL.md`, `CONTEXT.template.md`, and `references/onboarding.md` now
  each carry the loop as a fixed shell, its internals as personal, and the reason
  a person is required: the settings have no other source.
- **The vocabulary is working equipment, not output.** Nothing forbade emitting
  the local terms, state names, frontmatter keys, or store paths at the person.
  Guide mode was told it "does not need" the vocabulary — permission to skip,
  rather than an instruction to withhold — and the one rule about what shows
  through an answer governs structure, not wording. `SKILL.md` now states the
  rule and names what leaks most readily, with two narrow exceptions (inspect
  mode, and working on How Do itself); `references/onboarding.md` carries it
  beside the anti-label bullet, where it bites hardest.
- **The glossary defines the words a newcomer trips over first.**
  `references/vocabulary.md` was silently missing `pedagogy`, `onboarding`,
  `exemplar`, `payload`, and `store`, plus the new `shell` and `internals`.

- **The default-store test pins the platform it asserts.** `default_store_path()`
  documents and implements `%APPDATA%\howdo\CONTEXT.md` on Windows and
  `~/.howdo/CONTEXT.md` elsewhere, but
  `test_default_store_is_user_scoped_and_keeps_the_canonical_basename` passed no
  `platform=` and asserted the POSIX branch unconditionally — so it agreed with
  whatever host ran it, and stayed green on Linux-only CI while proving nothing
  about Windows. All three branches are now asserted through `subTest` with
  `platform` pinned per case.

## 0.8.0

- **A reading has to be tested before it settles.** Restructuring onboarding
  into objectives dropped the contrast pass and stopped at "you can name one
  thing that helps" — formation, not testing, which would let an agent settle a
  hypothesis it never checked. The stopping rule now requires a reading that
  survived contact: predict from it, render something that way, look at what
  comes back. How you test stays free. Observations also record what tested
  them, because "they said so" and "it predicted correctly" should not read the
  same to whoever picks the file up next — especially since the exemplar is
  reused where nobody can catch it being wrong.
- **`Look` is defined as running the test `Check` wrote.** The word is unchanged;
  its definition now carries the weight. `Check` states the observable
  postcondition — it writes the test. `Look` takes in the actual result and runs
  that test against it; the difference, observed minus expected, is the residual.
  The old wording ("inspect what actually happened, not merely what the model
  said") was a testing instruction wearing an observing word, and a step that
  only reads back what was reported has not run the test.
- **The pedagogy is the loop, and onboarding tunes it.** `Map` is the domain and
  its priors, `Path` sequences it, `Check` states what would count as understood,
  `Do` teaches, `Look` tests against that, `Update` revises the smallest
  disproved part. Onboarding does not invent a pedagogy; it establishes one
  person's settings for that loop, and each setting now names the stage it tunes.
  Those settings are learned from the person's preference for, and critique of,
  how information was presented — judged by whether it built understanding, not
  by whether they enjoyed it.
- **Onboarding establishes a pedagogy, and the agent chooses the route.** The
  seven-step comparative interview is replaced by what must end up established
  — anchors, build direction, what counts as understood, how correction should
  land — plus explicit latitude over how to get there: use the work the person
  brought, learn a dimension by doing it rather than asking, state an
  assumption and invite correction, or skip what the conversation already
  showed. The register is a conversation, never an intake form; ideally the
  person cannot tell an onboarding is happening. The structural receipt is
  unchanged — the route is free, the receipt is not.
- **The anchor domain's expertise requirement is now explained, not just stated.**
  What onboarding learns is saved as an exemplar — a reusable shape — whose
  purpose is to be applied to topics the person is *not* expert in. That is why
  it must be calibrated somewhere they are: a novice cannot separate "that was
  well built" from "I finally understood it", and calibrating there generalises
  what felt good while confused. Observations carry the scope they are expected
  to transfer to, and in the novice domain the burden of noticing a shape has
  stopped working falls entirely on the agent.
- Context section descriptions keep their preference-and-critique framing, which
  was correct — that is the mechanism by which the loop's settings are learned.
  What they were missing was the qualifier: preference and critique **judged by
  whether the presentation built understanding**, not by whether it was enjoyed.
  Made explicit in place; headings and the stored schema are untouched, so
  settled stores keep working.

Minor, not patch: this adds a value to the public `ContextState` enum, three
public helpers, and a frontmatter key. All additive — a store settled under
0.7.0 has no `scope` key, reads as `scope: user`, and settles unchanged.

- **CI exists.** `.github/workflows/tests.yml` runs the suite and the example on
  Python 3.10–3.13, and runs `install.py` end to end on Linux, macOS, and
  Windows, including a reinstall over a settled store. `CONTRIBUTING.md` claimed
  CI ran on push and pull request; until now that was not true.

- Instantiation strips the template's self-description, not just `template: true`.
  A store no longer carries prose telling its reader it cannot be settled.
- Store resolves to per-user application data by platform: `%APPDATA%\howdo\CONTEXT.md`
  on Windows, `~/.howdo/CONTEXT.md` elsewhere. Resolution depends only on
  configuration, never on disk state. New: `default_store_path()`.
- Context scope is explicit. `scope: user` is the default; `install.py --shared`
  opts into one generic install-wide store, which marks itself `scope: shared`
  and is the only kind allowed to live inside the payload. New: `is_shared()`.
- `SKILL.md` now names the store path, the helper call, and the hand-install
  fallback, so step 0 is executable from the skill file alone.
- Installs no longer copy `__pycache__`, bytecode, or other build noise.
- **`onboarding: deferred` is a first-class state.** Previously the only ways
  out of onboarding were finishing it or declining it outright, so a user who
  said "not now" had to be recorded as a refusal — permanently unlearned. A
  deferral leaves the offer open for a later session, opens a lineage so it can
  settle with the same `context_id`, and can still become a decline. A decline
  cannot be reopened by deferring. New: `defer_onboarding()`.
- **Detail moved to `references/`, loaded on demand.** The onboarding interview,
  store resolution, fork and scope rules move to `references/onboarding.md`; the
  vocabulary table to `references/vocabulary.md`. `SKILL.md` keeps the state
  routing and the three guarantees those details back — onboarding gates the
  first substantive HowDo, a decline is durable, completion is structural only —
  so a reference that is never read cannot take a guarantee with it.
- **Requested, not ambient.** The description no longer advertises `"help me"`,
  `"say more"`, `"do work"`, or bare how-to questions as triggers; it asks for
  an explicit invocation, the loop by name, or a request to work this way. The
  handles remain moves inside a HowDo already underway. Description compressed
  from 814 to 611 characters.

## 0.7.0
- **Template and context are separate types.** The shipped file is `CONTEXT.template.md`, marked `template: true`, with `inspect_context()` state `template`. It has no lineage, skips the fork check, is never `ready`, and is refused by `complete_onboarding()`, `decline_onboarding()`, and `fork_context()` (`TemplateContextError`). `ensure_context()` strips the marker when opening a store.
- Install separates the **replaceable payload** from the **durable store**: the payload is copied to `<skills-dir>/how-do/`, the context is instantiated at `$HOWDO_CONTEXT` or `~/.howdo/CONTEXT.md`, and reinstall never clobbers a settled store.
- `resolve_context_path()` and `ensure_context()` added; `ensure_context()` never overwrites an existing store.
- `complete_onboarding()` and `decline_onboarding()` refuse a target inside a skill payload (`PayloadContextError`) unless `allow_payload=True`. A receipt the install cannot keep is no longer written silently.
- `payload_root()` exposes the check: a directory shipping `SKILL.md` is payload.
- `install.py` installs, verifies, and names the directory from `name:` in the frontmatter rather than from the repo folder.

## 0.6.1
- `onboarding: declined` is a persisted state; `decline_onboarding()` added; a decline is not re-asked and is not learned context.
- `complete_onboarding()` refuses an already-ready context (no `context_id` churn) and preserves the id when reopening a declined context.
- Onboarding evidence strings are newline-sanitized; placeholder detection matches prefixes.
- SKILL.md states that structural completion is not proof of truthful evidence.

## 0.6.0
- Agency modifier: `How[actor]` binds `I / you / we / they` above the kernel; kernel records `Request.actor` only, no pronoun parsing.
- Durable-context readiness is structural: required frontmatter keys, required evidence sections, `complete_onboarding()`; missing lineage metadata is `invalid`, not silently ready.
- Comparative onboarding runs before the first substantive HowDo unless explicitly declined (reverts 0.5.1's lazy gate; enforced by a release test).

## 0.5.1
- `Request.mutates` defaults to `True` (opt out of contracts, not in).
- `Admission` is single-use; replay raises.
- `settle()` refuses a patch on an `invariant`-routed residual without explicit override.
- `Check.evaluate` fails closed on predicate exceptions.

## 0.5.0
- Protocol kernel with lineage: `resolve → admit → operate → observe → settle`, gate evidence provenance, stale-resolution fizzle, observer isolated from executor report, invariants evaluated before and after, one-layer settlement guard.
- `context.py`: `inspect_context()` / `fork_context()`; `ADVERSARIAL.md` records enforced vs declared.

## 0.4.0
- First reference runtime alongside the skill text.
