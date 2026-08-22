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
import sys
import uuid


ContextState = Literal[
    "missing",
    "template",
    "onboarding_required",
    "reconnaissance_required",
    "ready",
    "deferred",
    "declined",
    "fork_required",
    "expired",
    "invalid",
]

# A context declares what kind of thing it records. The kinds are disjoint:
# a person context is elicited because a pedagogy is not observable, and an
# environment context is inspected because an environment's affordances are.
# Neither validator can be satisfied by the other's file — the metadata keys
# and the evidence sections both differ.
KIND_PERSON = "person"
KIND_ENVIRONMENT = "environment"
_KIND_KEY = "context_kind"
_KINDS = (KIND_PERSON, KIND_ENVIRONMENT)

# Lifetime and write authority are independent of kind, so that "environment"
# never silently implies "ephemeral".
LIFETIME_EPHEMERAL = "ephemeral"
LIFETIME_FROZEN = "frozen"
LIFETIME_PERSISTENT = "persistent"
_LIFETIMES = (LIFETIME_EPHEMERAL, LIFETIME_FROZEN, LIFETIME_PERSISTENT)
_LIFETIME_KEY = "lifetime"

AUTHORITY_WRITABLE = "writable"
AUTHORITY_READONLY = "readonly"
_AUTHORITIES = (AUTHORITY_WRITABLE, AUTHORITY_READONLY)
_AUTHORITY_KEY = "write_authority"

# Whether this install records signals. Off unless a person says otherwise, so
# the absence of the key is the default rather than an omission to repair. It
# is named for what it switches -- signal recording -- rather than for
# onboarding, which is settled by a different key and a different machine.
SIGNALS_ON = "on"
SIGNALS_OFF = "off"
_SIGNALS_KEY = "signals"
_SIGNALS_TRUE = {"on", "true", "yes", "1", "enabled"}

_TRIAL_KEY = "trial_id"
_UNSET = {None, "", "pending", "none"}

_BASE_META = {
    "howdo_context",
    "context_id",
    "context_file",
    "skill",
    "skill_version",
    "parent_context_id",
}
# The settlement key differs by kind and is not shared. "onboarding" is person
# language; an environment context is never deferred or declined, because there
# is nobody to ask.
_REQUIRED_META_BY_KIND = {
    KIND_PERSON: _BASE_META | {"onboarding"},
    KIND_ENVIRONMENT: _BASE_META | {_KIND_KEY, "reconnaissance", _LIFETIME_KEY, _AUTHORITY_KEY},
}
_REQUIRED_META = _REQUIRED_META_BY_KIND[KIND_PERSON]

_REQUIRED_SECTIONS_BY_KIND = {
    KIND_PERSON: (
        "Calibration domains",
        "Representation observations",
        "Structures that landed",
        "Structures that did not land",
    ),
    KIND_ENVIRONMENT: (
        "Available ground",
        "Imposed ordering",
        "Verification mechanisms",
        "Mutation and authority boundaries",
    ),
}
_REQUIRED_SECTIONS = _REQUIRED_SECTIONS_BY_KIND[KIND_PERSON]
_PLACEHOLDERS = {"", "pending", "none", "none yet", "- pending", "- none yet"}
_PLACEHOLDER_PREFIXES = ("pending", "none yet")

SKILL_VERSION = "0.10.0"

