# How Do v0.8.0 + Runtime Toolkit

**How Do** is a small discipline for understanding-before-acting.

```text
How[actor] : Map -> Path -> Check -> Do -> Look -> Update
```

The reference runtime implements it as:

```text
resolve -> admit -> operate -> observe -> settle
```

`I / you / we / they` changes whose capabilities, authority, environment, and
evidence constrain the HowDo. It does **not** create four new workflows.

How Do is **requested, not ambient**: it loads when someone asks for it by name,
by its loop, or by asking to slow down and ground the work — not on every how-to
question.

New here? Read [QUICKSTART.md](QUICKSTART.md).

## Install

```bash
git clone https://github.com/bdf1992/HowDo.git
cd HowDo
python install.py            # payload -> ~/.claude/skills/how-do, store -> per-user app data
python install.py --verify   # check an existing install, change nothing
python install.py --target DIR   # install into a different skills directory
python install.py --plugin DIR   # assemble a plugin root instead of a skill directory
```

Reinstalling re-copies the payload and leaves a settled context alone.

## As a plugin

`--plugin` writes the same payload with a `.claude-plugin/plugin.json` manifest
and `bin/` alongside it. Point a session at the result, or assemble it straight
into a skills directory so it loads on the next session:

```bash
python install.py --plugin ~/.claude/skills/how-do   # loads as how-do@skills-dir
claude --plugin-dir ./dist/how-do                    # or load it for one session
```

The skill stays `/how-do`. `SKILL.md` sits at the plugin root rather than under
`skills/`, which is what keeps the invocation un-namespaced — a `skills/how-do/`
layout would make it `/how-do:how-do`.

Two things come with the plugin host. `$CLAUDE_PLUGIN_DATA` is a directory it
guarantees will survive updates, so the durable store no longer depends on this
repository choosing a safe path. And `bin/` joins the shell `PATH` while the
plugin is enabled, so `howdo-context` is addressable from any directory:

```bash
howdo-context            # report the store's state
howdo-context --ensure   # instantiate it from the template if missing
howdo-context --path     # print the resolved store path
```

## Durable context

Two files, two lifetimes:

| file | location | lifetime |
|---|---|---|
| `CONTEXT.template.md` | the payload | ships with the skill; replaced on every update |
| `CONTEXT.md` | the store | yours; written by onboarding, survives updates |

Your `CONTEXT.md` is created from the template the first time you use the skill.
You settle yours; the template stays untouched.

The store is per-person, so it lives where the platform keeps per-user state:

| # | source | value |
|---|---|---|
| 1 | `--context PATH` | as given |
| 2 | `$HOWDO_CONTEXT` | as given |
| 3 | `$CLAUDE_PLUGIN_DATA` | `<that directory>/CONTEXT.md`, when a plugin host declares one |
| 4 | platform default | `%APPDATA%\howdo\CONTEXT.md` on Windows; `~/.howdo/CONTEXT.md` on macOS and Linux |

Moving a settled context means pointing `HOWDO_CONTEXT` at it. Keep the filename
`CONTEXT.md`: any other name is read as a fork — a separate context that starts
from its own onboarding.

A single generic context for everyone using one install is opt-in:

```bash
python install.py --shared   # store -> <payload>/CONTEXT.md, marked scope: shared
```

A shared store calibrates to whoever onboarded first, so treat it as weaker
evidence and never as a claim about the current user.

`CONTEXT.md` ships with `onboarding: required`. Before the first substantive
HowDo, the agent establishes how understanding gets built for you — a
conversation, never an intake form. You can decline it (`onboarding: declined`)
or say *not now* (`onboarding: deferred`); both are recorded, and neither becomes
learned context. The full interview, the runtime helpers, and the store and fork
rules are in [`references/onboarding.md`](references/onboarding.md).

## Agency modifier

| form | actor context |
|---|---|
| `How do I...` | user capabilities, environment, authority, relevant settled domain context |
| `How do you...` | actual assistant/tool capabilities; user context may shape rendering only |
| `How do we...` | compose user + assistant contexts and expose responsibility boundaries |
| `How do they...` | evidence about the external actor; never project user context onto them |

Durable `CONTEXT.md` primarily follows the **receiver** as a rendering lens.
Actor context follows the **subject** of the request. That separation prevents a
presentation preference from becoming a capability or authority claim.

## Context lifetime

```text
HowDo -> trace -> LongHow -> proposed durable lesson -> settlement -> CONTEXT revision
```

One interaction may change the current rendering immediately. It does not
automatically become a permanent learner claim.

## Layout

- `SKILL.md` — the skill itself: discipline, loop, agency modifier, persistence rules. This repo is the skill; install it as a directory.
- `QUICKSTART.md` — first run and ordinary use.
- `references/` — detail loaded on demand: `onboarding.md`, `vocabulary.md`.
- `CONTEXT.template.md` — the shipped template the durable store is instantiated from.
- `runtime/howdo/core.py` — zero-dependency operation protocol.
- `runtime/howdo/context.py` — zero-dependency context lifetime helpers.
- `examples/jira_workflow.py` — ordinary workflow example.
- `tests/` — runtime and context contract tests.
- `packaging/plugin.json` — the plugin manifest, minus a version the assembler derives.
- `bin/howdo-context` — store inspection from anywhere; on `PATH` under a plugin host.
- `ADVERSARIAL.md` — enforced attacks and declared boundaries.
- `CONTRIBUTING.md` — lanes, rules, PR shape. `CHANGELOG.md` — versions.

## QA

```bash
python -m unittest discover -s tests -v
python examples/jira_workflow.py
python install.py --plugin dist/how-do && claude plugin validate dist/how-do
```

The bundle and Python package share release version `0.8.0`, so package identity
does not drift from the skill release.

## License

MIT.
