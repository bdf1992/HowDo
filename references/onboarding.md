# Durable context: onboarding, store, forks

Read this when the active context is anything but `onboarding: complete`. A ready
context needs none of it — `SKILL.md` already carries the routing and the
guarantees.

## Comparative onboarding

Onboarding is a calibration, not a psychometric test. Stop as soon as one useful
positive distinction and one useful negative distinction are grounded.

1. **Establish a calibration domain.** Ask for one or two domains or subjects the person knows well enough to catch a weak explanation quickly. Ask what kind of work or judgment they perform there.
2. **Same idea, different renderings.** Choose one small concept inside a calibration domain and explain the same underlying content in 3–4 materially different forms, kept similar in length and factual content:
   - relational / diagram-first;
   - narrative / sequence-and-consequence;
   - formal / definitions-table-schema;
   - executable / code-checklist-worked procedure.
3. **Get comparative feedback.** Ask which landed, which did not, and what structural difference mattered. Reasons matter more than labels.
4. **Run one contrast pass.** Produce one short explanation emphasizing the liked traits and one emphasizing the disliked traits. Ask whether the contrast is real. Probe ordering/density only if still ambiguous.
5. **Write observations, not identities.** Record claims such as “for relational systems, diagram→example→terminology landed better than prose-first,” with applicability, evidence, confidence, and limits. Preserve at least one concrete positive and negative example.
6. **Settle structurally.** The context is ready only when the calibration domain, representation observation, landed example, and rejected example each contain at least one non-placeholder evidence bullet. Then assign a `context_id`, set `context_file` to the actual basename, and mark `onboarding: complete`. This is structural completeness only; it does not prove that the evidence is truthful or good.
7. **Give the agency note once.** Explain briefly that `I / you / we / they` changes whose capabilities and context are used; it does not require another learner questionnaire.

## Decline versus deferral

Two different answers, two different states, and conflating them costs a calibration.

- **Declined** (`onboarding: declined`) is an answer. The person does not want durable calibration. Never ask again on any later session unless they reopen it themselves, and never treat the file as learned context.
- **Deferred** (`onboarding: deferred`) is a postponement. The person wants to get on with the work. Do that, without learned context, and leave the offer open — it may be raised again on a later session, at most once per session. A deferral that is never taken up simply stays deferred.

`defer_onboarding()` persists the postponement and assigns a stable `context_id`, so the lineage exists and the same file can settle later with that identity intact. A deferred context onboards normally when the person is ready, and can still be declined outright. A decline cannot be reopened by deferring — onboard it instead.

Never record "not now" as a refusal.

## Template versus instance

The payload ships `CONTEXT.template.md`: an artifact, versioned, marked
`template: true`, replaced by every update, never settled and never forked.
`ensure_context()` instantiates it into the store, stripping both the marker and
the template's self-description — so no store ever carries prose claiming it
cannot be settled. The instance is a lineage. Do not conflate them.

## Store location

Resolve the store in this order:

1. a path the user selected explicitly for this session;
2. `$HOWDO_CONTEXT`, if set;
3. the platform default — `%APPDATA%\howdo\CONTEXT.md` on Windows, `~/.howdo/CONTEXT.md` on macOS and Linux.

Resolution depends only on configuration, never on what is already on disk, so
one environment always resolves to one path. Anyone moving a settled store points
`HOWDO_CONTEXT` at it. The basename stays `CONTEXT.md`; a different basename is
read as a fork.

If the payload ships `runtime/`, the helpers answer all of this directly:

```bash
python -c "import sys; sys.path.insert(0, 'runtime'); \
from howdo.context import ensure_context, inspect_context; \
s = ensure_context(template='CONTEXT.template.md'); print(s.path, s.state)"
```

If `runtime/` or `CONTEXT.template.md` is absent — the skill was copied by hand
rather than installed — do not guess a store into the payload. Create the
resolved path with the frontmatter keys `howdo_context`, `context_id: pending`,
`context_file: CONTEXT.md`, `scope: user`, `skill: how-do`, `skill_version`,
`onboarding: required`, `parent_context_id: none`, and the six evidence sections
named above, then onboard it.

## Per-user by default; generic by opt-in

`scope: user` is the default: this context records how one person takes
explanations. `scope: shared` marks a generic store for everyone using one
install — opted into via `install.py --shared`, never inferred, and the only kind
admitted inside the payload. A shared store calibrates to whoever onboarded
first: treat its observations as weaker evidence, never as a claim about the
current user.

## Fork / rename rule

`CONTEXT.md` is intentionally forkable. Its frontmatter records both `context_id`
and `context_file`.

- A template is not a context: it has no `context_id`, fails the readiness check by type rather than by evidence, and is refused by the settlement and fork helpers.
- If no active context file exists, instantiate one from the template and run onboarding before substantive work unless the user explicitly declines durable calibration.
- If required lineage metadata is missing, treat the file as invalid rather than silently ready.
- If `onboarding: required`, or the comparative evidence sections are placeholders, onboarding is unresolved. If `onboarding: declined`, do not ask again and do not use the file as learned context.
- If the actual basename differs from embedded `context_file`, treat the file as a **new fork** and run onboarding for that lineage. Do not silently reuse the old identity.
- Prefer non-destructive copy/fork: `CONTEXT.md` → `CONTEXT.visual.md`, `CONTEXT.code.md`, etc. Keep the source file. The new file may name the source as `parent_context_id`, but inherited preferences are hypotheses until the fork settles them.
- Never auto-merge context files. If several exist, use the explicitly selected one; otherwise use canonical `CONTEXT.md`.
- A skill version bump alone does not erase a settled context. Migrate structure if needed while preserving learned observations.

## Runtime helpers

`resolve_context_path()`, `default_store_path()`, `ensure_context()`,
`inspect_context()`, `complete_onboarding()`, `decline_onboarding()`,
`fork_context()`, `defer_onboarding()`, `is_shared()`. They enforce the structural lifetime without
trying to automate the human judgment inside the interview.
