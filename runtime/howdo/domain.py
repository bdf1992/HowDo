"""Domain-how: the artifact a recurring concern leaves behind, and its index.

`SKILL.md` has always promised this file -- "one file per recurring concern:
map, path, consequential contracts, invariants, one worked example, and
revision" -- and nothing ever wrote one. The discipline described its artifacts
and minted only `CONTEXT.md`, which is a pedagogy and is barred from carrying
domain facts. So a person's domain work left no durable trace at all.

This module issues that file and indexes it. Three rules shape it:

* **Issued from a run, not from a plan.** A domain-how is built out of what a
  HowDo actually resolved and observed. There is no constructor that takes a
  description of work someone intends to do.
* **Untested until grounded.** Issuing marks `untested`. Only a residual that
  matched promotes it, and any content change drops it back -- so a map that was
  rewritten cannot inherit the grounding its predecessor earned.
* **The index is a view, not the authority.** It is rebuilt from the files it
  describes, in the same spirit as `experiment/CROSSINGS.md`: relations are
  projections over evidence, so a lost or stale index is a rebuild rather than
  a loss.

The store is the one outside the payload. A domain-how settled inside the skill
would be discarded by the next update with no error raised -- the failure
`CONTEXT.md` already had, one level down.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence
import copy
import hashlib
import json
import os
import re

from .context import payload_root, resolve_context_path
from .contract import ContractError, RequestContract
from .core import Paradigm, Residual, Resolution

__all__ = [
    "DOMAIN_VERSION",
    "STATUS_GROUNDED",
    "STATUS_UNTESTED",
    "DomainError",
    "DomainHow",
    "IndexEntry",
    "Staleness",
    "WorkedExample",
    "domain_path",
    "ground",
    "issue",
    "issue_from_run",
    "load",
    "read_index",
    "reindex",
    "resolve_domain_root",
    "revise",
    "staleness",
]


DOMAIN_VERSION = 1

#: Issued, but no observed run has confirmed it yet.
STATUS_UNTESTED = "untested"
#: A residual that matched promoted it. See :func:`ground`.
STATUS_GROUNDED = "grounded"

_STATUSES = (STATUS_UNTESTED, STATUS_GROUNDED)

_ROOT_ENV = "HOWDO_DOMAINS"
_ROOT_DIRNAME = "domains"
_INDEX_BASENAME = "index.json"
_SUFFIX = ".json"

# A concern names a file and an index key, so it is constrained the way
# resolution operands are: an uppercase and a lowercase spelling of the same
# concern must not be able to fork into two artifacts.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class DomainError(ValueError):
    """A domain-how that cannot be issued, loaded, or promoted honestly."""


def _slug(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise DomainError(f"{name} must be a string, got {type(value).__name__}")
    cleaned = value.strip()
    if not _SLUG.match(cleaned):
        raise DomainError(
            f"{name} must match {_SLUG.pattern} so casing cannot fork one concern "
            f"into two; got {value!r}"
        )
    return cleaned


def _plain(name: str, value: Any) -> Any:
    """Reject anything a stored artifact could not be read back from."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(f"{name}[{i}]", item) for i, item in enumerate(value)]
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise DomainError(f"{name} keys must be strings, got {type(key).__name__}")
            out[key] = _plain(f"{name}.{key}", item)
        return out
    raise DomainError(
        f"{name} must be JSON-representable to survive being written down; "
        f"got {type(value).__name__}"
    )


