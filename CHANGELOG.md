# Changelog

Versions are aligned across `plugin/SKILL.md`, `README.md`, `pyproject.toml`, and `plugin/CONTEXT.template.md`; `tests/test_release.py` enforces it.

## 0.10.0

- **The one escape hatch in the payload guard described a trade the plugin route
  does not offer.** `_refuse_payload_settlement` lets a store through when it
  declares `scope: shared`, on the stated grounds that whoever declared it
  "accepted that a wholesale reinstall discards it". That is true of a skill
  directory, which is replaced in place. It is false of a plugin: hosts install
  under a directory named for the release, so an update does not touch the old
  one — it creates a new one beside it and reads from there. The store is not
  discarded, it is **orphaned**: still on disk, still readable, and no longer the
  file anything loads. Nothing raises and nothing goes missing, which makes it
  strictly worse than deletion for a durable context and impossible to opt into
  knowingly. `is_plugin_payload()` now tells the two kinds apart by the manifest
  a plugin root ships and a skill directory never does, and a `scope: shared`
  settlement inside a plugin payload raises instead, naming
  `$CLAUDE_PLUGIN_DATA` as where the store belongs. A skill directory is
  unchanged, and an explicit `allow_payload=True` still overrides — a caller who
  states the risk is not the accident being guarded against. This strengthens an
  existing guarantee rather than weakening one, per rule 1, and the new row in
  `ADVERSARIAL.md` says so.

- **Four of seven version strings were unchecked, and a release is what would
  have found that out.** `test_release_versions_are_aligned` verified
  `SKILL.md`, `README.md`, `pyproject.toml`, `CONTEXT.template.md` and
  `CHANGELOG.md`. It never checked `runtime/howdo/context.py`, whose
  `SKILL_VERSION` stamps `skill_version` into every context the runtime writes
  — a constant CONTRIBUTING rule 4 already listed as one that must move with the
  rest, so the rule was right and only the test was behind — nor the quickstart
  title. A bump could reach four places, pass CI, and ship contexts stamped with
  the previous release. The test now pins the release in one literal and checks
  all seven against it. The plugin manifest is checked separately because it is
  derived rather than typed, and `.claude-plugin/marketplace.json` now carries
  no version at all: a marketplace catalog versions itself, not the plugin
  inside it, and a number there asserted a coupling nothing maintained.

- **Two shipped documents told the reader to run a file the plugin does not
  ship.** `QUICKSTART.md` and `references/onboarding.md` both pointed at
  `python install.py --shared` to opt into a generic store. For a marketplace
  user that command does not exist, and the advice was worse than unreachable:
  a plugin payload is *version-scoped*, so a shared store settled inside it is
  discarded by the next release rather than merely replaced — precisely the loss
  the store design exists to prevent. Both now say how the opt-in differs by
  install route, and that under a plugin the store belongs at a path the host
  does not replace. A test fails on any shipped document that carries a runnable
  `install.py` command, because naming the other route in prose is fine and
  handing someone a command to copy is not.

- **Packaging was a lane in practice and absent from the rules.** It has a
  handoff, a CI job, a directory boundary and its own findings, while
  `CONTRIBUTING.md` named four lanes and offered no `Layer:` value for it — so
  every packaging change had to misfile itself as docs. It is now the fifth
  lane, with the rule that makes it different: the boundary is the directory,
  and anything inside `plugin/` reaches every user by every route.

- **A plugin nobody can install is not packaged.** The plugin root was
  generated into `dist/`, which is gitignored, so `/plugin install` had nothing
  to clone and the packaging lane could not close parity. The payload now lives
  at `plugin/` as a committed plugin root — `SKILL.md`, `CONTEXT.template.md`,
  `QUICKSTART.md`, `LICENSE`, `references/`, `runtime/`, `examples/` and `bin/`,
  with `.claude-plugin/plugin.json` in it and `.claude-plugin/marketplace.json`
  at the repository root pointing there. The move is what makes the boundary
  real rather than remembered: `experiment/`, `tests/`, `packaging/` and the
  contributor docs sit outside the payload directory and cannot reach a user by
  any route, where before they were kept out by an assembler consulting a list.
  `install.py` gains `PAYLOAD_ROOT` and nothing else changes about it; `PAYLOAD`
  still names what an *ordinary skill directory* receives, which is the plugin
  root minus `bin/` and the manifest, because a skill directory is not a plugin
  and a host that found a manifest in one would be right to be confused. The
  invocation is unchanged and that was verified rather than assumed: a headless
  probe of `claude --plugin-dir plugin` returns `/how-do`, so a directory named
  `plugin` still loads under the name its manifest declares.

