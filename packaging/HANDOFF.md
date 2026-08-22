# Packaging lane — handoff

Branch `claude/howdo-fullscope-plugin-qqvw7h`. Draft PR #14.
Merged up to `main` through #13 and #15. Release 0.9.0.

**The layout changed.** `plugin/` is now the plugin root and the whole of what
ships; everything beside it is a repository concern. Paths below assume that.

This lane converts How Do into a Claude Code plugin. It is **packaging only**:
no hook, no agent, no `settings.json`, nothing that would make the discipline
ambient. That restraint is not conservatism, it is the roadmap's gate — see
*Deliberately not done* below before adding a component.

**Two of three parity items are closed. One remains, and it still gates the
merge.** Item 2 is a real difference between the two install paths: a person
who installs the plugin never sees the note the installer prints. It is not
packaging work — the only obvious fix is a `SessionStart` hook, and whether
that is admissible is a question about the discipline, not about packaging.
It needs a decision, not an implementation.

---

## Established, do not re-derive

These were tested against the runtime, not read from the documentation. Two of
them contradict the published docs, so re-reading the docs will actively
mislead you. Method: build a plugin under `~/.claude/skills/<name>/` with a
`.claude-plugin/plugin.json`, then `claude plugin details <name>@skills-dir`
and a headless `claude --plugin-dir <path> -p '...'` to read back the
registered name.

| question | answer | how it was shown |
|---|---|---|
| Does a root `SKILL.md` use the frontmatter `name`? | **No.** The *plugin* name wins; frontmatter `name` is ignored | Set them to different values (`how-do` vs `totally-different-name`); the plugin name registered |
| Root `SKILL.md` invocation name | bare `/how-do` — no namespace | headless probe returned `how-do` |
| `skills/<name>/SKILL.md` invocation name | `/<plugin>:<skill>` — namespaced | headless probe returned `hd-b:how-do` |
| Does the host identify a plugin by directory or manifest? | **Manifest.** Directory is ignored | Directory `divergent`, manifest `how-do` → loaded as `how-do@skills-dir` |
| Does `bin/` reach the Bash `PATH`? | Yes | `command -v howdo-context` resolved inside the plugin root |
| Does `plugin details` count a root-`SKILL.md` skill? | **No** — reports `Skills (0)`, `~0 tok`, though the skill loads fine | Observed on three separate probes |

The docs claim the opposite of rows 1 and 4. The last row is a host-side
reporting gap, not ours: anyone inspecting the plugin sees an empty inventory
even though the skill works. Do not "fix" it by moving `SKILL.md` under
`skills/` — that trades a cosmetic reporting bug for a renamed skill.

**Why row 1 is load-bearing.** `SKILL.md`'s description promises `/how-do`, and
`tests/test_release.py::InvocationIntentTests::test_description_asks_to_be_invoked`
asserts that string. A `skills/how-do/` layout silently renames the skill to
`/how-do:how-do` and breaks both. `tests/test_plugin.py::LayoutTests` pins the
root layout for exactly this reason.

---

## What landed

- `packaging/plugin.json` — manifest source. **Carries no `version`;** the
  assembler reads it from `SKILL.md` so release alignment stays at four places.
  A test fails if a version is ever added here.
- `install.py --plugin DIR` — `assemble_plugin()` calls `copy_payload()` and
  then adds the manifest and `bin/`. It does not re-list files. That is the
  whole design: the rule that keeps `experiment/` and `tests/` out of an
  install is enforced in one place and the plugin inherits it.
- `runtime/howdo/context.py` — `$CLAUDE_PLUGIN_DATA` in the store precedence,
  between `$HOWDO_CONTEXT` and the platform default. Below the env var so
  installing never relocates a store somebody placed; above the platform
  default so a host that states its own directory beats one we guess. Absent
  the variable, resolution is unchanged.
- `bin/howdo-context` (+ `.cmd` shim) — store report / `--ensure` / `--path`
  from any directory. Replaces the `sys.path.insert(0, 'runtime')` shell-out in
  `references/onboarding.md`, which only resolved from inside the payload.
- `install.py::report()` — plugin-aware. A plugin root is judged by its
  manifest name; the directory is free. An ordinary skill dir still has to
  match `SKILL.md`.
- `tests/test_plugin.py` — 28 tests of 302. Parity is asserted **in both directions**
  against `copy_payload`'s output rather than a second file list.
- CI `plugin:` job — appended at the end of `tests.yml` deliberately, so it
  cannot conflict with in-flight edits to the `suite:` job.

---

## Open work items

### 1. ~~Not distributable~~ — CLOSED

The payload moved under `plugin/`, now a tracked plugin root: manifest,
`SKILL.md`, `references/`, `runtime/`, `examples/`, `bin/`.
`.claude-plugin/marketplace.json` at the repo root points at it. Both pass
`claude plugin validate --strict`, and loading the tracked directory with
`--plugin-dir ./plugin` registers the skill as bare `/how-do` with `bin/` on
`PATH` — no build step anywhere.

One reversal came with it: **the manifest version is tracked, not derived.**
There is no assembler left to derive it during, because a marketplace reads
the file as committed. It is the fifth place `test_release.py` holds aligned.
Do not try to restore the derived version — an earlier revision of this
document forbade pinning it, and a test now asserts the opposite.

### 2. `CONFIGURATION_NOTE` never reaches a plugin user — OPEN, still gates parity