@dataclass(frozen=True)
class WorkedExample:
    """One run that actually happened, kept as the artifact's evidence.

    Not an illustration written afterwards. These are the inputs that were
    resolved, the result that was predicted, and the state that was observed --
    which is why :func:`issue_from_run` is the only ordinary way to get one.
    """

    inputs: Mapping[str, Any] = field(default_factory=dict)
    expected: Mapping[str, Any] = field(default_factory=dict)
    observed: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("inputs", "expected", "observed"):
            object.__setattr__(self, name, _plain(name, dict(getattr(self, name))))

    def as_dict(self) -> dict[str, Any]:
        return {
            "inputs": dict(self.inputs),
            "expected": dict(self.expected),
            "observed": dict(self.observed),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WorkedExample":
        _reject_unknown("example", data, {"inputs", "expected", "observed"})
        return cls(
            inputs=data.get("inputs", {}),
            expected=data.get("expected", {}),
            observed=data.get("observed", {}),
        )


@dataclass(frozen=True)
class DomainHow:
    """What one recurring concern leaves behind.

    The six parts `SKILL.md` named: ``map``, the ``contract``'s path, its
    consequential contracts and invariants, one worked ``example``, and a
    ``revision``. Plus the two the prose left implicit and unenforceable -- the
    ``status`` that separates issued from grounded, and the paradigm revision
    the grounding was observed against.
    """

    concern: str
    map: Mapping[str, Any]
    contract: RequestContract
    example: WorkedExample
    revision: int = 1
    status: str = STATUS_UNTESTED
    # The paradigm revision the grounding run observed. None until grounded:
    # an artifact that has never been tested has nothing to be stale against.
    observed_against: int | None = None
    grounded_by: str | None = None
    version: int = DOMAIN_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "concern", _slug("concern", self.concern))
        object.__setattr__(self, "map", _plain("map", dict(self.map)))
        if not self.map:
            raise DomainError(
                "a domain-how carries the map its path is navigable in; an empty map "
                "makes the path untestable"
            )
        if not isinstance(self.contract, RequestContract):
            raise DomainError(
                f"contract must be a RequestContract, got {type(self.contract).__name__}"
            )
        if not isinstance(self.example, WorkedExample):
            raise DomainError(
                f"example must be a WorkedExample, got {type(self.example).__name__}"
            )
        if not isinstance(self.revision, int) or self.revision < 1:
            raise DomainError(f"revision must be a positive int, got {self.revision!r}")
        if self.status not in _STATUSES:
            raise DomainError(f"unknown status {self.status!r}; expected one of {_STATUSES}")
        if self.status == STATUS_UNTESTED and self.observed_against is not None:
            raise DomainError("an untested domain-how has no observation to be measured against")
        if self.status == STATUS_GROUNDED and self.observed_against is None:
            raise DomainError("a grounded domain-how records the revision it was observed against")
        if self.observed_against is not None and (
            not isinstance(self.observed_against, int) or self.observed_against < 0
        ):
            raise DomainError(f"observed_against must be a revision, got {self.observed_against!r}")
        if self.version != DOMAIN_VERSION:
            raise DomainError(
                f"domain-how version {self.version!r} is not {DOMAIN_VERSION}; "
                "this host does not know how to read it"
            )

    @property
    def grounded(self) -> bool:
        return self.status == STATUS_GROUNDED

    @property
    def path(self) -> tuple[str, ...]:
        """The workflow this concern runs. `references/vocabulary.md`: path is the workflow."""
        return self.contract.path

    @property
    def requires(self) -> tuple[str, ...]:
        """The capabilities a host must offer to run this concern at all."""
        return self.contract.requires

    def content_bytes(self) -> bytes:
        """The bytes the content digest commits to.

        Lineage is deliberately excluded: grounding an artifact must not look
        like editing it, or every promotion would read as a new artifact.
        """

        payload = {
            "version": self.version,
            "concern": self.concern,
            "map": dict(self.map),
            "contract": self.contract.as_dict(),
            "example": self.example.as_dict(),
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.content_bytes()).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "concern": self.concern,
            "revision": self.revision,
            "status": self.status,
            "observed_against": self.observed_against,
            "grounded_by": self.grounded_by,
            "digest": self.digest(),
            "map": dict(self.map),
            "contract": self.contract.as_dict(),
            "example": self.example.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DomainHow":
        _reject_unknown(
            "domain-how",
            data,
            {
                "version",
                "concern",
                "revision",
                "status",
                "observed_against",
                "grounded_by",
                "digest",
                "map",
                "contract",
                "example",
            },
        )
        for name in ("map", "contract", "example"):
            if not isinstance(data.get(name), Mapping):
                raise DomainError(f"`{name}` must be an object")
        how = cls(
            concern=data.get("concern", ""),
            map=data["map"],
            contract=RequestContract.from_dict(data["contract"]),
            example=WorkedExample.from_dict(data["example"]),
            revision=data.get("revision", 1),
            status=data.get("status", STATUS_UNTESTED),
            observed_against=data.get("observed_against"),
            grounded_by=data.get("grounded_by"),
            version=data.get("version", DOMAIN_VERSION),
        )
        stored = data.get("digest")
        if stored is not None and stored != how.digest():
            raise DomainError(
                f"domain-how {how.concern!r} does not match its recorded digest; "
                "the file was edited outside the issuer"
            )
        return how


@dataclass(frozen=True)
class IndexEntry:
    """One row of the index: enough to choose an artifact without opening it."""

    concern: str
    revision: int
    status: str
    digest: str
    intent: str
    path: tuple[str, ...]
    requires: tuple[str, ...]
    observed_against: int | None

    @classmethod
    def of(cls, how: DomainHow) -> "IndexEntry":
        return cls(
            concern=how.concern,
            revision=how.revision,
            status=how.status,
            digest=how.digest(),
            intent=how.contract.intent,
            path=how.path,
            requires=how.requires,
            observed_against=how.observed_against,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "concern": self.concern,
            "revision": self.revision,
            "status": self.status,
            "digest": self.digest,
            "intent": self.intent,
            "path": list(self.path),
            "requires": list(self.requires),
            "observed_against": self.observed_against,
        }