_TEMPLATE_KEY = "template"
_TEMPLATE_TRUE = {"true", "yes", "1"}
# Prose that documents the template *as a template*. It is meaningless — and
# actively misleading — once the file has become a lineage, so instantiation
# removes it rather than copying it into the store.
_TEMPLATE_BLOCK = re.compile(
    r"(?ms)^[ \t]*<!--[ \t]*template-only:start[ \t]*-->.*?"
    r"^[ \t]*<!--[ \t]*template-only:end[ \t]*-->[ \t]*\n?"
)
# A store is per-user by default. "shared" marks a deliberately generic store
# that every user of one install reads, which is the only reason a context is
# allowed to live inside the replaceable payload.
_SCOPE_KEY = "scope"
_SCOPE_USER = "user"
_SCOPE_SHARED = "shared"
_STORE_ENV = "HOWDO_CONTEXT"
# A plugin host tells the plugin where per-install persistent state belongs.
# That directory survives updates by contract, which is the same guarantee the
# payload/store split exists to provide -- so when a host offers it, it is a
# better default than a path this module invents. It stays *below* HOWDO_CONTEXT
# so that a person who has already moved a settled store keeps it.
_STORE_PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA"
_STORE_DIRNAME = ".howdo"
# Windows keeps per-user application state under %APPDATA%; a dotdir in the
# profile root works but is not where a Windows user looks for it.
_STORE_APPDATA_ENV = "APPDATA"
_STORE_APPDATA_DIRNAME = "howdo"
_CONTEXT_BASENAME = "CONTEXT.md"
# A skill payload directory is identified by the skill file it ships. Anything
# under it is replaced wholesale on reinstall or update.
_PAYLOAD_MARKER = "SKILL.md"
_PAYLOAD_SEARCH_DEPTH = 6
# A plugin root ships its manifest; an ordinary skill directory never does,
# because the installer's PAYLOAD deliberately excludes it. That makes the
# manifest the one reliable way to tell the two payload kinds apart from a path
# alone -- no host directory layout is assumed, and nothing is parsed.
_PLUGIN_MANIFEST = (".claude-plugin", "plugin.json")


class TemplateContextError(ValueError):
    """A settlement was attempted on the shipped template.

    A template is an artifact of the payload, not a lineage. It has no
    ``context_id`` to settle into and is replaced by the next update. Instantiate
    a store with :func:`ensure_context` and settle that instead.
    """


class PayloadContextError(ValueError):
    """A settlement was attempted on a context living inside a skill payload.

    The payload is replaceable: install, update, and reinstall overwrite it. A
    settled context written there is discarded without any error being raised,
    so the write would produce a receipt the installation cannot keep.
    """


class ContextKindError(ValueError):
    """A settlement was attempted across context kinds.

    ``person`` and ``environment`` are different kinds, not two modes of one
    onboarding. Their evidence sections are disjoint, so settling one through
    the other's helper would write text into headings that do not exist and
    stamp a marker the validator does not read.
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


def _drop_frontmatter_keys(text: str, keys: set[str]) -> str:
    """Remove flat frontmatter keys; used to strip the template marker."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("context requires flat YAML frontmatter")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("context frontmatter is not closed") from exc
    front = [
        line for line in lines[1:end]
        if ":" not in line or line.split(":", 1)[0].strip() not in keys
    ]
    return "\n".join(["---", *front, *lines[end:]]) + ("\n" if text.endswith("\n") else "")


def _strip_template_block(text: str) -> str:
    """Remove the template-only preamble when instantiating a store.

    The shipped template has to explain that it is a template. The instance it
    produces must not repeat that claim: a settled store whose body still says
    "do not settle this file" contradicts its own frontmatter and tells the next
    reader to ignore the lineage it just opened.
    """
    stripped = _TEMPLATE_BLOCK.sub("", text, count=1)
    # Removing a delimited block leaves the blank lines that surrounded it.
    return re.sub(r"\n{3,}", "\n\n", stripped)


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


def _is_template(metadata: Mapping[str, str]) -> bool:
    return str(metadata.get(_TEMPLATE_KEY, "")).strip().lower() in _TEMPLATE_TRUE


def is_shared(metadata: Mapping[str, str]) -> bool:
    """True when a context declares itself the generic store for an install.

    Absence means ``user``: a context that predates the key, or was written
    without one, is per-person. Genericness is only ever opted into.
    """
    return str(metadata.get(_SCOPE_KEY, _SCOPE_USER)).strip().lower() == _SCOPE_SHARED


