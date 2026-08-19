# How Do v0.8.0 — quickstart

## First run

`CONTEXT.template.md` ships with the skill; your `CONTEXT.md` is instantiated from it into the store — `--context`, else `$HOWDO_CONTEXT`, else the platform default (`%APPDATA%\howdo\CONTEXT.md` on Windows, `~/.howdo/CONTEXT.md` on macOS and Linux). Settle the store, never the template; instantiation drops the template's self-description, so the file you settle reads as a context and nothing else.

The store is per-person by default. One generic context shared by everyone using an install is opt-in — `python install.py --shared` — and marks itself `scope: shared` so a later reader can tell it apart from a personal one. If your `CONTEXT.md` is unresolved, calibrate before the first substantive HowDo unless the user explicitly declines durable calibration. Persist a decline as `onboarding: declined`; later sessions do not ask again and do not use learned durable context. A *not now* is different — persist `onboarding: deferred`, get on with the work, and leave the offer open.

Ask for one domain they know well. Explain one familiar idea in a few equivalent forms: relational/diagram, narrative, formal/schema, executable/procedural. Ask what landed, what did not, and why. Run one liked-vs-disliked contrast. Record one bounded observation plus concrete positive and negative examples. Do not assign a fixed learning-style label.

Then give one operational note:

> `I / you / we / they` changes whose capabilities and context I use. It changes the frame of the How, not the learning interview.

## Ordinary use

```text
How[actor] : Map -> Path -> Check -> Do -> Look -> Update
```

- **Actor** — whose capability, authority, environment, and evidence matter?
- **Map** — what are we actually working with?
- **Path** — how should the work proceed?
- **Check** — what must be true before, and observably true after, consequential steps?
- **Do** — act only when those checks are grounded.
- **Look** — inspect what actually happened.
- **Update** — change only what the residual disproved.

`CONTEXT.md` shapes rendering. It must not manufacture capability or evidence for the bound actor.

## Afterward

Keep one-run feedback in the HowDo trace. LongHow promotes only recurring or explicitly ratified lessons into durable context.

To experiment with a different learned interface, fork rather than overwrite:

```text
CONTEXT.md -> CONTEXT.code.md
```

The old file remains intact; the new lineage calibrates independently.
