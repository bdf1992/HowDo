"""Environment-kind context: the PILOT-0001 adapter.

How Do's durable context is person-derived and says so: a pedagogy "cannot be
generated" because it has no source but the person. A benchmark agent has no
person, so synthesizing one would fabricate exactly the evidence completion
exists to require — and completion is structural, so the fake would pass.

This module adds the other kind instead. An environment context records
independently inspectable facts about where the work happens: what exists, what
ordering the environment imposes, what constitutes verification, and who holds
write authority. It is obtained by looking, because an environment's affordances
are observable in the way a pedagogy is not.

The kinds are disjoint. Neither validator can be satisfied by the other's file.

Lifetime and write authority are independent of kind, so that "environment"
never silently implies "ephemeral". During a pilot only two combinations are
admissible; see :func:`assert_pilot_admissible`.

This is an experiment adapter, not part of the discipline. It lives under
``experiment/`` rather than in ``runtime/howdo`` so the boundary is a fact
about the filesystem and not a claim in a document: an ordinary How Do install
copies ``runtime/`` and therefore cannot contain any of this.

Declared dependency: this module imports private helpers from
``howdo.context`` (frontmatter parsing, section replacement, placeholder
tables). That coupling is deliberate and one-directional. ``howdo.context``
knows about context *kinds* generically and knows nothing about PILOT-0001;
this module knows about PILOT-0001 and reaches into the kernel. If the kernel's
private helpers change, this adapter breaks and the skill does not.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import hashlib
import re
import stat

from howdo.context import (
    AUTHORITY_READONLY,
    AUTHORITY_WRITABLE,
    ContextKindError,
    ContextStatus,
    KIND_ENVIRONMENT,
    KIND_PERSON,
    LIFETIME_EPHEMERAL,
    LIFETIME_FROZEN,
    LIFETIME_PERSISTENT,
    SKILL_VERSION,
    TemplateContextError,
    _PLACEHOLDERS,
    _PLACEHOLDER_PREFIXES,
    _UNSET,
    _drop_frontmatter_keys,
    _frontmatter,
    _is_template,
    _replace_section,
    _set_frontmatter,
    _strip_template_block,
    _TEMPLATE_KEY,
    context_kind,
    context_lifetime,
    inspect_context,
    new_context_id,
    write_authority,
)

__all__ = [
    "FrozenContext",
    "PilotAdmissibilityError",
    "ReconReceipt",
    "TrialClosure",
    "PILOT_ADMISSIBLE",
    "assert_pilot_admissible",
    "close_trial_context",
    "complete_reconnaissance",
    "describe_frozen",
    "freeze_context",
    "open_trial_context",
]

_SECTIONS = {
    "available_ground": "Available ground",
    "imposed_ordering": "Imposed ordering",
    "verification_mechanisms": "Verification mechanisms",
    "authority_boundaries": "Mutation and authority boundaries",
}
_NOTES_SECTION = "Reconnaissance notes"
_READONLY_MODE = 0o444


class PilotAdmissibilityError(ValueError):
    """A context configuration the pilot protocol does not admit.

    The type system allows every kind/lifetime/authority combination because
    they are orthogonal. The *protocol* admits two. Persistent accumulating
    context is the one that matters: it would let trial N+1 inherit what trial N
    learned, and repeated-trial independence is the assumption the whole
    five-trial design rests on.
    """


class FrozenContextError(ValueError):
    """A write was attempted against a context that is frozen or read-only."""


@dataclass(frozen=True)
class ReconReceipt:
    """What one reconnaissance pass observed, structured on the loop.

    Environmental ground only: what would be true of this environment whatever
    the task was. Not task learning, not a partial solution. Nothing here can
    check that — the boundary is the procedure's, and the structural validator
    says as much.
    """

    available_ground: str          # Map    — what exists, what can be inspected
    imposed_ordering: str          # Path   — what ordering the environment imposes
    verification_mechanisms: str   # Check  — what independently establishes success
    authority_boundaries: str      # Update — what is mutable, canonical, writable
    notes: str | None = None

    def evidence(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in _SECTIONS}


@dataclass(frozen=True)
class FrozenContext:
    """An environment context whose immutability is externally inspectable.

    ``frozen`` is not a promise made to the agent. The digest lets any receipt
    prove which bytes were in play, and the file is dropped to read-only so the
    property is visible to the operating system rather than only to this
    library. The harness should additionally deliver it through a read-only
    mount: the permission bit is the in-band signal, the mount is the boundary.
    """

    path: Path
    digest: str
    source: str
    created_from: str
    byte_length: int
    readonly: bool = True


@dataclass(frozen=True)
class TrialClosure:
    """What was destroyed when a trial ended, so a receipt can attest to it."""

    trial_id: str
    digest: str
    byte_length: int


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean(value: str) -> str:
    return re.sub(r"[\r\n]+", " ", value).strip()


def _require_observation(name: str, value: str) -> str:
    cleaned = _clean(value)
    lowered = cleaned.lower()
    if not cleaned or lowered in _PLACEHOLDERS or lowered.startswith(_PLACEHOLDER_PREFIXES):
        raise ValueError(f"{name} must contain an observation from reconnaissance")
    return cleaned


def _require_environment(path: Path, metadata: Mapping[str, str]) -> None:
    if context_kind(metadata) != KIND_ENVIRONMENT:
        raise ContextKindError(
            f"{path} is a {context_kind(metadata)} context; reconnaissance settles "
            f"environmental ground, which a person context does not record"
        )


def _refuse_write(path: Path, metadata: Mapping[str, str]) -> None:
    lifetime = context_lifetime(metadata)
    authority = write_authority(metadata)
    if lifetime == LIFETIME_FROZEN or authority == AUTHORITY_READONLY:
        raise FrozenContextError(
            f"{path} is lifetime={lifetime} write_authority={authority}; a frozen "
            f"or read-only context cannot be settled. Take a fresh reconnaissance "
            f"pass into a writable trial context instead."
        )


def open_trial_context(
    destination: str | Path,
    *,
    template: str | Path,
    trial_id: str,
) -> ContextStatus:
    """Instantiate an ephemeral environment context bound to one trial.

    The binding is the contamination control. An ephemeral context cannot be
    read without asserting which trial is reading, so a reused volume or a
    recycled container reports ``expired`` instead of quietly handing trial N's
    reconnaissance to trial N+1.
    """
    if not str(trial_id).strip() or str(trial_id).strip() in _UNSET:
        raise ValueError("an ephemeral context requires a concrete trial_id")

    dst = Path(destination).expanduser()
    if dst.exists():
        raise FileExistsError(
            f"{dst} already exists; a trial context is created once and destroyed "
            f"with its trial"
        )

    source = Path(template).expanduser()
    if not source.exists():
        raise FileNotFoundError(source)

    text = source.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    if not metadata:
        raise ValueError("template requires flat YAML frontmatter")
    _require_environment(source, metadata)

    text = _drop_frontmatter_keys(text, {_TEMPLATE_KEY})
    text = _strip_template_block(text)
    text = _set_frontmatter(
        text,
        {
            "context_kind": KIND_ENVIRONMENT,
            "context_id": "pending",
            "context_file": dst.name,
            "skill_version": f'"{SKILL_VERSION}"',
            "reconnaissance": "required",
            "parent_context_id": "none",
            "lifetime": LIFETIME_EPHEMERAL,
            "write_authority": AUTHORITY_WRITABLE,
            "trial_id": str(trial_id).strip(),
        },
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return inspect_context(dst, trial_id=trial_id)


def complete_reconnaissance(
    path: str | Path,
    receipt: ReconReceipt,
    *,
    trial_id: str | None = None,
) -> Path:
    """Settle an environment context from a reconnaissance receipt.

    Structural only, exactly as person onboarding is. This establishes that each
    of the four sections holds non-placeholder material. It does not establish
    that the observations are true, and it cannot tell an observation about the
    environment from a conclusion about the task.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    text = p.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    if _is_template(metadata):
        raise TemplateContextError(
            f"{p} is the shipped template; open a trial context with "
            f"open_trial_context() and settle that instead"
        )
    _require_environment(p, metadata)
    _refuse_write(p, metadata)

    values = {
        name: _require_observation(name, getattr(receipt, name)) for name in _SECTIONS
    }

    status = inspect_context(p, trial_id=trial_id)
    if status.state == "expired":
        raise ValueError(status.reason)
    if status.state == "fork_required":
        raise ValueError("fork must be normalized before reconnaissance can settle")
    if status.state == "invalid":
        raise ValueError(status.reason)
    if status.state == "ready":
        raise ValueError("environment context is already settled")

    for name, heading in _SECTIONS.items():
        text = _replace_section(text, heading, f"- {values[name]}")
    if receipt.notes:
        text = _replace_section(text, _NOTES_SECTION, f"- {_clean(receipt.notes)}")

    text = _set_frontmatter(
        text,
        {
            "context_id": new_context_id(),
            "context_file": p.name,
            "reconnaissance": "complete",
        },
    )
    p.write_text(text, encoding="utf-8")
    return p


