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
```

Reinstalling re-copies the payload and leaves a settled context alone.

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
| 3 | platform default | `%APPDATA%\howdo\CONTEXT.md` on Windows; `~/.howdo/CONTEXT.md` on macOS and Linux |

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

## Request contracts

A resolution is assembled from Python objects, so the path, the predicted shape,
and the checks are real but stuck in the process that built them. A
`RequestContract` states them as data instead:

```python
from howdo import Host, RequestContract, bind

contract = RequestContract.from_json(shipped)   # path, accepts, expects, rules, requires
bound = bind(contract, Host("ci", capabilities=frozenset({"jira.write"})))
```

`bind` answers *can this run here* before anything resolves: a missing capability
or a read-only host for a consequential contract comes back as `Unsupported`
rather than as a surprise mid-operation. What the operation reads is declared
(`accepts`) and reaches the executor on the resolution instead of through a
closure; what it promises to make observable is declared (`expects`), and an
observation that does not match that shape routes to `contract` rather than
`postcondition` — a result that cannot be compared is a different fault from one
that came out wrong.

Checks travel as serializable clauses over a closed operator set, so a
consequential contract carries its own gate wherever it is loaded. A host may add
Python checks, but only on top of the contract's own.

```bash
python examples/portable_contract.py   # one contract, three hosts
```

## Layout

- `SKILL.md` — the skill itself: discipline, loop, agency modifier, persistence rules. This repo is the skill; install it as a directory.
- `QUICKSTART.md` — first run and ordinary use.
- `references/` — detail loaded on demand: `onboarding.md`, `vocabulary.md`.
- `CONTEXT.template.md` — the shipped template the durable store is instantiated from.
- `runtime/howdo/core.py` — zero-dependency operation protocol.
- `runtime/howdo/context.py` — zero-dependency context lifetime helpers.
- `runtime/howdo/contract.py` — portable request contracts: declared I/O shape, serializable checks, host binding.
- `examples/jira_workflow.py` — ordinary workflow example.
- `examples/portable_contract.py` — the same operation as a contract, offered to three hosts.
- `tests/` — runtime and context contract tests.
- `ADVERSARIAL.md` — enforced attacks and declared boundaries.
- `CONTRIBUTING.md` — lanes, rules, PR shape. `CHANGELOG.md` — versions.

## QA

```bash
python -m unittest discover -s tests -v
python examples/jira_workflow.py
python examples/portable_contract.py
```

The bundle and Python package share release version `0.8.0`, so package identity
does not drift from the skill release.

## License

MIT.