- **A committed derived file is a file that can go stale.** The manifest is now
  in the tree, but `packaging/plugin.json` still carries no version and
  `SKILL.md` is still the only place a version is authored. `install.py`
  exposes the derivation as `manifest_bytes()`, and a test compares the
  committed manifest to it byte-for-byte rather than field-by-field, so the fix
  for a failure is mechanical — overwrite the file with what the function
  returns — instead of a judgement call about which of two plausible files is
  right. The same reasoning covers `plugin/LICENSE`, which a payload needs and a
  repository root also needs: two real copies checked equal by test, because a
  symlink would ship its own link text as the licence on a Windows checkout.

- **The host already guarantees what `install.py` was built by hand to
  provide.** Almost all of the installer exists to keep `CONTEXT.md` out of the
  payload, because the payload is replaced on update and a context settled
  inside it is discarded with no error raised. A plugin host declares
  `$CLAUDE_PLUGIN_DATA`, a directory contracted to survive updates — the same
  guarantee, enforced by the host rather than detected after the fact. It now
  sits in the store precedence between `$HOWDO_CONTEXT` and the platform
  default: below the environment variable, so installing the plugin never
  relocates a store somebody already placed, and above the platform default,
  so a host that states its own directory is believed over one this repository
  guesses. Absent the variable, resolution is byte-for-byte what it was.

- **How Do can be installed as a plugin, and it is still `/how-do`.**
  `install.py --plugin DIR` lays the same payload out as a plugin root: a
  `.claude-plugin/plugin.json` derived from `packaging/plugin.json`, plus
  `bin/`. `SKILL.md` stays at the root rather than moving under `skills/`,
  which is what keeps the invocation un-namespaced — verified against the
  runtime, not the documentation, which claims the frontmatter `name` decides
  it. It does not: a root-`SKILL.md` plugin is invoked by the *plugin* name, so
  a `skills/how-do/` layout would silently rename the skill to `/how-do:how-do`
  and break the string the description promises and `test_release.py` asserts.
  The manifest carries no version of its own; the assembler reads it from
  `SKILL.md`, so release alignment stays at four places rather than five.

- **The onboarding helper is addressable from anywhere.**
  `references/onboarding.md` told the agent to run a `sys.path` insert against
  the relative path `runtime`, which resolves only when the process happens to
  be sitting in the payload. `bin/howdo-context` reports, resolves, and
  instantiates the store with no such requirement; a plugin host puts `bin/` on
  the shell `PATH` while the plugin is enabled. `howdo-context.cmd` ships
  beside it because an extensionless file with a shebang is not executable on
  Windows, and this project branches the store location on Windows explicitly
  enough that a POSIX-only affordance would be a real gap rather than a
  cosmetic one.

- **Parity is tested in both directions.** `tests/test_plugin.py` asserts the
  plugin root contains everything an ordinary install contains and nothing
  beyond the manifest and `bin/`, comparing against `install.copy_payload`
  rather than a second hand-maintained file list — two install paths fail by
  drifting, and a payload rule enforced on one path and absent on the other is
  the shape that failure takes. One check is skipped rather than passing: the
  assembled plugin still names PILOT-0001, because `runtime/howdo/environment.py`
  is the pilot adapter and every install path carries it. Moving it out of the
  payload is separate work in flight; the check activates itself when it lands.
- **A request's I/O was implied, so it was neither checkable nor portable.** The
  kernel refuses a consequential operation with no expected state and no
  precondition, but it never knew what that expected state was *shaped* like,
  what the operation read, or what a host had to be able to do before the
  operation was runnable there at all. Those three lived in the caller's head
  and in Python closures, which meant they could not be checked and could not
  leave the process. `runtime/howdo/contract.py` states them as data: `accepts`
  (declared inputs, now carried on `Request.inputs` and reaching the executor on
  the resolution instead of through a closure), `expects` (the shape of the
  observable result), `rules` (checks as clauses over a closed operator set,
  compiling into ordinary `Check` objects so the gate is the same one), and
  `requires` (capabilities a host must offer). A contract round-trips through
  JSON and digests to a stable identity, and `bind(contract, host)` answers
  *can this run here* before anything resolves. A consequential contract must
  carry its own precondition and its own result shape, because a gate the host
  happened to supply is not part of what shipped. One new route: an observation
  that does not match the declared shape is a `contract` residual, not a
  `postcondition` one — a result that cannot be compared is a different fault
  from one that came out wrong, and filing it as the latter claims a test ran
  that did not. Optional, additive, and no invariant above it moved.

