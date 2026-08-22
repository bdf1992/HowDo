# Packaging lane — handoff

Branch `claude/howdo-fullscope-plugin-handoff-2yn8w9`. Work in `647d4a0`,
handoff in `f5d400b`, both replayed onto `main`.

`claude/howdo-fullscope-plugin-qqvw7h` (draft PR #14) is where the lane
started, and it replayed onto the same `main` independently and in parallel.
Its work is merged in here; **close #14 rather than working it further**, or
the two states drift again.

This lane converts How Do into a Claude Code plugin. It is **packaging only**:
no hook, no agent, no `settings.json`, nothing that would make the discipline
ambient. That restraint is not conservatism, it is the roadmap's gate — see
*Deliberately not done* below before adding a component.

**The branch does not merge until parity is closed.** Three items were open and
none could be closed from inside this lane alone. **All three are now
resolved:** #12 landed and took item 3 with it; item 1 is closed by moving the
payload under `plugin/`; item 2 turned out not to be a packaging gap at all and
is raised as skill-text issue #18, which this lane does not wait on.

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
| Does a plugin root named something other than the plugin still invoke bare? | **Yes.** `plugin/` loads as `/how-do` | Headless probe of `claude --plugin-dir plugin` returned `/how-do`; this is row 4 holding for the committed layout |
| Is `version` required in a manifest? | **No, but its absence warns** | `claude plugin validate` on a versionless manifest: *Validation passed with warnings*. A committed manifest must carry one to keep the no-warnings bar |

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
- `tests/test_plugin.py` — 28 tests of 465. Parity is asserted **in both directions**
  against `copy_payload`'s output rather than a second file list.
- CI `plugin:` job — appended at the end of `tests.yml` deliberately, so it
  cannot conflict with in-flight edits to the `suite:` job.
- `plugin/` — the payload as a committed plugin root, with
  `.claude-plugin/plugin.json` in it and `.claude-plugin/marketplace.json` at
  the repository root pointing there. This is item 1's close; see it below for
  what the move does and does not change.

---

## Open work items

### 1. ~~Not distributable~~ — CLOSED by moving the payload under `plugin/`

A marketplace clones a repository and treats a directory as the plugin root.
The payload was *generated* into `dist/` (gitignored), so `/plugin install`
could not reach it. Two routes were on the table; the preferred one is taken.

`SKILL.md`, `CONTEXT.template.md`, `QUICKSTART.md`, `LICENSE`, `references/`,
`runtime/`, `examples/` and `bin/` now live under `plugin/`, which carries a
committed `.claude-plugin/plugin.json`. `.claude-plugin/marketplace.json` at
the repository root points at it. Both validate under `--strict` with no
warnings.

**The boundary is now a filesystem fact.** `experiment/`, `tests/`,
`packaging/` and the contributor docs sit outside `plugin/` and cannot reach a
user by any route, rather than by an assembler remembering a list.
`install.py` reads `PAYLOAD_ROOT`; `PAYLOAD` still names what an ordinary
skill directory gets, which is the plugin root minus `bin/` and the manifest —
a skill directory is not a plugin and a host finding a manifest there would be
right to be confused.

**Verified against the runtime, as the findings table demands.** A headless
probe of `claude --plugin-dir plugin` returns `/how-do`: the invocation stays
un-namespaced from a directory named `plugin`, because the manifest names the
plugin and the directory does not. That is finding 4 holding under the new
layout, and it is what makes the move safe.

The rejected route — publishing a built branch from CI — is recorded because it
is the fallback if a host ever refuses a subdirectory plugin root: run
`install.py --plugin` on push to main and push the result to a `plugin` branch.
Nothing depends on it today.

**The committed manifest is derived, not authored.** `packaging/plugin.json`
still carries no version, `install.manifest_bytes()` is still the one authority,
and `tests/test_plugin.py::DistributionTests` compares the committed file to it
byte-for-byte. A release that bumps `SKILL.md` and forgets the manifest fails
CI rather than shipping a stale version. The trap below stands unchanged: do
not put a version in `packaging/plugin.json`.

### 2. `CONFIGURATION_NOTE` never reaches a plugin user — blocks parity

`install.py` prints a person-facing note on a fresh install explaining the
onboarding conversation and both opt-outs. `tests/test_release.py::InstallerNoteTests`
guards its content carefully. A `/plugin install` never runs `install.py`, so
that note reaches nobody.

**Read the skill text before deciding this is a gap.** It was written up as a
degraded first run — the conversation still happens, the person just never got
the heads-up. Checking that against `SKILL.md` does not support it, and points
somewhere else:

- *"Onboarding gates the first substantive HowDo, not the person's first
  sentence: by the time it runs, they have already opted into the discipline."*
  The plugin user is not skipping a gate. They reach the same gate by the same
  route.
- *"Keep it a conversation between two people working out how to work together;
  it is never an intake form, and **the person should ideally not be able to
  tell an onboarding is happening**."* This is the one that matters. A note
  announcing *four things are about to be established and you may decline* is
  precisely telling them an onboarding is happening. By the skill's own
  standard the installer path is the deviation and the plugin path is the
  described ideal.
- The decline is not lost either. *Refuses* forbids "silently bypassing
  onboarding without an explicit user decline or deferral" — an explicit answer
  inside the conversation, which the routing table and the four guarantees make
  first-class. It does not require a pre-announcement.

What is genuinely lost is narrower than the item claimed: the chance to decline
*before* the conversation starts, rather than during it. Whether that is worth
having is a real question, and it is not obviously yes.

So the packaging answer is **do nothing here**, and the open question is not
"how do we deliver the note to a plugin user" but **"is `CONFIGURATION_NOTE`
doctrinally right in the first place?"** — because it and the sentence in
`SKILL.md` cannot both be. `tests/test_release.py::InstallerNoteTests` guards
the note's content carefully, which makes the tension enforced rather than
latent: the suite pins a note that pre-announces, while the skill text asks for
a conversation the person cannot detect.

That is a skill-text decision, not a packaging one, and it is raised as one in
**issue #18**, with the three ways it could go and the note that none of them
has a trace from real use behind it yet. Packaging is not blocked on the
answer: whichever way it lands, this lane does nothing differently. **Do not reach for a `SessionStart` hook**
in the meantime: a hook speaks on every session rather than once at install,
and injects context rather than printing to a console the person is watching,
which is much closer to the line *Refuses* draws at "Loading the discipline
uninvited" than the installer note ever was.

### 3. ~~The plugin ships PILOT-0001~~ — CLOSED by PR #12

`tests/test_plugin.py::ParityTests::test_the_plugin_names_no_experiment` is
**skipped, not passing.** `runtime/howdo/environment.py` is the pilot adapter
and `howdo/__init__.py` re-exports its API, so every install path — plugin and
ordinary alike — carries the experiment.

Nothing to do here. The skip condition is
`(ROOT / "runtime" / "howdo" / "environment.py").exists()`, which clears itself
when PR #12 moves the adapter to `experiment/PILOT-0001/adapter/`. Verified
that it activates: with the adapter removed the test runs and correctly flags
the remaining `__init__.py` re-exports, so it also catches a partial fix.

**Closed as of `042e431`.** #12 merged to `main` as `4c2f5e5`; this lane took
it with the one additive `CHANGELOG.md` conflict the probe had predicted, and
the suite is now **465 tests, zero skips, all passing** —
`test_the_plugin_names_no_experiment` among them.

The tripwire read stronger than it was written to. A hand-made removal of the
adapter had left the `howdo/__init__.py` re-exports behind and the test flagged
them; #12 moves the adapter *and* clears the re-exports, so the test did not
merely un-skip, it went green. Nothing was owed by this lane and nothing was
added to it. **There is no longer a sanctioned skip:** a skipped test in this
suite is now a regression, wherever it appears.

---

## Collision map

Dry-run merges as of `5c71a17`, both against `origin/main` at `f8b9236`:

| open PR | branch | conflicts with this lane |
|---|---|---|
| — | `experiment/m0-harbor-runner` | `CHANGELOG.md` |

**Every PR the original map listed has merged.** #13 (request contracts /
domain-how) as `f8b9236`, #15 (emit frontmatter, same branch) as `333c837`, and
#12 (experiment/packaging boundary) as `4c2f5e5`. Each took only the additive
conflicts the map predicted — changelog blocks and a QA-command entry — and
`install.py`, `runtime/howdo/context.py`, `SKILL.md`, `tests/`, and
`.github/workflows/tests.yml` were never contested by any of them.

