"""Small helpers for the How Do durable context contract.

The skill remains usable without this module, but these helpers make the
first-run, completion, and rename/fork semantics inspectable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping
import os
import re
import uuid


ContextState = Literal[
    "missing",
    "onboarding_required",
    "ready",
    "declined",
    "fork_required",
    "invalid",
]

_REQUIRED_META = {
    "howdo_context",
    "context_id",
    "context_file",
    "skill",
    "skill_version",
    "onboarding",
    "parent_context_id",
}
_REQUIRED_SECTIONS = (
    "Calibration domains",
    "Representation observations",
    "Structures that landed",
    "Structures that did not land",
)
_PLACEHOLDERS = {"", "pending", "none", "none yet", "- pending", "- none yet"}
_PLACEHOLDER_PREFIXES = ("pending", "none yet")

_STORE_ENV = "HOWDO_CONTEXT"
_STORE_DIRNAME = ".howdo"
_CONTEXT_BASENAME = "CONTEXT.md"
# A skill payload directory is identified by the skill file it ships. Anything
# under it is replaced wholesale on reinstall or update.
_PAYLOAD_MARKER = "SKILL.md"
_PAYLOAD_SEARCH_DEPTH = 6


class PayloadContextError(ValueError):
    """A settlement was attempted on a context living inside a skill payload.

    The payload is replaceable: install, update, and reinstall overwrite it. A
    settled context written there is discarded without any error being raised,
    so the write would produce a receipt the installation cannot keep.
    """


@dataclass(frozen=True)
class ContextStatus:
    path: Path
    state: ContextState
    reason: str
    metadata: Mapping[str, str]


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the deliberately flat YAML frontmatter used by CONTEXT.md.

    This is not a general YAML parser; keeping the metadata flat preserves the
    zero-dependency runtime.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        data[key.strip()] = value
    return data


def _set_frontmatter(text: str, updates: Mapping[str, str]) -> str:
    """Replace or insert flat frontmatter keys without requiring PyYAML."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("context requires flat YAML frontmatter")

    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("context frontmatter is not closed") from exc

    front = lines[1:end]
    body = lines[end:]
    remaining = dict(updates)
    rewritten: list[str] = []

    for line in front:
        if ":" not in line or line.lstrip().startswith("#"):
            rewritten.append(line)
            continue
        key = line.split(":", 1)[0].strip()
        if key in remaining:
            rewritten.append(f"{key}: {remaining.pop(key)}")
        else:
            rewritten.append(line)

    for key, value in remaining.items():
        rewritten.append(f"{key}: {value}")

    return "\n".join(["---", *rewritten, *body]) + ("\n" if text.endswith("\n") else "")