- **The host already guarantees what `install.py` was built by hand to
  provide.** Almost all of the installer exists to keep `CONTEXT.md` out of the
  payload, because the payload is replaced on update and a context settled
  inside it is discarded with no error raised. A plugin host declares
  `$CLAUDE_PLUGIN_DATA`, a directory contracted to survive updates — the same
  guarantee, enforced by the host rather than detected after the fact. It now
  sits in the store precedence between `$HOWDO_CONTEXT` and the platform
  default: below the environment variable, so installing the plugin never
  relocates a store somebody already placed, and above the platform default,
  so a host that states its own directory is believed over one this repository
  guesses. Absent the variable, resolution is byte-for-byte what it was.

- **How Do can be installed as a plugin, and it is still `/how-do`.**
  `install.py --plugin DIR` lays the same payload out as a plugin root: a
  `.claude-plugin/plugin.json` derived from `packaging/plugin.json`, plus
  `bin/`. `SKILL.md` stays at the root rather than moving under `skills/`,
  which is what keeps the invocation un-namespaced — verified against the
  runtime, not the documentation, which claims the frontmatter `name` decides
  it. It does not: a root-`SKILL.md` plugin is invoked by the *plugin* name, so
  a `skills/how-do/` layout would silently rename the skill to `/how-do:how-do`
  and break the string the description promises and `test_release.py` asserts.
  The manifest carries no version of its own; the assembler reads it from
  `SKILL.md`, so release alignment stays at four places rather than five.

- **The onboarding helper is addressable from anywhere.**
  `references/onboarding.md` told the agent to run a `sys.path` insert against
  the relative path `runtime`, which resolves only when the process happens to
  be sitting in the payload. `bin/howdo-context` reports, resolves, and
  instantiates the store with no such requirement; a plugin host puts `bin/` on
  the shell `PATH` while the plugin is enabled. `howdo-context.cmd` ships
  beside it because an extensionless file with a shebang is not executable on
  Windows, and this project branches the store location on Windows explicitly
  enough that a POSIX-only affordance would be a real gap rather than a
  cosmetic one.

- **Parity is tested in both directions.** `tests/test_plugin.py` asserts the
  plugin root contains everything an ordinary install contains and nothing
  beyond the manifest and `bin/`, comparing against `install.copy_payload`
  rather than a second hand-maintained file list — two install paths fail by
  drifting, and a payload rule enforced on one path and absent on the other is
  the shape that failure takes. One check is skipped rather than passing: the
  assembled plugin still names PILOT-0001, because `runtime/howdo/environment.py`
  is the pilot adapter and every install path carries it. Moving it out of the
  payload is separate work in flight; the check activates itself when it lands.

- **Writing the analysis before the data caught two defects in the stopping
  rule.** `experiment/analysis/pilot0001.py` is the committed analysis — a
  task-level permutation test and bootstrap, seeded, zero dependencies —
  written and validated against synthetic trials with a known effect before any
  real trial exists. Running it against synthetic nulls immediately falsified
  two rules that had read as obviously sensible in prose. The first: STOP was
  defined as "the interval includes zero and its upper bound is below δ\*",
  which sends a real-but-too-small effect to INCONCLUSIVE when it is in fact
  conclusive; STOP is now simply an upper bound below δ\*. The second: harm was
  drafted as a gate at 20% of tasks regressing, but with single-digit
  trials-per-arm one trial is worth more than δ\* of a per-task pass rate, so
  30–40% of tasks regress by at least δ\* under a true null — the ceiling would
  have fired on nothing at all, and on a genuine positive too. Harm is now
  computed at the δ\* threshold, reported, and flagged for investigation, and
  the protection against a treatment that lifts the mean while breaking tasks
  comes from GO requiring the interval's lower bound to clear δ\*.
  `PILOT-0001/SIZING.md` records what the analysis does on synthetic data and
  states why every figure in it is optimistic; its useful finding is that tasks
  buy more precision than trials do, because the task is the unit of analysis.
  `PILOT-0001/REHEARSAL.md` and `PILOT-0001/RESULTS.template.md` complete the
  operational set: exercise the machinery on excluded tasks and throw the
  results away, then write the preregistered result before anything exploratory
  by document order.