def context_kind(metadata: Mapping[str, str]) -> str:
    """Return the declared kind of a context.

    Absence means ``person``: every context written before the kind existed
    records a pedagogy, so the default preserves them exactly. An unrecognised
    value is returned as-is so :func:`inspect_context` can report it rather
    than quietly treating an unknown kind as a person.
    """
    return str(metadata.get(_KIND_KEY, KIND_PERSON)).strip().lower() or KIND_PERSON


def context_lifetime(metadata: Mapping[str, str]) -> str:
    """Return the declared lifetime. Absent means ``persistent``.

    A person context has always outlived the session that settled it, so the
    default has to keep meaning that. Environment contexts must declare one.
    """
    return str(metadata.get(_LIFETIME_KEY, LIFETIME_PERSISTENT)).strip().lower()


def write_authority(metadata: Mapping[str, str]) -> str:
    """Return the declared write authority. Absent means ``writable``."""
    return str(metadata.get(_AUTHORITY_KEY, AUTHORITY_WRITABLE)).strip().lower()


def read_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat frontmatter this project uses, for callers outside it.

    The parser is private because its internals may change; the *format* is
    not, and more than one module needs to read it. Exposing this is what
    keeps a second dialect from growing elsewhere in the payload -- two
    parsers for one format diverge on exactly the malformed files nobody
    tests with.
    """
    return _frontmatter(text)


def signals_enabled(metadata: Mapping[str, str]) -> bool:
    """Whether this install records signals. Absent means no.

    Off by default is the whole basis on which an observation surface is
    admissible at all: one a person switched on is not the ambience
    ``SKILL.md`` refuses, and one that arrived by default would be.
    """
    return str(metadata.get(_SIGNALS_KEY, "")).strip().lower() in _SIGNALS_TRUE


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


def is_plugin_payload(root: str | Path) -> bool:
    """True when a payload directory is a *plugin* root rather than a skill directory.

    The distinction is not cosmetic, and it is the reason this exists: the two
    kinds fail differently on update. A skill directory is replaced in place, so
    a file inside it is overwritten and gone. A plugin payload is version-scoped
    -- hosts install it under a directory named for the release -- so an update
    does not touch the old directory at all. It creates a new one beside it and
    reads from there.

    A file left in the old directory is therefore not discarded. It is
    *orphaned*: still on disk, still readable, and no longer the file anything
    loads. That is strictly worse than deletion for a durable context, because
    nothing raises and nothing is missing from the filesystem's point of view.
    """
    return (Path(root).joinpath(*_PLUGIN_MANIFEST)).is_file()


def default_store_path(
    *,
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
    platform: str | None = None,
) -> Path:
    """Return the per-user store location this platform expects.

    The store is per-person state, so it belongs where the platform already
    keeps per-person state: ``%APPDATA%\\howdo\\CONTEXT.md`` on Windows,
    ``~/.howdo/CONTEXT.md`` elsewhere. ``HOWDO_CONTEXT`` overrides both.

    This depends only on configuration, never on what is already on disk, so
    one environment always resolves to one path. Anyone moving a settled store
    points ``HOWDO_CONTEXT`` at it.
    """
    environ = os.environ if env is None else env
    base = Path(home).expanduser() if home is not None else Path.home()

    system = sys.platform if platform is None else platform
    if system.startswith("win"):
        appdata = environ.get(_STORE_APPDATA_ENV)
        roaming = (
            Path(appdata).expanduser() if appdata else base / "AppData" / "Roaming"
        )
        return roaming / _STORE_APPDATA_DIRNAME / _CONTEXT_BASENAME

    return base / _STORE_DIRNAME / _CONTEXT_BASENAME


def resolve_context_path(
    explicit: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
    platform: str | None = None,
) -> Path:
    """Resolve where this installation's durable context lives.

    Precedence, highest first:

    1. an explicitly selected file (never auto-merge several contexts);
    2. ``HOWDO_CONTEXT``, so a host can place the store wherever it keeps
       per-person state;
    3. ``CLAUDE_PLUGIN_DATA``, the directory a plugin host guarantees will
       survive updates -- present only when running as an installed plugin;
    4. the platform default from :func:`default_store_path`.

    Three and four are both "the host's per-install state directory"; the
    difference is that a plugin host states its own, so we do not have to
    guess one from the platform. Ordering it under ``HOWDO_CONTEXT`` means
    installing the plugin never moves a store somebody already relocated.

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

    plugin_data = environ.get(_STORE_PLUGIN_DATA_ENV)
    if plugin_data:
        return Path(plugin_data).expanduser() / _CONTEXT_BASENAME

    return default_store_path(env=environ, home=home, platform=platform)