def close_trial_context(path: str | Path, *, trial_id: str) -> TrialClosure:
    """Destroy a trial's ephemeral context and attest to what was destroyed.

    The container usually takes the file with it. Doing it explicitly means the
    evidence receipt can carry the digest of the context that was in play, so a
    later reader can tell that trial N's ground was not trial N+1's.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    metadata = _frontmatter(p.read_text(encoding="utf-8"))
    _require_environment(p, metadata)
    if context_lifetime(metadata) != LIFETIME_EPHEMERAL:
        raise ValueError(
            f"{p} is lifetime={context_lifetime(metadata)}; only an ephemeral "
            f"context is destroyed at a trial boundary"
        )
    bound = metadata.get("trial_id")
    if bound != trial_id:
        raise ValueError(
            f"{p} belongs to trial {bound!r}, not {trial_id!r}; refusing to close "
            f"another trial's context"
        )

    data = p.read_bytes()
    closure = TrialClosure(trial_id=trial_id, digest=_digest(data), byte_length=len(data))
    p.chmod(stat.S_IWRITE | stat.S_IREAD)
    p.unlink()
    return closure


def freeze_context(source: str | Path, destination: str | Path) -> FrozenContext:
    """Derive a read-only environment context from a settled one.

    The result is the H2 treatment's ground: byte-identical across every trial
    that uses it, with a digest that belongs in each of their receipts. It is a
    new lineage, parented to the context it was taken from — freezing a pass
    does not retroactively make that pass immutable.
    """
    src = Path(source).expanduser()
    dst = Path(destination).expanduser()
    if not src.exists():
        raise FileNotFoundError(src)
    if dst.exists():
        raise FileExistsError(dst)

    text = src.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    _require_environment(src, metadata)
    if _is_template(metadata):
        raise TemplateContextError(f"{src} is a template, not a settled lineage")

    status = inspect_context(src, trial_id=metadata.get("trial_id"))
    if status.state != "ready":
        raise ValueError(
            f"only a settled environment context can be frozen; {src} is "
            f"{status.state}: {status.reason}"
        )

    created_from = metadata.get("context_id", "unknown")
    text = _set_frontmatter(
        text,
        {
            "context_id": new_context_id(),
            "context_file": dst.name,
            "parent_context_id": created_from,
            "lifetime": LIFETIME_FROZEN,
            "write_authority": AUTHORITY_READONLY,
            "trial_id": "none",
        },
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    data = dst.read_bytes()
    dst.chmod(_READONLY_MODE)
    return FrozenContext(
        path=dst,
        digest=_digest(data),
        source=str(src),
        created_from=created_from,
        byte_length=len(data),
    )


def describe_frozen(path: str | Path) -> FrozenContext:
    """Recompute a frozen context's descriptor, for verifying a receipt.

    ``readonly`` reports the filesystem, not the frontmatter. A context that
    declares itself frozen while sitting on a writable file is exactly the
    discrepancy this is for.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    metadata = _frontmatter(p.read_text(encoding="utf-8"))
    _require_environment(p, metadata)
    if context_lifetime(metadata) != LIFETIME_FROZEN:
        raise ValueError(f"{p} is lifetime={context_lifetime(metadata)}, not frozen")

    data = p.read_bytes()
    mode = p.stat().st_mode
    writable = bool(mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    return FrozenContext(
        path=p,
        digest=_digest(data),
        source=str(p),
        created_from=metadata.get("parent_context_id", "unknown"),
        byte_length=len(data),
        readonly=not writable,
    )


PILOT_ADMISSIBLE = frozenset(
    {
        (KIND_ENVIRONMENT, LIFETIME_EPHEMERAL, AUTHORITY_WRITABLE),
        (KIND_ENVIRONMENT, LIFETIME_FROZEN, AUTHORITY_READONLY),
    }
)


def assert_pilot_admissible(path: str | Path) -> tuple[str, str, str]:
    """Raise unless this context may take part in a pilot trial.

    Returns the admitted ``(kind, lifetime, write_authority)`` triple.

    A person context is inadmissible inside a trial. That is deliberate: the
    pilot's treatment is the loop plus environment context, and the person half
    of How Do is not present in any arm. Making it a mechanical refusal stops a
    pedagogy being carried into the organism by accident.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    metadata = _frontmatter(p.read_text(encoding="utf-8"))
    triple = (context_kind(metadata), context_lifetime(metadata), write_authority(metadata))

    if triple in PILOT_ADMISSIBLE:
        return triple

    kind, lifetime, authority = triple
    if kind == KIND_PERSON:
        raise PilotAdmissibilityError(
            f"{p} is a person context; the pilot treatment carries no pedagogy and "
            f"a person context is inadmissible inside a trial"
        )
    if lifetime == LIFETIME_PERSISTENT:
        raise PilotAdmissibilityError(
            f"{p} is persistent; later trials would inherit what earlier trials "
            f"learned, and repeated-trial independence is what the design rests on"
        )
    raise PilotAdmissibilityError(
        f"{p} is ({kind}, {lifetime}, {authority}); the pilot admits "
        f"{sorted(PILOT_ADMISSIBLE)}"
    )
