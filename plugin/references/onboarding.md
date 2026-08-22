# Durable context: onboarding, store, forks

Read this when the active context is anything but `onboarding: complete`. A ready
context needs none of it — `SKILL.md` already carries the routing and the
guarantees.

## Establishing the pedagogy

The pedagogy is the loop itself, and it comes in two halves: the loop is a fixed
shell, and its internals are personal.

The shell is identical in every install: **Map** is the domain and its priors,
**Path** sequences it, **Check** states what would count as understood, **Do**
teaches, **Look** tests the result against that, and **Update** revises the
smallest part the evidence disproved. Nobody establishes this; it ships.

The internals have no source but the person, which is why onboarding needs one
present. Their settings for that shell cannot be inferred from the host, the
task, or anything already on disk — only from how this person responds to being
taught. So onboarding does not invent a pedagogy, and it is not a configuration
step either: it works out **this person's settings for that shell**.

Drop the first half and onboarding reads as an agent inventing a pedagogy per
reader. Drop the second and it reads as boilerplate someone could skip.

You learn those settings the way the skill learns anything else: present the
information, and take their preference and their critique of it — their judgment
of whether it actually built understanding, not whether they enjoyed it. That
judgment is only available to someone who can already tell, which is why the
anchor domain matters.

You have latitude in how you get there. What follows is what must end up
established, not a script to run.

### What you are trying to establish

- **Anchors — tunes `Map`.** A domain this person knows well enough to tell a good explanation from a bad one, and whose material new work can attach to. This is also the instrument, and its expertise requirement is load-bearing — see below.
- **Build direction — tunes `Path`.** Does understanding arrive instance-first (the case, then the principle it illustrates) or principle-first (the rule, then where it bites)? This is the most load-bearing thing you can learn, and it is independent of medium.
- **What counts as understood — tunes `Check` and `Look`.** For them: predicting the next result, reproducing the steps, watching the thing break, or saying it back in their own words. This is what `Check` should commit to and what `Look` should test for.
- **How correction should land — tunes `Update`.** Directly, by counterexample, by question, or side-by-side with what they said. Getting this wrong makes every later residual expensive.

Two are usually enough to start. Anchors and build direction carry the most
weight; the other two often arrive on their own from ordinary work.

### How you get there is yours

Any of these is a legitimate route:

- **Use the work they brought — but only if they are expert in it.** If their current task sits inside a domain they know well, it is both real work and a valid instrument, and costs them nothing. If they are a novice in it, it is not a valid instrument; find an anchor elsewhere.
- **Learn it by doing it.** Explain something instance-first and see whether they engage or ask you to back up. You do not have to ask a question to learn the answer to one.
- **Ask outright.** Some people know exactly how they learn and will tell you in a sentence. Take the gift.
- **Guess and invite correction.** "I'll start with the concrete case and generalize after — say if you'd rather have the rule first." A stated assumption is faster than a question — and it becomes evidence when you watch whether it held, not when they nod at it.
- **Skip what is already visible.** If they opened with a precise technical question full of domain vocabulary, you already have their anchor. Do not ask for it.

Take the dimensions in whatever order the conversation offers them.

Stop when you have **tested** a reading, not when you have formed one. Someone
stating a preference hands you a hypothesis; predicting from it and watching
whether the prediction holds is what turns it into evidence. Render something
the way the reading says to, and look at what comes back. Testing what you
learned is what makes it evident — an untested reading is a guess, and this one
gets reused later in a domain where nobody can catch it being wrong.

How you test is as free as how you learn: a deliberate contrast, the next thing
you were going to explain anyway, or simply noticing whether the exchange after
it went easier. What you need is one reading that survived contact, with the
reason it survived.

### Why the anchor must be a domain they know

What you learn here does not stay here. The observation is saved as an
**exemplar** — a reusable *shape* — and its whole purpose is to be applied later
to topics the person is **not** expert in. That is the payoff: you work out how
understanding gets built for them somewhere they can check your work, then carry
the shape into places where they cannot.

Which is exactly why the calibration domain has to be one they know well. In a
domain where they are a novice, they cannot separate *"that was well built"*
from *"I finally understood it"*. Those feel identical from the inside and mean
completely different things. Calibrate there and you learn what felt good while
confused, then generalise it to every future topic.

Two consequences worth holding on to:

