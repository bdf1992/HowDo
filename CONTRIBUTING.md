# Contributing to How Do

How Do is a small discipline (`Map → Path → Check → Do → Look → Update`) with a tiny reference kernel (`resolve → admit → operate → observe → settle`). Contributions follow the same discipline they touch: establish how, act through the gate, report the residual, update one layer.

Read `SKILL.md`, then `ADVERSARIAL.md`, before opening anything.

## What this is, and is not

The goalposts. Move one only with a residual from real use, never because a probe suggested it.

- It **is** a baseline discipline, a protocol kernel whose invariants are enforced by tests, and a durable-context lifecycle that is structurally checkable.
- It **is not** a trust boundary, an agent framework, an identity or custody system, a pronoun parser, or the interviewer. Anything the kernel cannot prove is written in `ADVERSARIAL.md` as a declared boundary, not hidden.
- The runtime must never become more complex than the work it protects.

## Three lanes

**Attack.** Reproduce a way the kernel or context module breaks a promise it makes. Open an issue with the shortest script that shows it (see `ADVERSARIAL.md` for the shape). An attack that only defeats a *declared* boundary is a doc issue, not a bug.

**Fix.** Close an attack. A kernel change ships with a test named for the invariant it protects (`test_admission_is_single_use`, not `test_fix_bug_12`), and `ADVERSARIAL.md` moves the row from declared to enforced, or adds it.

**Skill text.** Change `SKILL.md`, `CONTEXT.md`, or the examples. Justify with a trace: what request, which actor, what was rendered, what the residual was, which one layer it indicts.

## Rules that will block a merge

1. **No weakened invariant.** The rows under "Enforced" in `ADVERSARIAL.md` are the contract. A PR that makes any of them false is closed unless it replaces the guarantee with a stronger one and says so.
2. **One layer per PR.** Kernel, context module, or skill text; a residual points at one place. Cross-layer changes are split, or explained the way `settle(allow_multi_layer=True)` is: explicitly and with a reason.
3. **Tests target invariants.** Every kernel or context change adds or edits a test whose failure would mean the promise broke. Coverage of lines is not the point; coverage of promises is.
4. **Versions stay aligned.** `SKILL.md`, `README.md`, `pyproject.toml`, `CONTEXT.template.md`, `runtime/howdo/context.py`, and `CHANGELOG.md` move together. `tests/test_release.py` will tell you if they don't.
5. **Handles are earned, not added.** A new small-word handle is admissible only if it names a move over the paradigm and its residual is measurable, and it should arrive with the trace that earned it. The six in `SKILL.md` are a seed set, not a menu, and not the whole set.
6. **The actor is a modifier, not a fork.** `I / you / we / they` changes whose capability, authority, and evidence apply. It does not add a workflow, a loop, or a kernel branch.
7. **Contexts are personal, and live outside the payload.** The store is resolved by `resolve_context_path()` and instantiated by `ensure_context()`; the settlement helpers refuse a target inside a skill payload unless it declares `scope: shared` or the caller passes `allow_payload=True`. Never commit a settled `CONTEXT.md` or any fork of one. The tracked file is `CONTEXT.template.md` and must inspect as `template`; a test guards that and that no `CONTEXT.md` is tracked. `.gitignore` excludes `CONTEXT.md` and `CONTEXT.*.md`, negating the template. Respect a persisted `onboarding: declined`, and treat `onboarding: deferred` as an open offer rather than a refusal.
8. **No new subsystems without use.** Persistence backends, parsers, orchestration, hosting, plugin systems: proposals need a real HowDo trace that could not be served without them.

## Running the suite

```bash
python -m unittest discover -s tests -t . -v
python examples/jira_workflow.py
```

Zero dependencies; Python ≥ 3.10. `.github/workflows/tests.yml` runs the suite and the example on 3.10–3.13, and runs the installer end to end on Linux, macOS, and Windows — on every push and pull request.

## Pull request shape

Fill these in; short is fine, missing is not.

```
Layer:     kernel | context | skill-text | docs
Residual:  what broke, or what real use surfaced (link the issue or paste the trace)
Map:       the parts and relations this touches
Path:      what changed, in order
Check:     the test(s) that would fail if the promise broke
Declared:  any boundary added to or removed from ADVERSARIAL.md
```

Commit messages follow the same idea: name the invariant or the residual, not the file.

## Versioning

Patch (`0.x.y`): closes attacks, tightens wording, no new surface. Minor (`0.x.0`): a new capability that has earned its way in with a trace and tests, or a deliberate goalpost move recorded in `CHANGELOG.md` and enforced by a release test. There is no major version yet; the discipline hasn't been used enough to deserve one.

## Where to start

Don't start by probing the kernel; it's been probed. Start by running `how do I …` on something you actually need, with the actor bound and the receiver established out loud, and bring back the trace. That residual is worth more than any attack.