def ensure_context(
    path: str | Path | None = None,
    *,
    template: str | Path,
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
    platform: str | None = None,
    scope: str = _SCOPE_USER,
) -> ContextStatus:
    """Instantiate the store from the shipped template if it does not exist.

    An existing store is never overwritten, so reinstalling or updating the
    payload cannot clobber settled context. Returns the resulting status so a
    host can route straight into onboarding, decline, or ordinary work.
    """
    destination = resolve_context_path(path, env=env, home=home, platform=platform)
    if destination.exists():
        return inspect_context(destination)

    source = Path(template).expanduser()
    if not source.exists():
        raise FileNotFoundError(source)

    text = source.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    if not metadata:
        raise ValueError("template requires flat YAML frontmatter")

    # The instance is a different type from the template it came from: the
    # marker and the template-only prose are stripped, and a fresh, unsettled
    # lineage is opened. Carrying the prose over would leave every store — even
    # a settled one — telling its reader that it cannot be settled.
    text = _drop_frontmatter_keys(text, {_TEMPLATE_KEY})
    text = _strip_template_block(text)
    text = _set_frontmatter(
        text,
        {
            "context_id": "pending",
            "context_file": destination.name,
            "scope": scope,
            "onboarding": "required",
            "parent_context_id": "none",
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return inspect_context(destination)


def _refuse_template_settlement(path: Path) -> None:
    status = inspect_context(path)
    if status.state == "template":
        raise TemplateContextError(
            f"{path} is the shipped template; instantiate a store with "
            f"ensure_context() and settle that instead"
        )


def _refuse_payload_settlement(path: Path, *, allow_payload: bool) -> None:
    if allow_payload:
        return
    root = payload_root(path)
    if root is None:
        return
    shared = is_shared(_frontmatter(path.read_text(encoding="utf-8")))
    if shared and not is_plugin_payload(root):
        # A store that declares scope: shared was placed here deliberately, by
        # someone who accepted that a wholesale reinstall discards it. That is
        # an opted-into trade, not the accident this refusal exists to catch.
        return
    if shared:
        # The same declaration under a plugin buys a different trade than the
        # one it describes. A version-scoped payload is not replaced on update,
        # so the store is not discarded -- it is left in the previous version's
        # directory while the skill reads from the new one. Nobody opts into
        # that, because nothing announces it: no error, no missing file, just a
        # context that silently stops being the one in use.
        raise PayloadContextError(
            f"{path} declares scope: shared inside a *plugin* payload at {root}. "
            f"A plugin payload is version-scoped, so the next release reads from "
            f"a new directory and this file is orphaned rather than replaced. "
            f"Put the shared store where the host does not version it -- the "
            f"directory named by ${_STORE_PLUGIN_DATA_ENV}, or a path in "
            f"${_STORE_ENV} -- and mark it scope: shared there. "
            f"resolve_context_path() already returns such a path"
        )
    raise PayloadContextError(
        f"{path} is inside the skill payload at {root}; settle the store "
        f"returned by resolve_context_path() instead, mark it scope: shared to "
        f"opt into a generic install-wide context, or pass allow_payload=True"
    )


def inspect_context(path: str | Path, *, trial_id: str | None = None) -> ContextStatus:
    """Return whether a durable context is absent, new, ready, declined, forked, or invalid.

    A copied/renamed context is detected because its embedded ``context_file``
    no longer matches its actual basename. A settled marker is not sufficient by
    itself: the evidence sections required for that context's *kind* must also
    contain non-placeholder material.

    ``trial_id`` asserts which trial is reading. It is required to read an
    ephemeral context and ignored otherwise: an ephemeral context that outlives
    its trial reports ``expired`` instead of handing back content, so a reused
    volume surfaces as a state rather than as silent contamination.
    """
    p = Path(path)
    if not p.exists():
        return ContextStatus(p, "missing", "context file does not exist", {})

    text = p.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    kind = context_kind(metadata)
    if kind not in _KINDS:
        return ContextStatus(
            p, "invalid", f"unrecognised context_kind: {kind!r}", metadata
        )
    missing = sorted(_REQUIRED_META_BY_KIND[kind] - set(metadata))
    if missing:
        return ContextStatus(
            p,
            "invalid",
            f"context frontmatter missing required keys: {', '.join(missing)}",
            metadata,
        )

    if metadata.get("skill") != "how-do":
        return ContextStatus(p, "invalid", "context skill marker is not how-do", metadata)

    if _is_template(metadata):
        # A template is a different type from a context: no lineage, no fork
        # check, never ready, never settled.
        return ContextStatus(p, "template", "shipped template; instantiate a store from it", metadata)

    declared = metadata.get("context_file")
    if declared != p.name:
        return ContextStatus(
            p,
            "fork_required",
            f"embedded context_file={declared!r} does not match basename={p.name!r}",
            metadata,
        )

    if kind == KIND_ENVIRONMENT:
        return _inspect_environment(p, text, metadata, trial_id)

    if metadata.get("onboarding") == "deferred":
        # Deferred is not declined. The person chose to work first, so the
        # offer stays open; nothing here is learned context yet.
        if metadata.get("context_id") in {None, "", "pending"}:
            return ContextStatus(p, "invalid", "deferred context requires a stable context_id", metadata)
        return ContextStatus(
            p,
            "deferred",
            "calibration deferred; work without learned context and may re-offer later",
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
        heading
        for heading in _REQUIRED_SECTIONS_BY_KIND[KIND_PERSON]
        if not _section_has_evidence(text, heading)
    ]
    if incomplete_meta or missing_evidence:
        reason = "context has not established a pedagogy"
        if metadata.get("onboarding") == "complete" and missing_evidence:
            reason += f"; missing evidence in: {', '.join(missing_evidence)}"
        return ContextStatus(p, "onboarding_required", reason, metadata)

    return ContextStatus(p, "ready", "context is ready", metadata)


def _inspect_environment(
    p: Path,
    text: str,
    metadata: Mapping[str, str],
    trial_id: str | None,
) -> ContextStatus:
    """Validate an environment context.

    Ordering is deliberate. Lifetime and authority are checked first because a
    context that cannot say how long it lives cannot be trusted at all; the
    trial binding is checked next because it decides whether this reader may
    look at the content; evidence is checked last.
    """
    lifetime = context_lifetime(metadata)
    if lifetime not in _LIFETIMES:
        return ContextStatus(p, "invalid", f"unrecognised lifetime: {lifetime!r}", metadata)

    authority = write_authority(metadata)
    if authority not in _AUTHORITIES:
        return ContextStatus(
            p, "invalid", f"unrecognised write_authority: {authority!r}", metadata
        )

    if lifetime == LIFETIME_EPHEMERAL:
        bound = metadata.get(_TRIAL_KEY)
        if bound in _UNSET:
            return ContextStatus(
                p, "invalid", "ephemeral context is not bound to a trial_id", metadata
            )
        if trial_id is None:
            return ContextStatus(
                p,
                "invalid",
                f"ephemeral context is bound to trial {bound!r} and must be read "
                f"with the reading trial's id",
                metadata,
            )
        if trial_id != bound:
            return ContextStatus(
                p,
                "expired",
                f"ephemeral context belongs to trial {bound!r}, not {trial_id!r}; "
                f"it did not survive the trial boundary",
                metadata,
            )

    incomplete_meta = (
        metadata.get("reconnaissance") != "complete"
        or metadata.get("context_id") in _UNSET
    )
    missing_evidence = [
        heading
        for heading in _REQUIRED_SECTIONS_BY_KIND[KIND_ENVIRONMENT]
        if not _section_has_evidence(text, heading)
    ]
    if incomplete_meta or missing_evidence:
        reason = "environment context has not established ground"
        if metadata.get("reconnaissance") == "complete" and missing_evidence:
            reason += f"; missing evidence in: {', '.join(missing_evidence)}"
        return ContextStatus(p, "reconnaissance_required", reason, metadata)

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
    """Settle the minimum structural receipt for an established pedagogy.

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
    _refuse_template_settlement(p)
    _refuse_payload_settlement(p, allow_payload=allow_payload)

    if context_kind(_frontmatter(p.read_text(encoding="utf-8"))) != KIND_PERSON:
        raise ContextKindError(
            f"{p} is not a person context; onboarding settles a pedagogy, which "
            f"an environment context does not record"
        )

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
                if status.state in {"declined", "deferred"}
                and status.metadata.get("context_id") not in {None, "", "pending"}
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
    _refuse_template_settlement(p)
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


def defer_onboarding(path: str | Path, *, allow_payload: bool = False) -> Path:
    """Persist "not now" without spending the offer.

    Distinct from :func:`decline_onboarding`. A decline is an answer and is
    final: never ask again, never treat the file as learned context. A deferral
    is only a postponement — the person chose to work first, so the offer stays
    open for a later session. Neither state is learned context, and a deferral
    that is never taken up simply stays deferred.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    _refuse_template_settlement(p)
    _refuse_payload_settlement(p, allow_payload=allow_payload)

    status = inspect_context(p)
    if status.state == "fork_required":
        raise ValueError("fork must be normalized before onboarding can be deferred")
    if status.state == "invalid":
        raise ValueError(status.reason)
    if status.state == "ready":
        raise ValueError("ready context has nothing left to defer")
    if status.state == "declined":
        raise ValueError("declined context cannot be reopened by deferring; onboard it instead")
    if status.state == "deferred":
        return p

    existing = status.metadata.get("context_id")
    text = _set_frontmatter(
        p.read_text(encoding="utf-8"),
        {
            "context_id": existing if existing not in {None, "", "pending"} else new_context_id(),
            "context_file": p.name,
            "onboarding": "deferred",
        },
    )
    p.write_text(text, encoding="utf-8")
    return p


def set_signals(path: str | Path, *, on: bool, allow_payload: bool = False) -> Path:
    """Turn signal recording on or off, with the guards every setting gets.

    A setting with a reader and no writer is one only a person willing to hand
    edit YAML can use, and the sibling transitions -- completing, declining,
    deferring -- all refuse the template and refuse a payload-resident store.
    This is the same refusal for the same reason: the write would succeed and
    the next update would discard it, silently.

    Unlike those, this is reversible and carries no evidence, so it does not
    touch the lineage or the onboarding state. It flips one key.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    _refuse_template_settlement(p)
    _refuse_payload_settlement(p, allow_payload=allow_payload)

    text = _set_frontmatter(
        p.read_text(encoding="utf-8"),
        {_SIGNALS_KEY: SIGNALS_ON if on else SIGNALS_OFF},
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
    if _is_template(meta):
        raise TemplateContextError(
            f"{src} is a template, not a lineage; use ensure_context() to instantiate it"
        )
    parent = meta.get("context_id", "unknown")

    text = _set_frontmatter(
        text,
        {
            "howdo_context": meta.get("howdo_context", '"2"'),
            "context_id": "pending",
            "context_file": dst.name,
            "skill": "how-do",
            "skill_version": f'"{SKILL_VERSION}"',
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