What is left in flight is `experiment/m0-harbor-runner`, which lives entirely
under `experiment/` and touches `CHANGELOG.md` alone. **The tree is quiet**, so
item 1's gate is open.

The 0.9.0 bump needed **no edit here**: the manifest derives its version from
`SKILL.md`, so `--plugin` emitted 0.9.0 on its own. That is the design working;
do not add a version to `packaging/plugin.json` to "keep them in sync".

`howdo/payload-store-split` is empty against main. Stale; ignore.

**Suggested order.** Done: #13, #15, #12 all landed and this lane took them.
Item 1 is next and no longer waits on anything.

To re-check collisions after anything moves:

```bash
git checkout -B probe origin/<their-branch>
git merge --no-commit --no-ff <this-branch> || git diff --name-only --diff-filter=U
git merge --abort; git checkout <this-branch>; git branch -D probe
```

---

## Verifying this lane

```bash
python -m unittest discover -s tests -v        # 471 tests, zero skips
python plugin/examples/jira_workflow.py
python plugin/examples/portable_contract.py
python plugin/examples/issue_domain_how.py
claude plugin validate plugin --strict                        # the committed root
claude plugin validate .claude-plugin/marketplace.json --strict
python install.py --plugin dist/how-do
claude plugin validate dist/how-do             # expects: Validation passed, no warnings
python install.py --plugin dist/how-do --verify
python install.py --target /tmp/skilldir && python install.py --target /tmp/skilldir --verify
```