- **Record what the observation is expected to transfer to.** An observation carries applicability — "on systems with hidden dependencies, the failure case had to come before the rule" — not just a preference. Applying it outside that scope is a guess, and should be held as one.
- **In the novice domain, the burden is entirely yours.** They cannot tell you the shape stopped working; they will only look lost, or go quiet, or stop asking. Watch for that and treat it as a residual against the exemplar, not as a fact about them.

### Keep it a conversation

This is two people working out how to work together. It is not an intake form,
an assessment, or a personality quiz, and it must never feel like one.

- No visible steps, phases, or numbered questions. Ideally the person cannot tell an onboarding is happening at all.
- One question at a time, at most. Batched questions read as a form.
- Never use learning-style vocabulary at them. Do not ask whether they are a visual learner; do not tell them what kind of learner they are.
- Never say the machinery at them either. The local terms are working equipment, not output: no *pedagogy*, *calibration*, *anchor domain*, *exemplar*, *residual*, no state names, no store paths. Onboarding leaks these hardest, because it is where you are thinking about them most. The aim is that the person cannot tell an onboarding is happening; naming it guarantees they can.
- **"I don't know" is an answer, and a useful one.** Someone who cannot describe their own comprehension needs you to instrument it rather than ask about it. Record that — it is a pedagogical finding, not a failed question.
- Say once that this is a starting guess they can correct any time. Provisionality stated out loud is both honest and good teaching.
- If they are impatient, they are telling you something. Defer and get to work.

### What must end up written

The route is free; the receipt is not. Settle only when each required evidence
section holds at least one real bullet: the anchor domain, an observation about
how understanding gets built for this person, one concrete thing that helped,
and one concrete thing that did not — each with the reason it did.

Write observations, not identities. "Needed the failing case before the rule
would stick, on protocol work" is usable by a later session. "Visual learner"
is not.

Record what tested it. An observation whose evidence is only that the person
said so is weaker than one that predicted something and was right, and the two
should not read the same to whoever picks this up next.

Then assign a `context_id`, set `context_file` to the actual basename, and mark
`onboarding: complete`. That is structural completeness only; it does not prove
the evidence is truthful or good.

Mention once that `I / you / we / they` changes whose capabilities and context
are used. It does not need another round of questions.

### A first hypothesis, not a verdict

`HowDo → trace → LongHow → settlement` exists because the interview is the
weakest evidence source in the system. Traces from real work beat anything
established at the door. Get enough to start, then let the work correct you.

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

If the payload ships `bin/` on `PATH` — a plugin host puts it there — one
command answers all of this from any directory:

```bash
howdo-context --ensure
```

Otherwise the helpers answer it directly, from the payload root:

```bash
python -c "import sys; sys.path.insert(0, 'runtime'); \
from howdo.context import ensure_context, inspect_context; \
s = ensure_context(template='CONTEXT.template.md'); print(s.path, s.state)"
```

That second form resolves `runtime` relative to the working directory, so run
it from the payload or give it an absolute path. `howdo-context` has no such
requirement, which is the reason it exists.

If `runtime/` or `CONTEXT.template.md` is absent — the skill was copied by hand
rather than installed — do not guess a store into the payload. Create the
resolved path with the frontmatter keys `howdo_context`, `context_id: pending`,
`context_file: CONTEXT.md`, `scope: user`, `skill: how-do`, `skill_version`,
`onboarding: required`, `parent_context_id: none`, and the six evidence sections
named above, then onboard it.

## Per-user by default; generic by opt-in

`scope: user` is the default: this context records how one person takes
explanations. `scope: shared` marks a generic store for everyone using one
install — never inferred, always opted into, and the only kind admitted inside
the payload. A shared store calibrates to whoever onboarded first: treat its
observations as weaker evidence, never as a claim about the current user.

**How it is opted into depends on how the skill was installed, and under a
plugin the payload is the wrong place for it.** A skill directory is replaced wholesale on
update, which is why its installer carries a `--shared` opt-in at all, and why
it is explicit rather than inferred. A plugin's payload is *version-scoped* — it sits
under a directory named for the release — so a shared store settled inside it is
discarded by the next version, not merely overwritten. Under a plugin, point
`$HOWDO_CONTEXT` at a path the host does not replace, or use the directory the
host names in `$CLAUDE_PLUGIN_DATA`, and mark the store `scope: shared` there.
`howdo-context --path` reports where resolution currently lands.

Settling a shared store inside a plugin payload is **refused**, not merely
discouraged: the runtime raises rather than letting a context be written
somewhere the next release stops reading. The refusal names the directory to use
instead.

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