`install.py` prints a person-facing note on a fresh install explaining the
onboarding conversation and both opt-outs. `tests/test_release.py::InstallerNoteTests`
guards its content carefully. A `/plugin install` never runs `install.py`, so
that note reaches nobody.

This is a degraded first run, not a broken one: `SKILL.md` still gates
onboarding at the first substantive HowDo, so the conversation happens — the
person just never got the heads-up that explains it and offers the decline.

**Do not reach for a `SessionStart` hook without deciding the doctrine question
first.** A hook that speaks before being asked is close to the line `SKILL.md`
draws in *Refuses* — "Loading the discipline uninvited." A note that only
explains a pending conversation may be admissible where injected context is
not, but that is a skill-text decision, not a packaging one. Raise it as a
skill-text change with a trace, per `CONTRIBUTING.md`.

### 3. ~~The plugin ships PILOT-0001~~ — CLOSED

#12 merged and moved the adapter to `experiment/PILOT-0001/adapter/`, out of
the payload. The tripwire this lane left behind
(`test_the_plugin_names_no_experiment`) stopped skipping on its own, ran, and
passed. Nothing in `plugin/` names the pilot.

The suite now has **no skips at all**. Any skip is a regression.

## Collision map

Nothing is in flight against this lane. #13, #15, and #12 have all merged and
all three are absorbed.

The one that mattered is recorded here because it will look strange in the
history otherwise. #12 and this lane both moved `runtime/howdo/environment.py`,
to different places — here to `plugin/runtime/` with the rest of the payload,
there to `experiment/PILOT-0001/adapter/`. Git reported a rename/rename
conflict across three paths. **#12 won, correctly**: that file is the pilot
adapter and never belonged in the payload. The resolution was:

```bash
git rm plugin/runtime/howdo/environment.py           # ours: wrong home
git add experiment/PILOT-0001/adapter/environment.py # theirs: correct home
```

`tests/test_environment_context.py` then needed both paths, one on each side of
the boundary: `PAYLOAD / "runtime"` for the runtime it tests, and
`ROOT / "experiment" / "PILOT-0001"` for the adapter that imports across it.

`howdo/payload-store-split` is empty against main. Stale; ignore.

To re-check collisions after anything moves:

```bash
git checkout -B probe origin/<their-branch>
git merge --no-commit --no-ff <this-branch> || git diff --name-only --diff-filter=U
git merge --abort; git checkout <this-branch>; git branch -D probe
```

---

## Verifying this lane

```bash
python -m unittest discover -s tests -v        # 470 tests, no skips
python plugin/examples/jira_workflow.py
python plugin/examples/portable_contract.py
python plugin/examples/issue_domain_how.py
claude plugin validate ./plugin --strict       # the plugin root
claude plugin validate . --strict              # the marketplace entry
claude --plugin-dir ./plugin                   # loads the tracked root directly
python install.py --target /tmp/skilldir && python install.py --target /tmp/skilldir --verify
```

Any skip is a regression. The one that used to be sanctioned closed with #12.

To watch it load for real:

```bash
cp -r plugin ~/.claude/skills/how-do   # or: python install.py --plugin ~/.claude/skills/how-do
claude plugin list                     # expect: how-do@skills-dir, loaded
```

---

## Traps

- **`plugin details` showing `Skills (0)` is expected.** Host reporting gap for
  the root-`SKILL.md` layout. The skill loads. Do not restructure to fix it.
- **There are no sanctioned skips.** There used to be exactly one; it closed
  when #12 landed. A skip now means something regressed.
- **The manifest version IS tracked**, in `plugin/.claude-plugin/plugin.json`,
  and must match `plugin/SKILL.md`. An earlier revision of this lane derived it
  and forbade pinning it; that stopped being possible when the plugin root
  became tracked. `test_release.py` and `test_plugin.py` both assert alignment.
- **Do not move `SKILL.md` under `skills/`.** It renames the skill. See the
  findings table.
- **`bin/` is not in `PAYLOAD`.** It ships only via `PLUGIN_EXTRA` on the
  `--plugin` path, so an ordinary `install.py` skill directory does not carry
  it. Intentional — a bare skills directory has no `PATH` to join — but check
  it is what you meant before adding anything there.
- **Never put anything in `plugin/` that should not reach a user.** That
  directory ships verbatim. The handoff you are reading lives in `packaging/`
  for exactly this reason.
- **Windows.** `bin/howdo-context` is extensionless with a shebang, so
  `howdo-context.cmd` beside it is what makes the affordance real there. The CI
  `plugin:` job runs on `windows-latest` for this reason. Keep both.

---

## Deliberately not done

Five plugin slots are empty on purpose.

`hooks/`, and `settings.json` with an `agent` key, would make How Do load
without being asked. `SKILL.md` *Refuses* names that directly, and its
*When this runs* section is built on being requested rather than ambient.
Adding either is a discipline change wearing packaging clothes.

`monitors/`, `.mcp.json`, and `.lsp.json` have no fit.

`agents/` is the one slot with real value: a `look-verifier` subagent given the
Check-stage prediction and the actual result, with no access to the reasoning
that produced either, would be the first *structural* mechanism behind
"you cannot test a thing by asking it whether it worked." It is not blocked on
taste — it is blocked on `experiment/ROADMAP.md`, which states that every
further edit to the skill is unfalsifiable until something measures it, and
PILOT-0001 has not run. It is also a clean second arm for that pilot. Spending
it before the pilot runs costs the discriminating power the pilot exists to
provide.

Empty here means the same thing as the empty rows in the Handles table in
`SKILL.md`: fill one when a repeated move earns a measurable residual.
