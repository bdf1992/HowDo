"""Render an issued domain-how as an installable Agent Skill or Claude Code workflow.

The issuer produces a durable artifact. This projects one into the two formats a
host can actually load: a `SKILL.md` bundle per the Agent Skills specification,
and a dynamic-workflow script for `.claude/workflows/`.

Emission is a *projection*, never a second artifact. Nothing here is stored back
into the index, by the rule that governs every derived view in this runtime:
what can be recomputed is recomputed, and only what cannot is frozen. Re-emit
whenever the domain-how moves.

One refusal shapes the module. An untested domain-how is not emitted without an
explicit override, because a `SKILL.md` on disk is loaded by every future
session on that concern -- which is where a minted artifact compounds what a
spoken one does not: a wrong answer said once is heard once, while a wrong
answer written to disk is re-read by everything that comes after. The override
exists for review, and it stamps the output so a reader cannot mistake a draft
for settled ground.

Format constraints come from the two specifications, not from taste:

* Agent Skills -- a skill lives at `<root>/<name>/SKILL.md`, and `name` is
  lowercase letters, digits and hyphens, at most 64 characters, with no leading
  or trailing hyphen. Claude Code treats `name` as a display name defaulting to
  the directory name, so emitting the two identical is what satisfies both
  readings. Angle brackets are kept out of frontmatter because they can inject
  instructions into a system prompt.
* Dynamic workflows -- a `meta` object literal, then plain JavaScript with no
  module loading, and `meta.phases` titles matching the `phase()` calls.

**Two frontmatter targets, because they are not the same set.** Outside Claude
Code -- claude.ai uploads, the Skills API, `package_skill.py` -- only the Agent
Skills spec's six fields are accepted, and *any* other key fails packaging with
a hard error rather than being ignored. Inside Claude Code every documented
field works. `target="spec"` therefore emits only `name`, `description`,
`license`, `compatibility`, `metadata`, and `allowed-tools`; `target="claude-code"`
may add extensions.

The extension that matters is `disable-model-invocation`. A domain-how whose
contract is consequential describes an operation with side effects, and the
Claude Code documentation names exactly that case: use it "for workflows with
side effects or that you want to control timing, like `/commit`, `/deploy`".
That is also How Do's own doctrine -- requested, not ambient -- so a
consequential artifact emitted for Claude Code is not left auto-invocable. The
spec target cannot say this, and `render_skill` says so in the body instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import json
import re

from .contract import Field, Shape
from .domain import STATUS_GROUNDED, DomainError, DomainHow

__all__ = [
    "MAX_COMPATIBILITY",
    "MAX_DESCRIPTION",
    "MAX_NAME",
    "SPEC_FIELDS",
    "TARGET_CLAUDE_CODE",
    "TARGET_SPEC",
    "EmitError",
    "SkillBundle",
    "WorkflowScript",
    "render_skill",
    "render_workflow",
    "skill_name",
    "write_skill",
    "write_workflow",
]

#: Agent Skills: `name` caps at 64 characters.
MAX_NAME = 64
#: Agent Skills: `description` caps at 1024 characters. Claude Code truncates the
#: combined `description` + `when_to_use` at 1536 in its skill listing, which is a
#: display limit rather than a validation one -- so 1024 is the safe intersection
#: and the only cap that cannot fail a packaging step.
MAX_DESCRIPTION = 1024
#: Agent Skills: `compatibility` caps at 500 characters.
MAX_COMPATIBILITY = 500

#: The six fields the Agent Skills spec accepts. Anything else is a hard error on
#: claude.ai upload, the Skills API, and `package_skill.py`.
SPEC_FIELDS = (
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
)

TARGET_SPEC = "spec"
TARGET_CLAUDE_CODE = "claude-code"
_TARGETS = (TARGET_SPEC, TARGET_CLAUDE_CODE)

_SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Angle brackets in frontmatter can inject instructions into a system prompt.
_FRONTMATTER_UNSAFE = re.compile(r"[<>]")


class EmitError(ValueError):
    """An artifact that cannot be rendered into a loadable form honestly."""


def _guard(how: DomainHow, allow_untested: bool) -> None:
    if not isinstance(how, DomainHow):
        raise EmitError(f"expected a DomainHow, got {type(how).__name__}")
    if how.status != STATUS_GROUNDED and not allow_untested:
        raise EmitError(
            f"{how.concern!r} is {how.status}: emitting it installs an artifact that "
            "pre-loads every later session on this concern, on the strength of a run "
            "nothing confirmed. Ground it, or pass allow_untested=True for review."
        )


def skill_name(concern: str) -> str:
    """Project a concern onto a legal Agent Skills name.

    A concern may contain dots and underscores; a skill name may not. The
    projection is lossy on purpose and validated afterwards rather than trusted,
    because a name that does not match its directory is not loadable at all.
    """

    candidate = re.sub(r"[^a-z0-9]+", "-", concern.lower()).strip("-")
    candidate = re.sub(r"-{2,}", "-", candidate)
    if not candidate:
        raise EmitError(f"{concern!r} projects to an empty skill name")
    if len(candidate) > MAX_NAME:
        raise EmitError(
            f"{concern!r} projects to a {len(candidate)}-character name; the "
            f"specification caps it at {MAX_NAME}"
        )
    if not _SKILL_NAME.match(candidate):
        raise EmitError(f"{concern!r} projects to {candidate!r}, which is not a legal name")
    return candidate


def _yaml_scalar(value: str) -> str:
    """Quote a frontmatter value so a YAML parser accepts it.

    A plain scalar may not contain ": ", may not end in ":", and may not open
    with an indicator character. A generated description says things like
    "not a general-purpose helper: an unrelated question ...", which is exactly
    the first case -- and an unparseable frontmatter block is a hard failure on
    the packaging and upload paths, not a cosmetic problem. Double-quoting is
    valid for any content, so it is applied unconditionally rather than only
    when a scan thinks it is needed.
    """

    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _frontmatter_safe(name: str, value: str) -> str:
    cleaned = _FRONTMATTER_UNSAFE.sub("", value).replace("\n", " ").strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    if not cleaned:
        raise EmitError(f"{name} is empty once frontmatter-unsafe characters are removed")
    return cleaned


def _describe_shape(shape: Shape) -> list[str]:
    return [_describe_field(item) for item in shape.fields]


def _describe_field(item: Field) -> str:
    kind = f"list of {item.of}" if item.of else item.type
    suffix = "" if item.required else " (optional)"
    note = f" — {item.description}" if item.description else ""
    return f"`{item.name}`: {kind}{suffix}{note}"


def _render_map(value: Any, indent: int = 0) -> list[str]:
    pad = "  " * indent
    if isinstance(value, Mapping):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (Mapping, list)):
                lines.append(f"{pad}- **{key}**")
                lines.extend(_render_map(item, indent + 1))
            else:
                lines.append(f"{pad}- **{key}** — {item}")
        return lines
    if isinstance(value, list):
        return [f"{pad}- {item}" for item in value]
    return [f"{pad}- {value}"]


@dataclass(frozen=True)
class SkillBundle:
    """A rendered Agent Skill: the directory name and the `SKILL.md` it contains."""

    name: str
    description: str
    body: str
    #: Whether Claude may load this on its own. Reported rather than buried,
    #: because it is the person's call and they should be able to see it.
    auto_invocable: bool = True
    #: ``"user"`` when the caller decided, ``"default"`` when nobody did and the
    #: contract's consequences decided for them. A default is a prompt to ask,
    #: not a settled answer.
    invocation_chosen_by: str = "default"

    @property
    def text(self) -> str:
        return self.body


@dataclass(frozen=True)
class WorkflowScript:
    """A rendered dynamic workflow: the command name and the script source."""

    name: str
    source: str


def render_skill(
    how: DomainHow,
    *,
    allow_untested: bool = False,
    target: str = TARGET_SPEC,
    license: str | None = None,
    disable_model_invocation: bool | None = None,
) -> SkillBundle:
    """Render an issued domain-how as a `SKILL.md` bundle.

    The body carries what the artifact holds -- the map, the workflow, the gate,
    the observable result, and the run it was issued from -- plus the honest
    limit of what grounding proved, which is one matching run and not
    correctness.

    ``target`` decides which frontmatter fields may appear. ``"spec"`` keeps to
    the six the Agent Skills specification accepts, so the bundle survives
    packaging and upload; ``"claude-code"`` additionally marks a consequential
    artifact `disable-model-invocation: true`, which the spec target cannot say
    and which the body states in prose instead.

    ``license`` is emitted only when given: the issuer knows how the artifact was
    produced, not what licence covers the domain knowledge in it.

    ``disable_model_invocation`` is the person's call, not the issuer's. Whoever
    worked the concern out was in the room for it, and they are the one who knows
    whether this is something Claude should be able to reach for unprompted.
    ``None`` falls back to the contract's consequences -- a fallback, reported as
    ``invocation_chosen_by == "default"`` so a caller can put the question to
    them rather than let it stand silently.
    """

    if target not in _TARGETS:
        raise EmitError(f"unknown target {target!r}; expected one of {_TARGETS}")
    if disable_model_invocation is not None and not isinstance(disable_model_invocation, bool):
        raise EmitError("disable_model_invocation is a decision: True, False, or None")
    _guard(how, allow_untested)
    name = skill_name(how.concern)
    contract = how.contract

    caps = ", ".join(contract.requires) if contract.requires else "no special capability"
    description = _frontmatter_safe(
        "description",
        f"{contract.intent}. Use when the request is about {how.concern} specifically "
        f"and that concern is named or clearly implied; the procedure runs "
        f"{contract.path[0]} through {contract.path[-1]}, and needs {caps}. "
        f"Issued by How Do from an observed run, not a general-purpose helper: an "
        f"unrelated question about this domain is not by itself a reason to load it.",
    )
    if len(description) > MAX_DESCRIPTION:
        description = description[: MAX_DESCRIPTION - 1].rstrip() + "."

    # `name` is charset-guaranteed safe as a plain scalar; the rest are not.
    lines = ["---", f"name: {name}", f"description: {_yaml_scalar(description)}"]
    if license is not None:
        lines.append(f"license: {_yaml_scalar(_frontmatter_safe('license', license))}")
    if contract.requires:
        compatibility = _frontmatter_safe(
            "compatibility",
            "Requires a host offering: " + ", ".join(contract.requires) + ".",
        )
        if len(compatibility) > MAX_COMPATIBILITY:
            raise EmitError(
                f"compatibility is {len(compatibility)} characters; the specification "
                f"caps it at {MAX_COMPATIBILITY}"
            )
        lines.append(f"compatibility: {_yaml_scalar(compatibility)}")
    # The person decides; the contract's consequences only stand in when nobody has.
    chosen_by = "default" if disable_model_invocation is None else "user"
    disabled = (
        contract.consequential if disable_model_invocation is None else disable_model_invocation
    )
    if target == TARGET_CLAUDE_CODE and disabled:
        lines.append("disable-model-invocation: true")
    lines += [
        "metadata:",
        '  issued_by: "how-do"',
        f'  concern: "{how.concern}"',
        f'  revision: "{how.revision}"',
        f'  status: "{how.status}"',
        f'  digest: "{how.digest()[:16]}"',
        "---",
        "",
        f"# {how.concern}",
        "",
        contract.intent + ".",
        "",
    ]
    if disabled and target == TARGET_SPEC:
        lines += [
            "> **Invoke this deliberately.** It should not be loaded because a "
            "conversation drifted near the topic. Outside Claude Code the "
            "frontmatter cannot enforce that; treat this paragraph as the "
            "instruction.",
            "",
        ]

    if how.status == STATUS_GROUNDED:
        lines += [
            f"Issued by How Do from a run that was observed to match, at paradigm "
            f"revision {how.observed_against} (observer: {how.grounded_by}). That is "
            "one confirming run — it is not a claim that this is the best route, only "
            "that this route was taken and its result was checked.",
            "",
        ]
    else:
        lines += [
            "> **Untested.** This was issued but no observed run has confirmed it. "
            "Treat every step below as a proposal, not as settled ground.",
            "",
        ]

    lines += ["## Map", "", *_render_map(how.map), ""]
    lines += ["## Workflow", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(contract.path, 1)]
    lines += [""]

    preconditions = [r for r in contract.rules if r.kind == "precondition"]
    invariants = [r for r in contract.rules if r.kind == "invariant"]

    if preconditions:
        lines += ["## Check before acting", ""]
        lines += [f"- **{r.name}** — {r.description} (`{r.clause.describe()}`)" for r in preconditions]
        lines += ["", "If any of these cannot be established from real state, stop. "
                  "The crossing never became admissible; that is not a failed attempt.", ""]
    if invariants:
        lines += ["## Must stay true throughout", ""]
        lines += [f"- **{r.name}** — {r.description} (`{r.clause.describe()}`)" for r in invariants]
        lines += [""]

    if contract.accepts:
        lines += ["## Inputs", "", *[f"- {d}" for d in _describe_shape(contract.accepts)], ""]
    if contract.expects:
        lines += [
            "## What must be observable afterwards",
            "",
            *[f"- {d}" for d in _describe_shape(contract.expects)],
            "",
            "Observe the actual state. A report that the step ran is not evidence "
            "that it worked.",
            "",
        ]
    if contract.requires:
        lines += ["## Requires", "", *[f"- `{c}`" for c in contract.requires], ""]

    lines += [
        "## Worked example",
        "",
        "From the run this was issued from.",
        "",
        "```json",
        json.dumps(how.example.as_dict(), indent=2, sort_keys=True),
        "```",
        "",
    ]

    return SkillBundle(
        name=name,
        description=description,
        body="\n".join(lines).rstrip() + "\n",
        auto_invocable=not disabled,
        invocation_chosen_by=chosen_by,
    )


def render_workflow(how: DomainHow, *, allow_untested: bool = False) -> WorkflowScript:
    """Render an issued domain-how as a dynamic-workflow script.

    The loop is the structure: the gate is checked before anything acts, the path
    runs as ordered phases, and a final phase observes the world rather than
    reading back what the acting agents reported.
    """

    _guard(how, allow_untested)
    name = skill_name(how.concern)
    contract = how.contract

    def js(value: Any) -> str:
        """JSON is a JavaScript literal subset, so this escapes safely."""
        return json.dumps(value, ensure_ascii=False)

    preconditions = [r for r in contract.rules if r.kind == "precondition"]
    invariants = [r for r in contract.rules if r.kind == "invariant"]
    gate = [f"{r.name}: {r.description} ({r.clause.describe()})" for r in preconditions]
    holds = [f"{r.name}: {r.description} ({r.clause.describe()})" for r in invariants]
    observable = _describe_shape(contract.expects)

    description = _frontmatter_safe(
        "description", f"{contract.intent} ({how.concern}, r{how.revision})"
    )

    header = "" if how.status == STATUS_GROUNDED else (
        "// UNTESTED: issued but never confirmed by an observed run. Review before use.\n"
    )

    source = f"""{header}// Generated by How Do from domain-how {js(how.concern)} r{how.revision}