The probe that keeps the invocation honest, and the one to re-run after any
layout change:

```bash
claude --plugin-dir plugin -p 'Output ONLY the slash-command string that \
  invokes the How Do skill, exactly as a user would type it. Nothing else.'
# expects: /how-do   -- namespaced output means the layout renamed the skill
```

Any skip means something regressed. The one sanctioned skip was item 3 and it
is closed.

To watch it load for real:

```bash
python install.py --plugin ~/.claude/skills/how-do   # loads as how-do@skills-dir next session
claude plugin list
```

---

## Traps

- **`plugin details` showing `Skills (0)` is expected.** Host reporting gap for
  the root-`SKILL.md` layout. The skill loads. Do not restructure to fix it.
- **There is no expected skip any more.** Item 3's was the only one and #12
  closed it. The test that carried it is a tripwire that arms itself, so a skip
  reappearing means the pilot adapter is back in the payload. Do not delete the
  test to get a clean run.
- **Do not add a `version` to `packaging/plugin.json`.** It is derived. A test
  enforces this, and a pinned stale version silently blocks updates for every
  user.
- **Do not move `SKILL.md` under `skills/`.** It renames the skill. See the
  findings table.
- **`bin/` is not in `PAYLOAD`.** It ships only via `PLUGIN_EXTRA` in the
  plugin path. If you add anything to `bin/`, the ordinary install will not
  carry it — that is intentional, but check it is what you meant.
- **Anything you put in `plugin/` ships.** That is the point of the move, and
  it cuts both ways: a file added there that `PAYLOAD` does not name reaches a
  marketplace user while being silently absent from an ordinary install. A test
  fails on it rather than letting the two paths drift. Repository concerns go
  outside `plugin/`.
- **`plugin/LICENSE` is a copy of the root `LICENSE`, checked equal by test.**
  Not a symlink: a Windows checkout without symlink support would ship the link
  text as the licence. Edit both, or edit the root one and copy.
- **`plugin/.claude-plugin/plugin.json` is generated and committed.** Refresh it
  with `install.manifest_bytes()`, never by hand. The test compares bytes, so a
  hand edit that is merely equivalent still fails.
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
