# How Do v0.9.0 + Runtime Toolkit

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

## Issued artifacts

A finished HowDo can leave a **domain-how** behind: one file per recurring
concern, holding the map, the workflow, the contracts and invariants, and the
worked example from the run that produced it.

```python
from howdo import issue, issue_from_run, read_index, ground

how = issue_from_run(resolution, residual, concern="jira.workflow",
                     contract=CONTRACT, map={"statuses": [...]})
issue(how)                                   # -> ~/.howdo/domains/jira.workflow.json
read_index(status="grounded", requires=host_capabilities)
```

It is minted from a run that happened, never from a plan. It stays `untested`
until `ground()` promotes it on a residual that matched — and a revision drops
the grounding its predecessor earned, so an edited map cannot inherit evidence
about the old one. The index is rebuilt from the files, so it is a catalogue
rather than a second source of truth.

Artifacts live beside your context (`~/.howdo/domains/`, or `$HOWDO_DOMAINS`),
outside the payload, for the reason `CONTEXT.md` does: an update replaces the
skill without discarding what the work produced.

### Install it as a skill or a workflow

A grounded domain-how renders into either format a host loads directly:

```python
from howdo import write_skill, write_workflow

write_skill(how, "~/.claude/skills")        # -> jira-workflow/SKILL.md
write_workflow(how, "~/.claude/workflows")  # -> jira-workflow.js, runs as /jira-workflow
```

The skill body carries the map, the workflow, the gate, the invariants, the
observable result, and the run it came from. The workflow script is the loop:
`Check` establishes the gate and fizzles if it cannot, `Do` runs the path as
phases, and `Look` observes the world independently instead of reading back what
the acting agents reported.

Frontmatter has two targets, because the accepted field sets differ. The default
`target="spec"` emits only the six fields the Agent Skills specification allows
(`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`),
so the bundle survives claude.ai upload, the Skills API, and `package_skill.py` —
any other key fails those with a hard error rather than being ignored.
`target="claude-code"` additionally marks a consequential artifact
`disable-model-invocation: true`, so a skill that mutates state is not loaded
because a conversation drifted near the topic.

An untested artifact is refused unless you pass `allow_untested=True`, and the
override stamps the output — an installed skill pre-loads every later session on
that concern, so shipping an unconfirmed one is a different order of mistake
from getting one answer wrong. Emission is a projection: re-emit rather than
editing what came out.

```bash
python examples/issue_domain_how.py   # run -> issue -> index -> ground -> emit
```

## Layout

- `SKILL.md` — the skill itself: discipline, loop, agency modifier, persistence rules. This repo is the skill; install it as a directory.
- `QUICKSTART.md` — first run and ordinary use.
- `references/` — detail loaded on demand: `onboarding.md`, `vocabulary.md`.
- `CONTEXT.template.md` — the shipped template the durable store is instantiated from.
- `runtime/howdo/core.py` — zero-dependency operation protocol.
- `runtime/howdo/context.py` — zero-dependency context lifetime helpers.
- `runtime/howdo/contract.py` — portable request contracts: declared I/O shape, serializable checks, host binding.
- `runtime/howdo/domain.py` — the issuer and index: domain-hows minted from runs, grounded by evidence.
- `runtime/howdo/emit.py` — render an artifact as an Agent Skill bundle or a Claude Code workflow script.
- `examples/jira_workflow.py` — ordinary workflow example.
- `examples/portable_contract.py` — the same operation as a contract, offered to three hosts.
- `examples/issue_domain_how.py` — a run that leaves a durable, indexed artifact behind.
- `tests/` — runtime and context contract tests.
- `ADVERSARIAL.md` — enforced attacks and declared boundaries.
- `CONTRIBUTING.md` — lanes, rules, PR shape. `CHANGELOG.md` — versions.

## QA

```bash
python -m unittest discover -s tests -v
python examples/jira_workflow.py
python examples/portable_contract.py
python examples/issue_domain_how.py
```

The bundle and Python package share release version `0.9.0`, so package identity
does not drift from the skill release.

## License

MIT.
