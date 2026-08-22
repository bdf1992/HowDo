"""A deliberately small reference runtime for the How Do discipline.

The protocol is:
    resolve -> admit -> operate -> observe -> settle

No model SDK, tool framework, or persistence backend is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Literal, Mapping, Sequence
import copy
import time
import uuid


Agency = Literal["user", "assistant", "joint", "external", "unspecified"]


Route = Literal[
    "none",
    "precondition",
    "postcondition",
    "rendering",
    "hidden_postcondition",
    "invariant",
    # The observation cannot be compared to the prediction at all: the shapes
    # disagree. That indicts the declared interface, not the operation's
    # effect, so it must not be reported as a postcondition residual.
    "contract",
]
Predicate = Callable[[Mapping[str, Any]], bool]
Executor = Callable[["Resolution"], Mapping[str, Any]]
Observer = Callable[["ObservationContext"], Mapping[str, Any]]
Comparator = Callable[[Mapping[str, Any], Mapping[str, Any]], bool]
Patch = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _changed_top_level_keys(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> tuple[str, ...]:
    keys = set(before) | set(after)
    return tuple(sorted(key for key in keys if before.get(key) != after.get(key)))


@dataclass(frozen=True)
class Paradigm:
    """Revisioned, inspectable working state.

    `state` is intentionally untyped. The domain owns its map representation.
    """

    state: Mapping[str, Any]
    revision: int = 0
    paradigm_id: str = field(default_factory=lambda: _id("paradigm"))


@dataclass(frozen=True)
class Request:
    handle: str
    intent: str
    target: str | None = None
    # Semantic attribution only: the skill binds this from I/you/we/they.
    # The kernel records it but does not attempt natural-language inference.
    actor: Agency = "unspecified"
    # Consequential by default: a caller must opt OUT of contracts, not in.
    mutates: bool = True
    crosses_boundary: bool = False
    # What the operation reads. Without a declared channel, arguments travel
    # in `intent` as prose or inside an executor closure, and the operation's
    # input is describable but not inspectable.
    inputs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Snapshot for the same reason GateEvidence does: a caller that keeps
        # mutating the mapping must not be able to change, after the fact,
        # what the operation was asked to read.
        object.__setattr__(self, "inputs", copy.deepcopy(dict(self.inputs)))


@dataclass(frozen=True)
class Check:
    name: str
    description: str
    predicate: Predicate
    kind: Literal["precondition", "invariant"] = "precondition"

    def evaluate(self, state: Mapping[str, Any]) -> bool:
        """Fail closed: a predicate that raises counts as false."""
        try:
            return bool(self.predicate(state))
        except Exception:
            return False


@dataclass(frozen=True)
class GateEvidence:
    """Attributed evidence used to open the admission gate.

    This records provenance; it does not prove the external source is truthful.
    """

    state: Mapping[str, Any]
    source: str
    observed_at: float = field(default_factory=time.time)
    evidence_id: str = field(default_factory=lambda: _id("evidence"))

    def __post_init__(self) -> None:
        # Snapshot caller input so later mutation of the source mapping cannot
        # retroactively change what evidence opened the gate.
        object.__setattr__(self, "state", copy.deepcopy(dict(self.state)))


@dataclass(frozen=True)
class Resolution:
    request: Request
    paradigm_id: str
    paradigm_revision: int
    resolved_state: Mapping[str, Any]
    path: Sequence[str]
    expected: Mapping[str, Any]
    checks: Sequence[Check] = ()
    resolution_id: str = field(default_factory=lambda: _id("resolution"))


@dataclass(frozen=True)
class Fizzle:
    resolution: Resolution
    failed_checks: Sequence[str]
    reason: str
    route: Route
    evidence_source: str | None = None


@dataclass(frozen=True)
class Admission:
    resolution: Resolution
    passed_checks: Sequence[str]
    evidence_id: str
    evidence_source: str
    evidence_observed_at: float
    admitted_at: float = field(default_factory=time.time)
    admission_id: str = field(default_factory=lambda: _id("admission"))
    consumed: bool = False

    def _consume(self) -> None:
        if self.consumed:
            raise ValueError("admission already consumed: one gate opens one operation")
        object.__setattr__(self, "consumed", True)


@dataclass(frozen=True)
class Outcome:
    admission: Admission
    reported: Mapping[str, Any]
    started_at: float
    finished_at: float
    outcome_id: str = field(default_factory=lambda: _id("outcome"))


@dataclass(frozen=True)
class ObservationContext:
    """The observer's deliberately narrow view.

    It receives the expected keys and a caller-supplied handle to the world.
    It does not receive the executor report or Outcome.
    """

    expected_keys: tuple[str, ...]
    world: Any


@dataclass(frozen=True)
class Observation:
    outcome_id: str
    observed: Mapping[str, Any]
    observer_name: str
    observed_at: float = field(default_factory=time.time)
    observation_id: str = field(default_factory=lambda: _id("observation"))


@dataclass(frozen=True)
class Residual:
    resolution: Resolution
    observation: Observation
    matched: bool
    route: Route
    expected: Mapping[str, Any]
    observed: Mapping[str, Any]
    failed_invariants: Sequence[str] = ()
    note: str = ""
    residual_id: str = field(default_factory=lambda: _id("residual"))


@dataclass(frozen=True)
class Settlement:
    residual: Residual
    accepted: bool
    paradigm: Paradigm
    changed: bool
    changed_layers: Sequence[str]
    reason: str
    settlement_id: str = field(default_factory=lambda: _id("settlement"))


def resolve(
    request: Request,
    paradigm: Paradigm,
    *,
    path: Sequence[str],
    expected: Mapping[str, Any],
    checks: Sequence[Check] = (),
) -> Resolution:
    """Locate a request against one immutable paradigm revision."""

    if not path:
        raise ValueError("path must contain at least one step")

    consequential = request.mutates or request.crosses_boundary
    if consequential and not expected:
        raise ValueError("consequential operations require observable expected state")

    checks = tuple(checks)
    if consequential and not any(check.kind == "precondition" for check in checks):
        raise ValueError("consequential operations require at least one precondition")

    return Resolution(
        request=request,
        paradigm_id=paradigm.paradigm_id,
        paradigm_revision=paradigm.revision,
        resolved_state=copy.deepcopy(dict(paradigm.state)),
        path=tuple(path),
        expected=copy.deepcopy(dict(expected)),
        checks=checks,
    )


def admit(
    resolution: Resolution,
    paradigm: Paradigm,
    evidence: GateEvidence,
) -> Admission | Fizzle:
    """Evaluate admission against the current paradigm and attributed evidence.

    Staleness is rejected here, before any executor can run.
    """

    if paradigm.paradigm_id != resolution.paradigm_id:
        raise ValueError("resolution belongs to a different paradigm")

    if paradigm.revision != resolution.paradigm_revision:
        return Fizzle(
            resolution=resolution,
            failed_checks=("paradigm_revision",),
            reason="gate closed: resolution is stale",
            route="precondition",
            evidence_source=evidence.source,
        )

    passed: list[str] = []
    failed_preconditions: list[str] = []
    failed_invariants: list[str] = []

    for check in resolution.checks:
        if check.evaluate(evidence.state):
            passed.append(check.name)
        elif check.kind == "invariant":
            failed_invariants.append(check.name)
        else:
            failed_preconditions.append(check.name)

    if failed_invariants or failed_preconditions:
        failed = tuple(failed_invariants + failed_preconditions)
        route: Route = "invariant" if failed_invariants else "precondition"
        return Fizzle(
            resolution=resolution,
            failed_checks=failed,
            reason="gate closed: one or more checks were false",
            route=route,
            evidence_source=evidence.source,
        )

    return Admission(
        resolution=resolution,
        passed_checks=tuple(passed),
        evidence_id=evidence.evidence_id,
        evidence_source=evidence.source,
        evidence_observed_at=evidence.observed_at,
    )


def operate(admission: Admission, executor: Executor) -> Outcome:
    """Execute an admitted operation.

    The returned mapping is a report, not proof that the world changed.
    An admission is single-use: a second operate() on the same admission raises.
    """

    admission._consume()
    started = time.time()
    reported = executor(admission.resolution)
    finished = time.time()
    return Outcome(
        admission=admission,
        reported=copy.deepcopy(dict(reported)),
        started_at=started,
        finished_at=finished,
    )


def observe(
    outcome: Outcome,
    observer: Observer,
    *,
    world: Any,
    comparator: Comparator | None = None,
    observer_name: str = "observer",
) -> tuple[Observation, Residual]:
    """Observe world state without handing the observer the executor report.

    The observer should return enough state to compare all expected keys and to
    evaluate declared invariants. Extra observed keys are allowed.
    """

    resolution = outcome.admission.resolution
    context = ObservationContext(
        expected_keys=tuple(resolution.expected.keys()),
        world=world,
    )
    observed_map = copy.deepcopy(dict(observer(context)))
    observation = Observation(
        outcome_id=outcome.outcome_id,
        observed=observed_map,
        observer_name=observer_name,
    )

    expected = resolution.expected

    def default_compare(exp: Mapping[str, Any], obs: Mapping[str, Any]) -> bool:
        return all(key in obs and obs[key] == value for key, value in exp.items())

    cmp = comparator or default_compare
    postcondition_matched = bool(cmp(expected, observed_map))

    failed_invariants = tuple(
        check.name
        for check in resolution.checks
        if check.kind == "invariant" and not check.evaluate(observed_map)
    )

    if failed_invariants:
        matched = False
        route: Route = "invariant"
        note = "invariant residual"
    elif not postcondition_matched:
        matched = False
        route = "postcondition"
        note = "postcondition residual"
    else:
        matched = True
        route = "none"
        note = "postcondition and invariants matched"

    residual = Residual(
        resolution=resolution,
        observation=observation,
        matched=matched,
        route=route,
        expected=copy.deepcopy(dict(expected)),
        observed=observed_map,
        failed_invariants=failed_invariants,
        note=note,
    )
    return observation, residual


def settle(
    paradigm: Paradigm,
    residual: Residual,
    *,
    accept: bool,
    patch: Patch | None = None,
    reason: str = "",
    allow_multi_layer: bool = False,
    allow_after_invariant: bool = False,
) -> Settlement:
    """Apply an explicit evidence-backed write-back.

    By default a settlement may change at most one top-level paradigm layer.
    A caller must explicitly override that guard for a multi-layer rewrite.

    A residual routed to "invariant" means the paradigm was not safe to continue
    under; settling a patch on top of it is refused unless explicitly overridden.
    """

    if paradigm.paradigm_id != residual.resolution.paradigm_id:
        raise ValueError("residual belongs to a different paradigm")
    if paradigm.revision != residual.resolution.paradigm_revision:
        raise ValueError("stale residual: paradigm revision has changed")

    if residual.route == "invariant" and accept and patch is not None and not allow_after_invariant:
        raise ValueError(
            "residual is routed to invariant: paradigm is not safe to patch; "
            "pass allow_after_invariant=True to override"
        )

    if not accept or patch is None:
        return Settlement(
            residual=residual,
            accepted=accept,
            paradigm=paradigm,
            changed=False,
            changed_layers=(),
            reason=reason
            or (
                "accepted observation; no paradigm patch"
                if accept
                else "settlement rejected or deferred"
            ),
        )

    before = copy.deepcopy(dict(paradigm.state))
    new_state = copy.deepcopy(dict(patch(copy.deepcopy(before))))
    changed_layers = _changed_top_level_keys(before, new_state)

    if len(changed_layers) > 1 and not allow_multi_layer:
        raise ValueError(
            "settlement changes more than one top-level paradigm layer; "
            "pass allow_multi_layer=True to override"
        )

    changed = bool(changed_layers)
    next_paradigm = replace(
        paradigm,
        state=new_state,
        revision=paradigm.revision + (1 if changed else 0),
    )
    return Settlement(
        residual=residual,
        accepted=True,
        paradigm=next_paradigm,
        changed=changed,
        changed_layers=changed_layers,
        reason=reason or "evidence-backed paradigm update",
    )
