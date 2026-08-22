# Contributing to How Do

How Do is a small discipline (`Map → Path → Check → Do → Look → Update`) with a tiny reference kernel (`resolve → admit → operate → observe → settle`). Contributions follow the same discipline they touch: establish how, act through the gate, report the residual, update one layer.

Read `plugin/SKILL.md`, then `ADVERSARIAL.md`, before opening anything.

## What this is, and is not

The goalposts. Move one only with a residual from real use, never because a probe suggested it.

- It **is** a baseline discipline, a protocol kernel whose invariants are enforced by tests, and a durable-context lifecycle that is structurally checkable.
- It **is not** a trust boundary, an agent framework, an identity or custody system, a pronoun parser, or the interviewer. Anything the kernel cannot prove is written in `ADVERSARIAL.md` as a declared boundary, not hidden.
- The runtime must never become more complex than the work it protects.

## Five lanes

**Attack.** Reproduce a way the kernel or context module breaks a promise it makes. Open an issue with the shortest script that shows it (see `ADVERSARIAL.md` for the shape). An attack that only defeats a *declared* boundary is a doc issue, not a bug.

**Fix.** Close an attack. A kernel change ships with a test named for the invariant it protects (`test_admission_is_single_use`, not `test_fix_bug_12`), and `ADVERSARIAL.md` moves the row from declared to enforced, or adds it.

**Skill text.** Change `plugin/SKILL.md`, `CONTEXT.md`, or the examples. Justify with a trace: what request, which actor, what was rendered, what the residual was, which one layer it indicts.

**Packaging.** Change how the payload is laid out, assembled, or distributed: `plugin/`, `.claude-plugin/`, `install.py`, `packaging/`, the `plugin:` CI job. This lane touches no discipline and no invariant — if a change here alters what the skill *says* or what the kernel *promises*, it is in the wrong lane. Its own rule: the boundary is the directory. Anything inside `plugin/` ships to every user by every route, anything outside it reaches nobody, and `tests/test_plugin.py` asserts both directions rather than trusting a list. `packaging/HANDOFF.md` carries the findings that were established against the runtime rather than the documentation; read it before changing a layout, because two of those findings contradict the published docs.

**Experiment.** Change anything under `experiment/`. This lane exists because measurement work does not obey the other three: it has no residual from real use yet — producing one is the whole point — and rule 8 cannot be satisfied by a trace that does not exist. It gets its own rules, below, and its own goalposts. Nothing in this lane is a How Do release, and code here never earns promotion by being well made.

## Rules that will block a merge

1. **No weakened invariant.** The rows under "Enforced" in `ADVERSARIAL.md` are the contract. A PR that makes any of them false is closed unless it replaces the guarantee with a stronger one and says so.
2. **One layer per PR.** Kernel, context module, or skill text; a residual points at one place. Cross-layer changes are split, or explained the way `settle(allow_multi_layer=True)` is: explicitly and with a reason.
3. **Tests target invariants.** Every kernel or context change adds or edits a test whose failure would mean the promise broke. Coverage of lines is not the point; coverage of promises is.
4. **Versions stay aligned.** Seven places move together: `plugin/SKILL.md`, `README.md`, `pyproject.toml`, `plugin/CONTEXT.template.md`, `plugin/runtime/howdo/context.py`, `plugin/QUICKSTART.md`, and `CHANGELOG.md`. `tests/test_release.py` pins the release in one literal and checks all seven against it, so a bump that reaches only some of them fails rather than shipping. Two places are deliberately *not* on that list: `plugin/.claude-plugin/plugin.json` derives its version from `SKILL.md` and is checked byte-for-byte against the derivation, and `.claude-plugin/marketplace.json` carries no version at all — a marketplace catalog versions itself, not the plugin inside it, and a number there would assert a coupling nothing maintains.
5. **Handles are earned, not added.** A new small-word handle is admissible only if it names a move over the paradigm and its residual is measurable, and it should arrive with the trace that earned it. The six in `plugin/SKILL.md` are a seed set, not a menu, and not the whole set.
6. **The actor is a modifier, not a fork.** `I / you / we / they` changes whose capability, authority, and evidence apply. It does not add a workflow, a loop, or a kernel branch.
7. **Contexts are personal, and live outside the payload.** The store is resolved by `resolve_context_path()` and instantiated by `ensure_context()`; the settlement helpers refuse a target inside a skill payload unless it declares `scope: shared` or the caller passes `allow_payload=True`. Never commit a settled `CONTEXT.md` or any fork of one. The tracked file is `CONTEXT.template.md` and must inspect as `template`; a test guards that and that no `CONTEXT.md` is tracked. `.gitignore` excludes `CONTEXT.md` and `CONTEXT.*.md`, negating the template. Respect a persisted `onboarding: declined`, and treat `onboarding: deferred` as an open offer rather than a refusal.
8. **No new subsystems without use.** Persistence backends, parsers, orchestration, hosting, plugin systems: proposals need a real HowDo trace that could not be served without them.

