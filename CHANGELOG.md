# Changelog

Versions are aligned across `SKILL.md`, `README.md`, `pyproject.toml`, and `CONTEXT.template.md`; `tests/test_release.py` enforces it.

## 0.8.0

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