- **The pilot had a frozen treatment and no committed study.** `TREATMENT.md`
  said what would be administered; nothing said what would count as an effect,
  which tasks would be committed, how many trials, what analysis, or what result
  would stop the programme. `PILOT-0001/PREREGISTRATION.md` now does, and it is
  frozen in two stages so that the parts M0.0 must not influence — endpoints,
  analysis, δ\*, the stopping rule — are fixed before M0.0 runs, while the task
  set and trial count are filled from its output. It declares its own screening
  bias rather than leaving it to be discovered: selecting tasks on the control
  arm's mid-range performance means the pilot estimates an effect on tasks a raw
  agent finds neither trivial nor impossible, not on the suite. INCONCLUSIVE
  is defined as not a soft GO, and a null is recorded as falsifying this
  treatment and not the discipline, because the person-derived half is in no
  arm. `PILOT-0001/RUNBOOK.md` makes the study executable without midstream
  judgement: pre-run gates, the per-trial lifecycle ending in destruction, a
  disposition table to look up rather than decide, and integrity checks ordered
  before anyone looks at the difference. `evidence/preregistration.py` refuses to
  digest a document with an open commitment, so the four values still awaiting a
  decision — the task variance ceiling, δ\*, the reconnaissance budget, and the
  harm-rate ceiling — block a confirmatory trial rather than defaulting quietly.

- **Nothing said which benchmark tasks were allowed to be evidence.** Two kinds
  of unqualified task bias a study rather than blurring it: one nothing can
  solve scores zero in every arm and shrinks the effective sample while the task
  count says otherwise, and one that passes without being solved scores one in
  every arm and pulls a real effect toward zero. Both look ordinary in an
  aggregate score. `experiment/TASK-QUALIFICATION.md` is the procedure — oracle
  run five times because a 4/5 indicts the fixture rather than the solution, a
  no-op agent run three times where a single pass disqualifies outright,
  verifier type recorded, and a 20% infrastructure-flake cap because the
  exclusions a flaky task produces are decisions made after the data is visible.
  `experiment/evidence/qualification.py` derives the outcome from the counts and
  refuses to let it be asserted, so a record edited to promote a rejected task
  fails verification even with its digest recomputed. Judge-scored tasks come
  out `research_only`: they inform the census and exploratory analysis and never
  certify. Rejections stay in the record, because deleting them turns a
  committed set into a selected one.

- **The receipt was one frozen block and a list of field names.** Everything
  the programme will claim is a projection over receipts, so a field the receipt
  omits is evidence that does not exist — but only the resolution block had a
  shape, and the rest was a bullet list in the roadmap.
  `experiment/evidence/RECEIPT.md` is now the contract and
  `experiment/evidence/receipt.py` enforces the checkable half. The invariants
  are the ones that otherwise produce evidence that looks correct and is not:
  certification is derived from verifier kind, analysis class, and result rather
  than written, and is rechecked at verification time so a hand-edited receipt
  fails even with its digest recomputed; `failure_class` is required exactly
  when a trial did not measure the treatment and refused when it did, so an
  inconvenient result cannot be refiled as infrastructure noise; a confirmatory
  trial with no preregistration digest in force is refused; the H0 arm cannot
  report reconnaissance and the treatment arms cannot report its absence;
  trajectories and artifacts must be content addresses, since a path is a claim
  about a machine that will be reformatted; and appends refuse an out-of-order
  `run_sequence_index`, because interleaving is the defence against drift and it
  is unverifiable from a log that accepted trials in any order. Corrections are
  appended against a receipt's digest and never replace it. The contract also
  states what it does not enforce — chiefly that no structural check can tell a
  receipt saying `arm: h1` from a harness that ran H0.

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

- **Every skill the emitter produced was unloadable, and so was this one.** A
  plain YAML scalar may not contain `": "`, and a generated description always
  does — "not a general-purpose helper: an unrelated question ...". So did this
  repo's own `SKILL.md`, whose description has read "requested, not ambient: use
  when ..." since 0.8.0. Claude Code's reader is lenient enough to have hidden
  it; the paths that are not — claude.ai upload, the Skills API,
  `package_skill.py` — validate the block and fail with a hard error. Frontmatter
  values are now quoted unconditionally rather than when a scan believes it is
  needed, this repo's own description is quoted, and
  `FrontmatterIsParseableTests` checks both without adding a dependency. Found by
  giving the generated output to a real parser instead of reading it.