### Rules for the experiment lane

These replace rule 8 inside `experiment/` and add to the rest. Rules 1, 3, and 4 still apply unchanged: an experiment PR may not falsify an enforced row, must test the promise it makes, and may not drift the release version.

9. **Treatment before implementation.** What is being administered is written and frozen before the code that administers it. An adapter built first will define the treatment by accident, and the definition will be whatever was convenient to build.
10. **Preregistration before confirmatory data.** No confirmatory trial runs before `PREREGISTRATION.md` names the endpoints, the analysis, the effect threshold, and the STOP condition. Analysis chosen after results are visible is exploratory, and must be labelled exploratory in the writeup. Adding an endpoint after seeing the data is not a fix.
11. **Raw evidence is never rewritten.** Receipts are append-only. A wrong receipt is corrected by appending a correction that references it, never by editing or deleting it. A PR that mutates historical evidence is closed regardless of what it fixes.
12. **Experimental code does not imply skill promotion.** Landing on the experiment branch grants nothing. Promotion into `plugin/runtime/` or `plugin/SKILL.md` requires evidence that the discipline changed an outcome, and is a separate PR in a separate lane. "The implementation is clean" is not evidence.
13. **The payload boundary is enforced, not asserted.** The payload *is* `plugin/`, so `experiment/` sitting outside it is the enforcement rather than a rule the installer remembers; no payload file may name a specific experiment either. `tests/test_release.py` checks this by installing into a temporary directory.
14. **Cross-boundary dependencies are explicit or refused.** Experiment code may import from `plugin/runtime/howdo`; the reverse never happens. Where an experiment module depends on kernel internals, its docstring states the dependency and its direction, so that a later kernel change breaks the experiment loudly rather than the skill silently. A change to `plugin/runtime/` made *for* the experiment is a cross-layer PR under rule 2 and must say so.

## Running the suite

```bash
python -m unittest discover -s tests -t . -v
python plugin/examples/jira_workflow.py
```

Zero dependencies; Python ≥ 3.10. `.github/workflows/tests.yml` runs the suite and the example on 3.10–3.13, and runs the installer end to end on Linux, macOS, and Windows — on every push and pull request.

## Pull request shape

Fill these in; short is fine, missing is not.

```
Layer:     kernel | context | skill-text | docs | packaging | experiment
Residual:  what broke, or what real use surfaced (link the issue or paste the trace)
           (experiment lane: what the change makes measurable, or what it stops
            the measurement from being able to claim)
Map:       the parts and relations this touches
Path:      what changed, in order
Check:     the test(s) that would fail if the promise broke
Declared:  any boundary added to or removed from ADVERSARIAL.md
Promotes:  experiment lane only — `no`, or the evidence that earns it
```

Commit messages follow the same idea: name the invariant or the residual, not the file.

## Versioning

Patch (`0.x.y`): closes attacks, tightens wording, no new surface. Minor (`0.x.0`): a new capability that has earned its way in with a trace and tests, or a deliberate goalpost move recorded in `CHANGELOG.md` and enforced by a release test.

**1.0 is reserved for the Skill Graph.** It is not held back for lack of polish, and packaging maturity does not reach it: 0.10.0 ships How Do as an installable plugin, which is a new capability with a trace and tests — a minor by the definition above — and says nothing about whether the discipline works. That question belongs to `experiment/ROADMAP.md`, which holds that every further edit to the skill is unfalsifiable until something measures it, and PILOT-0001 has not run. A release that made the plugin sound like a maturity claim would be borrowing confidence the measurement has not supplied.

## Where to start

Don't start by probing the kernel; it's been probed. Start by running `how do I …` on something you actually need, with the actor bound and the receiver established out loud, and bring back the trace. That residual is worth more than any attack.