@dataclass(frozen=True)
class Staleness:
    """Whether a grounded artifact still speaks about the paradigm in front of you."""

    concern: str
    stale: bool
    observed_against: int | None
    current_revision: int
    reason: str


# -- store resolution -------------------------------------------------------


def resolve_domain_root(
    explicit: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    context_path: str | Path | None = None,
) -> Path:
    """Where issued domain-hows live.

    Beside the durable context, for the same reason it is there: outside the
    payload, so an update replaces the skill without discarding what the work
    produced. ``HOWDO_DOMAINS`` overrides, the way ``HOWDO_CONTEXT`` does.
    """

    if explicit is not None:
        return Path(explicit).expanduser()
    environ = os.environ if env is None else env
    configured = environ.get(_ROOT_ENV)
    if configured:
        return Path(configured).expanduser()
    return resolve_context_path(context_path, env=environ).parent / _ROOT_DIRNAME


def domain_path(concern: str, *, root: str | Path | None = None) -> Path:
    return Path(resolve_domain_root(root)) / f"{_slug('concern', concern)}{_SUFFIX}"


def _guard_payload(root: Path) -> None:
    payload = payload_root(root)
    if payload is not None:
        raise DomainError(
            f"{root} is inside the skill payload at {payload}; a domain-how settled "
            "there is discarded by the next install with no error raised"
        )


# -- issuing ----------------------------------------------------------------


def issue_from_run(
    resolution: Resolution,
    residual: Residual,
    *,
    concern: str,
    contract: RequestContract,
    map: Mapping[str, Any],
) -> DomainHow:
    """Mint a domain-how out of a HowDo that actually ran.

    The press, and the only ordinary way to get an artifact. A run supplies the
    example; the contract supplies the path, the shapes, and the rules. Nothing
    here accepts a description of work someone intends to do, because an
    artifact issued from an intention has no evidence in it.
    """

    if not isinstance(resolution, Resolution):
        raise DomainError(f"expected a Resolution, got {type(resolution).__name__}")
    if not isinstance(residual, Residual):
        raise DomainError(f"expected a Residual, got {type(residual).__name__}")
    if residual.resolution.resolution_id != resolution.resolution_id:
        raise DomainError("residual belongs to a different resolution")
    if tuple(contract.path) != tuple(resolution.path):
        raise DomainError(
            "contract path does not match the path the run resolved; the artifact "
            "would describe a route nothing took"
        )

    return DomainHow(
        concern=concern,
        map=map,
        contract=contract,
        example=WorkedExample(
            inputs=dict(resolution.request.inputs),
            expected=dict(residual.expected),
            observed=dict(residual.observed),
        ),
    )