// ({how.status}, digest {how.digest()[:16]}). Re-emit rather than editing:
// the artifact is the source, this script is a projection of it.

export const meta = {{
  name: {js(name)},
  description: {js(description)},
  phases: [
    {{ title: 'Check', detail: 'establish the gate before anything acts' }},
    {{ title: 'Do', detail: {js(' -> '.join(contract.path))} }},
    {{ title: 'Look', detail: 'observe the world and compare against the prediction' }},
  ],
}}

const MAP = {json.dumps(dict(how.map), indent=2, sort_keys=True)}
const GATE = {json.dumps(gate, indent=2)}
const INVARIANTS = {json.dumps(holds, indent=2)}
const OBSERVABLE = {json.dumps(observable, indent=2)}
const STEPS = {json.dumps(list(contract.path), indent=2)}
const REQUIRES = {json.dumps(list(contract.requires), indent=2)}

const target = args ? JSON.stringify(args) : 'the target named in the conversation'

phase('Check')
const gate = await agent(
  `Establish whether this work is admissible. Target: ${{target}}.

Map of the concern:
${{JSON.stringify(MAP, null, 2)}}

Every one of these must be established from real state, not assumed:
${{GATE.map(g => `- ${{g}}`).join('\\n')}}

Capabilities this needs: ${{REQUIRES.join(', ') || 'none'}}.

Report what you actually checked and where you read it from. If any of it cannot
be established, say so and do not propose a workaround: an inadmissible crossing
is not a failed attempt, and reporting it as one hides the missing evidence.`,
  {{ label: 'gate', phase: 'Check', schema: {{
    type: 'object',
    required: ['admissible', 'findings'],
    properties: {{
      admissible: {{ type: 'boolean' }},
      findings: {{ type: 'array', items: {{ type: 'string' }} }},
      missing: {{ type: 'array', items: {{ type: 'string' }} }},
    }},
  }} }},
)

