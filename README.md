# How Do v0.7.1 + Runtime Toolkit

**How Do** is a small discipline for understanding-before-acting.

```text
Map -> Path -> Check -> Do -> Look -> Update
```

The reference runtime remains:

```text
resolve -> admit -> operate -> observe -> settle
```

v0.7 closes the durable-context lifecycle and adds one small modifier:

```text
How[actor] : Map -> Path -> Check -> Do -> Look -> Update
```

`I / you / we / they` changes whose capabilities, authority, environment, and evidence constrain the HowDo. It does **not** create four new workflows.

## Install

```bash
git clone https://github.com/bdf1992/HowDo.git
cd HowDo
python install.py            # payload -> ~/.claude/skills/how-do, store -> per-user app data
python install.py --verify   # check an existing install, change nothing
```

Two locations, two lifetimes:

```
CONTEXT.template.md   in the payload   shipped artifact, versioned, replaced on update
CONTEXT.md            in the store     per-person lineage, settled by onboarding
```

These are two **types**, not two copies. The template carries `template: true`, has `context_id: template`, is skipped by the fork check, and can never become `ready`. `ensure_context()` strips both the marker and the template's self-description, then opens a fresh lineage in the store — so no store ever carries prose saying it cannot be settled. `complete_onboarding()`, `decline_onboarding()`, and `fork_context()` all refuse a template outright: a template has no lineage to settle into.

The directory is named from `name:` in `SKILL.md`, not from the repo folder — a loader matching the frontmatter name will not find `HowDo/`. Reinstalling re-copies the payload, ships no build noise, and leaves a settled store alone.

How Do is **requested, not ambient**: it loads when someone asks for it by name, by its loop, or by asking to slow down and ground the work — not on every how-to question.

### Where the store lives

The store is per-person, so it goes where the platform keeps per-user state. Resolution order:

| # | source | value |
|---|---|---|
| 1 | `--context PATH` | as given |
| 2 | `$HOWDO_CONTEXT` | as given |
| 3 | platform default | `%APPDATA%\howdo\CONTEXT.md` on Windows; `~/.howdo/CONTEXT.md` on macOS and Linux |

Resolution depends only on configuration, never on what is already on disk, so one environment always resolves to one path; anyone moving a settled store points `HOWDO_CONTEXT` at it. The basename stays `CONTEXT.md`, because a different basename is read as a fork.

### Per-user by default, generic by opt-in

This context records how one person takes explanations, so a per-user store is the default and `complete_onboarding()` / `decline_onboarding()` refuse a target inside the payload: the next update would discard the settlement without raising anything — a receipt the installation cannot keep.

A single generic context for everyone using one install is a legitimate setup, and it is opt-in only:

```bash
python install.py --shared   # store -> <payload>/CONTEXT.md, marked scope: shared
```

The file records `scope: shared` in its own frontmatter, so every later reader can tell a generic context from a personal one. That marker is what lifts the payload refusal — an unmarked context inside the payload is still refused as an accident. A shared store survives `install.py` re-runs, but it is lost if the skill directory is deleted or replaced wholesale, and it calibrates to whoever onboarded first: treat it as weaker evidence and never as a claim about the current user.

## First install

`CONTEXT.md` ships with `onboarding: required`. Before the first substantive HowDo, run one short comparative calibration unless the user explicitly declines durable calibration:

1. ask for a domain the person knows well enough to critique;
2. render one familiar concept in 3–4 equivalent structures;
3. ask what landed, what did not, and why;
4. run one positive/negative contrast;
5. record one bounded representation observation plus concrete positive and negative examples;
6. settle the context.

The runtime treats completion as a structural receipt only: `onboarding: complete` requires at least one non-placeholder bullet in each required evidence section. It does not validate the truth or quality of the feedback.

A user can decline the calibration and continue the task. Persist `onboarding: declined`; later sessions do not ask again, and the context must not be used as learned rendering context.

## Context lifetime

```text
HowDo -> trace -> LongHow -> proposed durable lesson -> settlement -> CONTEXT revision
```

One interaction may change the current rendering immediately. It does not automatically become a permanent learner claim.

## Agency modifier

| form | actor context |
|---|---|
| `How do I...` | user capabilities, environment, authority, relevant settled domain context |
| `How do you...` | actual assistant/tool capabilities; user context may shape rendering only |
| `How do we...` | compose user + assistant contexts and expose responsibility boundaries |
| `How do they...` | evidence about the external actor; never project user context onto them |

Durable `CONTEXT.md` primarily follows the **receiver** as a rendering/interaction lens. Actor context follows the **subject** of the request. That separation prevents a presentation preference from becoming a capability or authority claim.

## Forkable context

A context file records its basename in `context_file`.

```text
CONTEXT.md
    |
    +-- copy/fork --> CONTEXT.visual.md
    +-- copy/fork --> CONTEXT.code.md
```

A different basename is a new lineage. The source is preserved, the fork records `parent_context_id`, and onboarding is required again. Required lineage keys cannot simply be deleted to make a file ready.

Helpers:

- `resolve_context_path(...)` / `default_store_path(...)` -> where the store is, per platform
- `inspect_context(path)` -> `missing | template | onboarding_required | ready | declined | fork_required | invalid`
- `complete_onboarding(...)` -> writes the minimum comparative receipt and settles the file
- `decline_onboarding(path)` -> persists a no-calibration state without creating learned context
- `fork_context(source, destination)` -> non-destructive normalized fork
- `is_shared(metadata)` -> whether a context declares itself the generic store for an install
- `new_context_id()` -> opaque ID

## Layout

- `SKILL.md` — v0.7.1 discipline, loop, agency modifier, persistence rules
- `references/` — detail loaded on demand: `onboarding.md` (interview, store, forks, scope), `vocabulary.md`
- `CONTEXT.template.md` — the shipped template the durable store is instantiated from
- `runtime/howdo/core.py` — zero-dependency operation protocol; `Request.actor` records the bound actor lens without inferring language
- `runtime/howdo/context.py` — zero-dependency context lifetime helpers
- `examples/jira_workflow.py` — ordinary workflow example
- `tests/` — runtime + context contract tests
- `ADVERSARIAL.md` — enforced attacks and declared boundaries

## QA

```bash
python -m unittest discover -s tests -v
python examples/jira_workflow.py
```

The bundle and Python package share release version `0.7.1` so package identity does not drift from the skill release.

## Repository

- `SKILL.md` — the skill (this repo is the skill; install it as a directory).
- `runtime/howdo/` — zero-dependency reference kernel and context helpers.
- `tests/` — invariant tests; `ADVERSARIAL.md` — enforced vs declared.
- `CONTRIBUTING.md` — lanes, rules, PR shape. `CHANGELOG.md` — versions.
- License: MIT.