def issue(how: DomainHow, *, root: str | Path | None = None) -> Path:
    """Write an artifact into the store and refresh the index.

    A revision is required to replace what is already there: an issuer that
    silently overwrites is how a grounded artifact quietly becomes an untested
    one under the same name.
    """

    if not isinstance(how, DomainHow):
        raise DomainError(f"expected a DomainHow, got {type(how).__name__}")
    directory = Path(resolve_domain_root(root))
    _guard_payload(directory)

    target = directory / f"{how.concern}{_SUFFIX}"
    if target.is_file():
        existing = load(how.concern, root=directory)
        if existing.digest() == how.digest():
            return target
        if how.revision <= existing.revision:
            raise DomainError(
                f"{how.concern!r} is already at revision {existing.revision}; issuing "
                f"different content at revision {how.revision} would overwrite it. "
                "Use revise() to supersede it."
            )

    directory.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(how.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    reindex(root=directory)
    return target


def revise(how: DomainHow, previous: DomainHow) -> DomainHow:
    """Supersede an artifact, dropping the grounding its predecessor earned.

    Content changed, so the observation that grounded the old content no longer
    says anything about the new content. `SKILL.md` refuses to "promote an
    untested exemplar simply because it sounded plausible"; inheriting grounding
    across an edit is exactly that promotion, done silently.
    """

    if how.concern != previous.concern:
        raise DomainError("a revision stays within one concern")
    if how.digest() == previous.digest():
        return previous
    return replace(
        how,
        revision=previous.revision + 1,
        status=STATUS_UNTESTED,
        observed_against=None,
        grounded_by=None,
    )


def ground(
    concern: str,
    residual: Residual,
    *,
    root: str | Path | None = None,
    observer: str | None = None,
) -> DomainHow:
    """Promote an issued artifact on the strength of a run that matched.

    Refuses a residual that did not match. This is the one place where the
    prose rule -- "after a how survives at least one do/look cycle" -- becomes
    a condition something actually evaluates.
    """

    if not isinstance(residual, Residual):
        raise DomainError(f"expected a Residual, got {type(residual).__name__}")
    if not residual.matched:
        raise DomainError(
            f"residual routed to {residual.route!r}: a run that did not match cannot "
            "ground an artifact"
        )

    how = load(concern, root=root)
    promoted = replace(
        how,
        status=STATUS_GROUNDED,
        observed_against=residual.resolution.paradigm_revision,
        grounded_by=observer or residual.observation.observer_name,
    )
    directory = Path(resolve_domain_root(root))
    _guard_payload(directory)
    (directory / f"{promoted.concern}{_SUFFIX}").write_text(
        json.dumps(promoted.as_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    reindex(root=directory)
    return promoted


# -- loading and indexing ---------------------------------------------------


def load(concern: str, *, root: str | Path | None = None) -> DomainHow:
    target = Path(resolve_domain_root(root)) / f"{_slug('concern', concern)}{_SUFFIX}"
    if not target.is_file():
        raise DomainError(f"no domain-how issued for {concern!r} at {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DomainError(f"{target} is not valid JSON: {exc}") from exc
    try:
        return DomainHow.from_dict(data)
    except ContractError as exc:
        raise DomainError(f"{target} carries an unreadable contract: {exc}") from exc


def reindex(*, root: str | Path | None = None) -> tuple[IndexEntry, ...]:
    """Rebuild the index from the artifacts it describes.

    The index is a materialized view, never the authority -- the same rule
    `experiment/CROSSINGS.md` sets for the skill graph. A missing, stale, or
    corrupt index is therefore a rebuild, not a loss, and an artifact dropped
    into the directory by hand appears without anyone registering it.
    """

    directory = Path(resolve_domain_root(root))
    if not directory.is_dir():
        return ()
    _guard_payload(directory)

    entries: list[IndexEntry] = []
    unreadable: list[str] = []
    for candidate in sorted(directory.glob(f"*{_SUFFIX}")):
        if candidate.name == _INDEX_BASENAME:
            continue
        try:
            entries.append(IndexEntry.of(load(candidate.stem, root=directory)))
        except DomainError:
            # One bad file must not cost the whole index. It is reported in the
            # view rather than raised, so a rebuild always terminates.
            unreadable.append(candidate.name)

    (directory / _INDEX_BASENAME).write_text(
        json.dumps(
            {
                "version": DOMAIN_VERSION,
                "entries": [entry.as_dict() for entry in entries],
                "unreadable": unreadable,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return tuple(entries)


def read_index(
    *,
    root: str | Path | None = None,
    status: str | None = None,
    requires: Sequence[str] | None = None,
) -> tuple[IndexEntry, ...]:
    """The catalogue: what has been issued, which workflow each runs, what it needs.

    Read from the files rather than the cached view, so the answer cannot be
    stale. Filter by ``status`` to keep untested artifacts out of a decision, or
    by ``requires`` to see only what this host could run.
    """

    entries = reindex(root=root)
    if status is not None:
        if status not in _STATUSES:
            raise DomainError(f"unknown status {status!r}; expected one of {_STATUSES}")
        entries = tuple(entry for entry in entries if entry.status == status)
    if requires is not None:
        offered = set(requires)
        entries = tuple(entry for entry in entries if set(entry.requires) <= offered)
    return entries


def staleness(how: DomainHow, paradigm: Paradigm) -> Staleness:
    """Has the paradigm moved since this artifact was last observed to hold?

    `core.admit` fizzles a stale resolution, but that protection ends at the
    process boundary -- which is where a persisted artifact begins. An artifact
    issued against revision 3 will bind cleanly into revision 40 and say nothing
    about the difference unless something asks.
    """

    current = paradigm.revision
    if not how.grounded:
        return Staleness(
            concern=how.concern,
            stale=False,
            observed_against=None,
            current_revision=current,
            reason="untested: never observed to hold, so nothing to be stale against",
        )
    observed = how.observed_against or 0
    if observed == current:
        return Staleness(
            concern=how.concern,
            stale=False,
            observed_against=observed,
            current_revision=current,
            reason=f"observed against the current revision {current}",
        )
    return Staleness(
        concern=how.concern,
        stale=True,
        observed_against=observed,
        current_revision=current,
        reason=(
            f"grounded against revision {observed}; the paradigm is now at {current}. "
            "The artifact may still hold, but nothing has observed it since."
        ),
    )


def _reject_unknown(what: str, data: Mapping[str, Any], allowed: set[str]) -> None:
    if not isinstance(data, Mapping):
        raise DomainError(f"{what} must be an object, got {type(data).__name__}")
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise DomainError(f"unknown {what} keys: {unknown}")