if (!gate || !gate.admissible) {{
  log('gate closed: ' + ((gate && gate.missing) || ['no gate result']).join('; '))
  return {{ fizzled: true, missing: (gate && gate.missing) || ['no gate result'] }}
}}

phase('Do')
const done = []
for (const step of STEPS) {{
  const result = await agent(
    `Carry out this step: ${{step}}

Target: ${{target}}. Steps already completed: ${{done.length ? done.join('; ') : 'none'}}.

These must remain true throughout; stop and report rather than breaking one:
${{INVARIANTS.map(i => `- ${{i}}`).join('\\n') || '- (none declared)'}}

Report what you changed and where. Do not report success you have not checked.`,
    {{ label: step, phase: 'Do' }},
  )
  done.push(step)
  if (!result) break
}}

phase('Look')
const observed = await agent(
  `Observe the resulting state directly and independently. Target: ${{target}}.

Do NOT read back what the previous agents reported. Go to the source and look.

These must be observably true:
${{OBSERVABLE.map(o => `- ${{o}}`).join('\\n')}}

And these must still hold:
${{INVARIANTS.map(i => `- ${{i}}`).join('\\n') || '- (none declared)'}}

Report what you found, then the difference between that and what was predicted.
The difference is the result of this workflow; a report that says only "it
worked" has not run the test.`,
  {{ label: 'observe', phase: 'Look', schema: {{
    type: 'object',
    required: ['matched', 'observed', 'residual'],
    properties: {{
      matched: {{ type: 'boolean' }},
      observed: {{ type: 'object' }},
      residual: {{ type: 'string' }},
      brokenInvariants: {{ type: 'array', items: {{ type: 'string' }} }},
    }},
  }} }},
)