def _section_body(text: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _section_has_evidence(text: str, heading: str) -> bool:
    body = _section_body(text, heading)
    if body is None:
        return False
    # Instructional prose in the template is not onboarding evidence. Require
    # at least one explicit evidence bullet whose value is not a placeholder.
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        value = stripped[1:].strip().lower()
        if value and value not in _PLACEHOLDERS and not value.startswith(_PLACEHOLDER_PREFIXES):
            return True
    return False


def _replace_section(text: str, heading: str, body: str) -> str:
    pattern = re.compile(
        rf"(?ms)(^##\s+{re.escape(heading)}\s*$\n)(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(text)
    if not match:
        suffix = "" if text.endswith("\n") else "\n"
        return f"{text}{suffix}\n## {heading}\n\n{body.strip()}\n"
    return text[: match.start(2)] + body.strip() + "\n\n" + text[match.end(2) :].lstrip("\n")


def payload_root(path: str | Path) -> Path | None:
    """Return the skill payload directory containing ``path``, or ``None``.

    A payload directory is one that ships ``SKILL.md``. The check walks upward
    from the file so that ``<payload>/CONTEXT.md`` and any nested variant are
    both detected. This is a location question, not a durability claim: whether
    a store survives a reboot is the host's business, but whether a file sits in
    the part of the install that gets replaced is decidable right here.
    """
    p = Path(path)
    start = p if p.is_dir() else p.parent
    for candidate in [start, *start.parents][:_PAYLOAD_SEARCH_DEPTH]:
        if (candidate / _PAYLOAD_MARKER).is_file():
            return candidate
    return None


def resolve_context_path(
    explicit: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
) -> Path:
    """Resolve where this installation's durable context lives.

    Precedence, highest first:

    1. an explicitly selected file (never auto-merge several contexts);
    2. ``HOWDO_CONTEXT``, so a host can place the store wherever it keeps
       per-person state;
    3. ``~/.howdo/CONTEXT.md``.

    The basename stays ``CONTEXT.md`` for the canonical lineage because
    :func:`inspect_context` treats a different basename as a fork. Separation
    from the shipped template is by *path*, never by name.
    """
    if explicit is not None:
        return Path(explicit).expanduser()

    environ = os.environ if env is None else env
    configured = environ.get(_STORE_ENV)
    if configured:
        return Path(configured).expanduser()

    base = Path(home).expanduser() if home is not None else Path.home()
    return base / _STORE_DIRNAME / _CONTEXT_BASENAME


def ensure_context(
    path: str | Path | None = None,
    *,
    template: str | Path,
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
) -> ContextStatus:
    """Instantiate the store from the shipped template if it does not exist.

    An existing store is never overwritten, so reinstalling or updating the
    payload cannot clobber settled context. Returns the resulting status so a
    host can route straight into onboarding, decline, or ordinary work.
    """
    destination = resolve_context_path(path, env=env, home=home)
    if destination.exists():
        return inspect_context(destination)

    source = Path(template).expanduser()
    if not source.exists():
        raise FileNotFoundError(source)

    text = source.read_text(encoding="utf-8")
    if not _frontmatter(text):
        raise ValueError("template requires flat YAML frontmatter")

    text = _set_frontmatter(text, {"context_file": destination.name})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return inspect_context(destination)


def _refuse_payload_settlement(path: Path, *, allow_payload: bool) -> None:
    if allow_payload:
        return
    root = payload_root(path)
    if root is None:
        return
    raise PayloadContextError(
        f"{path} is inside the skill payload at {root}; settle the store "
        f"returned by resolve_context_path() instead, or pass allow_payload=True"
    )


def inspect_context(path: str | Path) -> ContextStatus:
    """Return whether a durable context is absent, new, ready, declined, forked, or invalid.

    A copied/renamed context is detected because its embedded ``context_file``
    no longer matches its actual basename. ``onboarding: complete`` is not
    sufficient by itself: the minimum comparative evidence sections must also
    contain non-placeholder material.
    """
    p = Path(path)
    if not p.exists():
        return ContextStatus(p, "missing", "context file does not exist", {})

    text = p.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    missing = sorted(_REQUIRED_META - set(metadata))
    if missing:
        return ContextStatus(
            p,
            "invalid",
            f"context frontmatter missing required keys: {', '.join(missing)}",
            metadata,
        )

    if metadata.get("skill") != "how-do":
        return ContextStatus(p, "invalid", "context skill marker is not how-do", metadata)

    declared = metadata.get("context_file")
    if declared != p.name:
        return ContextStatus(
            p,
            "fork_required",
            f"embedded context_file={declared!r} does not match basename={p.name!r}",
            metadata,
        )

    if metadata.get("onboarding") == "declined":
        if metadata.get("context_id") in {None, "", "pending"}:
            return ContextStatus(p, "invalid", "declined context requires a stable context_id", metadata)
        return ContextStatus(p, "declined", "durable calibration was declined; do not ask or use learned context", metadata)

    incomplete_meta = (
        metadata.get("onboarding") != "complete"
        or metadata.get("context_id") in {None, "", "pending"}
    )
    missing_evidence = [
        heading for heading in _REQUIRED_SECTIONS if not _section_has_evidence(text, heading)
    ]
    if incomplete_meta or missing_evidence:
        reason = "context has not completed comparative onboarding"
        if metadata.get("onboarding") == "complete" and missing_evidence:
            reason += f"; missing evidence in: {', '.join(missing_evidence)}"
        return ContextStatus(p, "onboarding_required", reason, metadata)

    return ContextStatus(p, "ready", "context is ready", metadata)


def complete_onboarding(
    path: str | Path,
    *,
    calibration_domain: str,
    representation_observation: str,
    landed_example: str,
    rejected_example: str,
    interaction_observation: str | None = None,
    allow_payload: bool = False,
) -> Path:
    """Settle the minimum structural receipt for comparative onboarding.

    This does not judge whether the user's feedback is *true*. It prevents a
    caller from making an untouched template ready by flipping two metadata
    fields while leaving the comparative evidence blank, and it refuses to
    settle a context that lives inside the replaceable skill payload.
    """
    def clean(value: str) -> str:
        return re.sub(r"[\r\n]+", " ", value).strip()

    values = {
        "calibration_domain": clean(calibration_domain),
        "representation_observation": clean(representation_observation),
        "landed_example": clean(landed_example),
        "rejected_example": clean(rejected_example),
    }
    for name, value in values.items():
        lowered = value.lower()
        if not value or lowered in _PLACEHOLDERS or lowered.startswith(_PLACEHOLDER_PREFIXES):
            raise ValueError(f"{name} must contain observed onboarding evidence")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    _refuse_payload_settlement(p, allow_payload=allow_payload)

    status = inspect_context(p)
    if status.state == "fork_required":
        raise ValueError("fork must be normalized before onboarding can settle")
    if status.state == "invalid":
        raise ValueError(status.reason)
    if status.state == "ready":
        raise ValueError("context onboarding is already complete")

    text = p.read_text(encoding="utf-8")
    text = _replace_section(text, "Calibration domains", f"- {values['calibration_domain']}")
    text = _replace_section(
        text, "Representation observations", f"- {values['representation_observation']}"
    )
    text = _replace_section(text, "Structures that landed", f"- {values['landed_example']}")
    text = _replace_section(
        text, "Structures that did not land", f"- {values['rejected_example']}"
    )
    if interaction_observation:
        text = _replace_section(
            text, "Interaction observations", f"- {clean(interaction_observation)}"
        )

    text = _set_frontmatter(
        text,
        {
            "context_id": (
                status.metadata.get("context_id")
                if status.state == "declined" and status.metadata.get("context_id") not in {None, "", "pending"}
                else new_context_id()
            ),
            "context_file": p.name,
            "onboarding": "complete",
        },
    )
    p.write_text(text, encoding="utf-8")
    return p


def decline_onboarding(path: str | Path, *, allow_payload: bool = False) -> Path:
    """Persist an explicit calibration decline without creating learned context.

    A decline is only worth persisting if it can be read back on the next
    session, so it is refused inside the payload for the same reason completion
    is: the write would succeed and then be discarded by the next update.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    _refuse_payload_settlement(p, allow_payload=allow_payload)

    status = inspect_context(p)
    if status.state == "fork_required":
        raise ValueError("fork must be normalized before onboarding can be declined")
    if status.state == "invalid":
        raise ValueError(status.reason)
    if status.state == "ready":
        raise ValueError("ready context cannot be converted to declined")
    if status.state == "declined":
        return p

    text = p.read_text(encoding="utf-8")
    text = _set_frontmatter(
        text,
        {
            "context_id": new_context_id(),
            "context_file": p.name,
            "onboarding": "declined",
        },
    )
    p.write_text(text, encoding="utf-8")
    return p


def fork_context(source: str | Path, destination: str | Path) -> Path:
    """Copy a context non-destructively and normalize it as a new lineage.

    Required lineage keys are inserted if an older/malformed source omitted
    them. The source is never removed or modified.
    """
    src = Path(source)
    dst = Path(destination)
    if not src.exists():
        raise FileNotFoundError(src)
    if dst.exists():
        raise FileExistsError(dst)

    text = src.read_text(encoding="utf-8")
    meta = _frontmatter(text)
    if not meta:
        raise ValueError("source context requires flat YAML frontmatter")
    parent = meta.get("context_id", "unknown")

    text = _set_frontmatter(
        text,
        {
            "howdo_context": meta.get("howdo_context", '"2"'),
            "context_id": "pending",
            "context_file": dst.name,
            "skill": "how-do",
            "skill_version": "\"0.7.0\"",
            "onboarding": "required",
            "parent_context_id": parent,
        },
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return dst


def new_context_id() -> str:
    """Generate an opaque id to write when onboarding is settled."""
    return f"context_{uuid.uuid4().hex[:12]}"