- **Emission had one frontmatter target where there are two.** Outside Claude
  Code only six fields are accepted and any other key is a hard error, while
  inside it every documented field works. `render_skill` now takes
  `target="spec"` (the default, restricted to `name`, `description`, `license`,
  `compatibility`, `metadata`, `allowed-tools`) or `target="claude-code"`. The
  distinction is not bookkeeping: a domain-how whose contract is consequential
  describes an operation with side effects, which is the documented case for
  `disable-model-invocation: true` — "workflows with side effects or that you
  want to control timing, like `/commit`, `/deploy`" — and also this
  discipline's own posture. Consequential artifacts emitted for Claude Code are
  therefore not left auto-invocable. The portable target cannot say it, states
  it in the body instead, and that limit is declared in `ADVERSARIAL.md` rather
  than papered over.

- **Two spec fields were being left on the floor.** `license` is emitted when the
  caller supplies one — the issuer knows how an artifact was produced, not what
  covers the domain knowledge in it — and a contract's `requires` now becomes the
  `compatibility` statement, which is what that field is for, capped at the
  specification's 500 characters.

## 0.9.0

Two capabilities, one arc: a request's declared I/O becomes portable, and a run
that used it can leave a durable artifact behind. A deliberate goalpost move —
`CONTRIBUTING.md` rule 8 asks for a trace before a persistence subsystem, and
this one was requested rather than earned that way. Recorded here as the rule
requires.

- **A request's I/O was implied, so it was neither checkable nor portable.** The
  kernel refuses a consequential operation with no expected state and no
  precondition, but it never knew what that expected state was *shaped* like,
  what the operation read, or what a host had to be able to do before the
  operation was runnable there at all. Those three lived in the caller's head
  and in Python closures: uncheckable, and unable to leave the process.
  `runtime/howdo/contract.py` states them as data — `accepts` (declared inputs,
  now carried on `Request.inputs` and reaching the executor on the resolution
  instead of through a closure), `expects` (the shape of the observable result),
  `rules` (checks as clauses over a closed operator set, compiling into ordinary
  `Check` objects so the gate is the same one), and `requires` (capabilities a
  host must offer). A contract round-trips through JSON, digests to a stable
  identity, and `bind(contract, host)` answers *can this run here* before
  anything resolves. A consequential contract must carry its own precondition
  and result shape, because a gate the host happened to supply is not part of
  what shipped. One new route: an observation that does not match the declared
  shape is a `contract` residual, not a `postcondition` one — a result that
  cannot be compared is a different fault from one that came out wrong.

- **The discipline described its artifacts and minted only a pedagogy.**
  `SKILL.md` has always promised a domain-how — "one file per recurring concern:
  map, path, consequential contracts, invariants, one worked example, and
  revision" — and nothing ever wrote one. `CONTEXT.md` was the sole durable
  artifact, and it is explicitly barred from carrying domain facts, so a
  person's domain work left no trace at all. `runtime/howdo/domain.py` issues
  that file and indexes it. It is minted from a run that happened rather than
  from a plan; it stays `untested` until a residual that *matched* grounds it;
  a revision drops the grounding its predecessor earned, so an edited map cannot
  inherit evidence about the old one; and the index is rebuilt from the
  artifacts it describes rather than trusted as a second authority, following
  the rule `experiment/CROSSINGS.md` already set for the skill graph. Artifacts
  live beside `CONTEXT.md` in the store, outside the payload, because a
  domain-how settled inside the skill is discarded by the next install with no
  error raised — the failure the context lifecycle already had, one level down.
  `staleness()` closes the gap the kernel cannot: `admit` fizzles a stale
  resolution, but that protection ends at the process boundary, so a grounded
  artifact records the paradigm revision it was observed against.

- **An artifact nothing can load is still only a description.** A domain-how is
  durable and indexed, but a host loads Agent Skills and workflow scripts, not
  JSON in a store. `runtime/howdo/emit.py` renders an issued artifact into
  either: a `SKILL.md` bundle conforming to the Agent Skills specification
  (name projected to the legal charset and capped, description capped and
  written so the generated skill is requested rather than ambient, frontmatter
  stripped of angle brackets), or a dynamic-workflow script for
  `.claude/workflows/` whose structure is the loop — `Check` establishes the
  gate and fizzles if it cannot, `Do` runs the path as phases, `Look` observes
  the world instead of reading back the acting agents' reports. Values are
  emitted as JSON literals so a map containing quotes, backticks or `${...}`
  cannot break the script, and the suite parses the output with `node --check`.
  Emission is stateless and derived: re-emit rather than editing what came out.
  An untested artifact is refused without an explicit override, and the override
  stamps the output, because an installed skill pre-loads every later session on
  that concern.

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
