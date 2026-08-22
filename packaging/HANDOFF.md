# Packaging lane — handoff

Branch `claude/howdo-fullscope-plugin-qqvw7h`, first commit `647d4a0`.

This lane converts How Do into a Claude Code plugin. It is **packaging only**:
no hook, no agent, no `settings.json`, nothing that would make the discipline
ambient. That restraint is not conservatism, it is the roadmap's gate — see
*Deliberately not done* below before adding a component.

**The branch does not merge until parity is closed.** Three items are open and
none of them can be closed from inside this lane alone. They are listed with
what unblocks each.

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
- `tests/test_plugin.py` — 28 tests. Parity is asserted **in both directions**
  against `copy_payload`'s output rather than a second file list.
- CI `plugin:` job — appended at the end of `tests.yml` deliberately, so it
  cannot conflict with in-flight edits to the `suite:` job.

---

## Open work items

### 1. Not distributable — blocks parity

A marketplace clones a repository and treats a directory as the plugin root.
Ours is *generated* into `dist/` (gitignored), so `/plugin install` cannot
reach it. Local use works today (`--plugin-dir`, or assemble into a skills
directory); distribution does not.

Two ways to close it, both cheap once the branches below have landed:

- **Move the payload under `plugin/`** and point a marketplace entry at that
  subdirectory. Cleanest end state — the boundary becomes a filesystem fact
  rather than an assembler behaviour. Deferred only because moving `SKILL.md`,
  `runtime/`, and `references/` now would conflict violently with both open
  PRs.
- **Publish a built branch from CI** — run `install.py --plugin` on every push
  to main and push the result to a `plugin` branch that the marketplace points
  at. No file moves, but the boundary stays a property of the assembler.

Prefer the first once the tree is quiet. Do not do either while PR #13 is open.

### 2. `CONFIGURATION_NOTE` never reaches a plugin user — blocks parity

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

### 3. The plugin ships PILOT-0001 — blocked on PR #12

`tests/test_plugin.py::ParityTests::test_the_plugin_names_no_experiment` is
**skipped, not passing.** `runtime/howdo/environment.py` is the pilot adapter
and `howdo/__init__.py` re-exports its API, so every install path — plugin and
ordinary alike — carries the experiment.

Nothing to do here. The skip condition is
`(ROOT / "runtime" / "howdo" / "environment.py").exists()`, which clears itself
when PR #12 moves the adapter to `experiment/PILOT-0001/adapter/`. Verified
that it activates: with the adapter removed the test runs and correctly flags
the remaining `__init__.py` re-exports, so it also catches a partial fix.

---

## Collision map

Dry-run merges as of `647d4a0`, both against `origin/main` at `c721c39`:

| open PR | branch | conflicts with this lane |
|---|---|---|
| **#12** experiment/packaging boundary | `claude/skill-graph-benchmark-index-s1vxax` | `CHANGELOG.md` |
| **#13** request contracts / domain-how | `claude/how-do-request-contract-3jqsr1` | `CHANGELOG.md`, `README.md` |

No conflicts in `install.py`, `runtime/howdo/context.py`, `SKILL.md`,
`tests/`, or `.github/workflows/tests.yml`. Both remaining conflicts are
additive — a changelog block and two list entries.

`howdo/payload-store-split` is empty against main. Stale; ignore.

**Suggested order.** Let #12 land first (item 3 closes for free). Then #13 —
note it moves the release to 0.9.0, and because the manifest derives its
version from `SKILL.md` there is nothing extra to bump here. Rebase this lane
onto the result, then do item 1.

To re-check collisions after anything moves:

```bash
git checkout -B probe origin/<their-branch>
git merge --no-commit --no-ff <this-branch> || git diff --name-only --diff-filter=U
git merge --abort; git checkout <this-branch>; git branch -D probe
```

---

## Verifying this lane

```bash
python -m unittest discover -s tests -v        # 206 tests, exactly 1 skip (item 3)
python examples/jira_workflow.py
python install.py --plugin dist/how-do
claude plugin validate dist/how-do             # expects: Validation passed, no warnings
python install.py --plugin dist/how-do --verify
python install.py --target /tmp/skilldir && python install.py --target /tmp/skilldir --verify
```

A second skip means something regressed — item 3 is the only sanctioned one.

To watch it load for real:

```bash
python install.py --plugin ~/.claude/skills/how-do   # loads as how-do@skills-dir next session
claude plugin list
```

---

## Traps

- **`plugin details` showing `Skills (0)` is expected.** Host reporting gap for
  the root-`SKILL.md` layout. The skill loads. Do not restructure to fix it.
- **The single skip is expected.** See item 3. Do not delete the test to get a
  clean run; it is a tripwire that arms itself.
- **Do not add a `version` to `packaging/plugin.json`.** It is derived. A test
  enforces this, and a pinned stale version silently blocks updates for every
  user.
- **Do not move `SKILL.md` under `skills/`.** It renames the skill. See the
  findings table.
- **`bin/` is not in `PAYLOAD`.** It ships only via `PLUGIN_EXTRA` in the
  plugin path. If you add anything to `bin/`, the ordinary install will not
  carry it — that is intentional, but check it is what you meant.
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
