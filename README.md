# How Do v0.7.0 + Runtime Toolkit

**How Do** is a small discipline for understanding-before-acting.

```text
Map -> Path -> Check -> Do -> Look -> Update
```

The reference runtime remains:

```text
resolve -> admit -> operate -> observe -> settle
```

v0.6 closes the durable-context lifecycle and adds one small modifier:

```text
How[actor] : Map -> Path -> Check -> Do -> Look -> Update
```

`I / you / we / they` changes whose capabilities, authority, environment, and evidence constrain the HowDo. It does **not** create four new workflows.

## Install

```bash
git clone https://github.com/bdf1992/HowDo.git
cd HowDo
python install.py            # payload -> ~/.claude/skills/how-do, store -> ~/.howdo/CONTEXT.md
python install.py --verify   # check an existing install, change nothing
```

Two locations, two lifetimes:

```
CONTEXT.template.md   in the payload   shipped artifact, versioned, replaced on update
CONTEXT.md            in the store     per-person lineage, settled by onboarding
```

These are two **types**, not two copies. The template carries `template: true`, has `context_id: template`, is skipped by the fork check, and can never become `ready`. `ensure_context()` strips the marker and opens a fresh lineage in the store. `complete_onboarding()`, `decline_onboarding()`, and `fork_context()` all refuse a template outright — a template has no lineage to settle into.

The directory is named from `name:` in `SKILL.md`, not from the repo folder — a loader matching the frontmatter name will not find `HowDo/`. The store path is `--context`, else `$HOWDO_CONTEXT`, else `~/.howdo/CONTEXT.md`; its basename stays `CONTEXT.md`, because a different basename is read as a fork. Reinstalling re-copies the payload and leaves a settled store alone.

`complete_onboarding()` and `decline_onboarding()` refuse a target inside the payload. A settlement written there would be discarded by the next update without raising anything — a receipt the installation cannot keep.

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

- `inspect_context(path)` -> `missing | onboarding_required | ready | declined | fork_required | invalid`
- `complete_onboarding(...)` -> writes the minimum comparative receipt and settles the file
- `decline_onboarding(path)` -> persists a no-calibration state without creating learned context
- `fork_context(source, destination)` -> non-destructive normalized fork
- `new_context_id()` -> opaque ID

## Layout

- `SKILL.md` — v0.7.0 discipline, onboarding, agency modifier, persistence rules
- `CONTEXT.md` — required durable context template
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

The bundle and Python package share release version `0.7.0` so package identity does not drift from the skill release.

## Repository

- `SKILL.md` — the skill (this repo is the skill; install it as a directory).
- `runtime/howdo/` — zero-dependency reference kernel and context helpers.
- `tests/` — invariant tests; `ADVERSARIAL.md` — enforced vs declared.
- `CONTRIBUTING.md` — lanes, rules, PR shape. `CHANGELOG.md` — versions.
- License: MIT.