return {{ concern: {js(how.concern)}, steps: done, gate, observed }}
"""
    return WorkflowScript(name=name, source=source)


def write_skill(
    how: DomainHow,
    root: str | Path,
    *,
    allow_untested: bool = False,
    overwrite: bool = False,
    target: str = TARGET_SPEC,
    license: str | None = None,
    disable_model_invocation: bool | None = None,
) -> Path:
    """Write a rendered skill to ``<root>/<name>/SKILL.md``.

    The directory is named for the skill, so the layout is not the caller's to
    choose: Claude Code defaults an absent `name` to the directory name, and the
    specification pins the two together.
    """

    bundle = render_skill(
        how,
        allow_untested=allow_untested,
        target=target,
        license=license,
        disable_model_invocation=disable_model_invocation,
    )
    directory = Path(root).expanduser() / bundle.name
    target = directory / "SKILL.md"
    if target.exists() and not overwrite:
        raise EmitError(f"{target} already exists; pass overwrite=True to replace it")
    directory.mkdir(parents=True, exist_ok=True)
    target.write_text(bundle.body, encoding="utf-8")
    return target


def write_workflow(
    how: DomainHow,
    root: str | Path,
    *,
    allow_untested: bool = False,
    overwrite: bool = False,
) -> Path:
    """Write a rendered workflow to ``<root>/<name>.js``."""

    script = render_workflow(how, allow_untested=allow_untested)
    directory = Path(root).expanduser()
    target = directory / f"{script.name}.js"
    if target.exists() and not overwrite:
        raise EmitError(f"{target} already exists; pass overwrite=True to replace it")
    directory.mkdir(parents=True, exist_ok=True)
    target.write_text(script.source, encoding="utf-8")
    return target
