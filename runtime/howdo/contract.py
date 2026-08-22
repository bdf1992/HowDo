"""Request contracts: the declared shape a request and its result must match.

The kernel already refuses a consequential operation with no expected state and
no precondition. It does not know what that expected state is *shaped* like, and
it cannot say what a host must be able to do before the operation is admissible.
Both live in the caller's head, which means they travel in prose or not at all.

A ``RequestContract`` writes them down:

* ``accepts`` -- the shape of what the operation reads (``Request.inputs``)
* ``expects`` -- the shape of the observable result the operation commits to
* ``rules``   -- named checks as declarative clauses rather than Python closures
* ``requires``-- the capabilities a host must offer for this to be runnable here

Everything above is data. A contract round-trips through plain JSON-able dicts
and digests to a stable identity, so the same contract loads into a Python host,
a shell host, or a model-only host and states the same obligations in each. That
is the whole point: a check that exists only as a closure is not portable, and a
predicted shape that exists only in prose is not checkable.

Nothing here relaxes a kernel invariant. Rules compile into ordinary
:class:`~howdo.core.Check` objects, so ``admit`` enforces them unchanged, and a
shape residual is routed to ``contract`` rather than laundered into a
postcondition residual it is not.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Literal, Mapping, Sequence
import hashlib
import json

from .context import AUTHORITY_READONLY, AUTHORITY_WRITABLE
from .core import (
    Agency,
    Check,
    Comparator,
    Observation,
    Observer,
    Outcome,
    Paradigm,
    Request,
    Residual,
    Resolution,
    observe as _observe,
    resolve as _resolve,
)

__all__ = [
    "CONTRACT_VERSION",
    "ELEMENT_TYPES",
    "OPS",
    "TYPES",
    "BoundContract",
    "Clause",
    "ContractError",
    "Field",
    "Host",
    "RequestContract",
    "Rule",
    "Shape",
    "Unsupported",
    "bind",
]


# Canonicalization changes. Without a version inside the hashed payload an old
# digest becomes uninterpretable: a different contract and the same contract
# serialized under different rules are indistinguishable.
CONTRACT_VERSION = 1

#: The closed type set. Deliberately small: enough to catch a host and a
#: contract disagreeing about shape, not a type system.
TYPES = ("any", "string", "integer", "number", "boolean", "list", "mapping")

#: Element types admissible under ``list``. Nesting is not offered; a shape that
#: needs it wants a schema language, and that is a different tool.
ELEMENT_TYPES = ("any", "string", "integer", "number", "boolean")

#: The closed operator set. Every one of these is evaluable by a host that has
#: only a mapping and a string, which is what makes a rule portable.
OPS = (
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "contains",
    "present",
    "absent",
    "truthy",
    "falsy",
)

#: Operators that read no operand. Supplying one is a contract error rather than
#: a silently ignored field, because the ignored field would look load-bearing.
_NULLARY = ("present", "absent", "truthy", "falsy")

_MISSING = object()


class ContractError(ValueError):
    """A contract that cannot be stated, loaded, or honoured as written."""


def _text(name: str, value: Any, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a string, got {type(value).__name__}")
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise ContractError(f"{name} must not be empty")
    return cleaned


def _json_value(name: str, value: Any) -> Any:
    """Reject anything that would not survive the trip to another host.

    A clause operand that only exists as a Python object makes the contract
    unloadable elsewhere while still passing every local test.
    """

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(f"{name}[{index}]", item) for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError(f"{name} keys must be strings, got {type(key).__name__}")
            out[key] = _json_value(f"{name}.{key}", item)
        return out
    raise ContractError(
        f"{name} must be JSON-representable so the contract loads on another host; "
        f"got {type(value).__name__}"
    )


def _type_ok(value: Any, type_name: str) -> bool:
    if type_name == "any":
        return True
    if type_name == "boolean":
        return isinstance(value, bool)
    # bool is a subclass of int; a flag is not a count and must not pass as one.
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "list":
        return isinstance(value, (list, tuple))
    if type_name == "mapping":
        return isinstance(value, Mapping)
    return False


def _lookup(state: Mapping[str, Any], key: str) -> Any:
    """Resolve a dotted key. Anything unresolvable is missing, never an error."""

    current: Any = state
    for part in key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


@dataclass(frozen=True)
class Field:
    """One declared key in a shape."""

    name: str
    type: str = "any"
    of: str | None = None
    required: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text("field name", self.name))
        object.__setattr__(self, "type", _text("field type", self.type))
        object.__setattr__(
            self, "description", _text("field description", self.description, allow_empty=True)
        )
        if self.type not in TYPES:
            raise ContractError(f"unknown type {self.type!r}; expected one of {TYPES}")
        if self.of is not None:
            if self.type != "list":
                raise ContractError("`of` describes list elements and is only valid on a list")
            element = _text("field element type", self.of)
            if element not in ELEMENT_TYPES:
                raise ContractError(
                    f"unknown element type {element!r}; expected one of {ELEMENT_TYPES}"
                )
            object.__setattr__(self, "of", element)
        if not isinstance(self.required, bool):
            raise ContractError("`required` must be a boolean")

    def violations(self, state: Mapping[str, Any]) -> tuple[str, ...]:
        value = _lookup(state, self.name)
        if value is _MISSING:
            return () if not self.required else (f"missing key {self.name!r}",)
        if not _type_ok(value, self.type):
            return (f"key {self.name!r}: expected {self.type}, got {type(value).__name__}",)
        if self.of is None:
            return ()
        return tuple(
            f"key {self.name!r}[{index}]: expected {self.of}, got {type(item).__name__}"
            for index, item in enumerate(value)
            if not _type_ok(item, self.of)
        )

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "type": self.type, "required": self.required}
        if self.of is not None:
            out["of"] = self.of
        if self.description:
            out["description"] = self.description
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Field":
        _reject_unknown("field", data, {"name", "type", "of", "required", "description"})
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "any"),
            of=data.get("of"),
            required=bool(data.get("required", True)),
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class Shape:
    """A declared mapping shape: which keys, of which types, and whether more are allowed."""

    fields: tuple[Field, ...] = ()
    closed: bool = False

    def __post_init__(self) -> None:
        fields = tuple(self.fields)
        for item in fields:
            if not isinstance(item, Field):
                raise ContractError(f"shape fields must be Field, got {type(item).__name__}")
        names = [item.name for item in fields]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ContractError(f"shape declares duplicate keys: {duplicates}")
        object.__setattr__(self, "fields", fields)
        if not isinstance(self.closed, bool):
            raise ContractError("`closed` must be a boolean")

    def __bool__(self) -> bool:
        return bool(self.fields)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields)

    def violations(self, state: Mapping[str, Any]) -> tuple[str, ...]:
        """Every way ``state`` fails this shape. Empty means it conforms."""

        if not isinstance(state, Mapping):
            return (f"expected a mapping, got {type(state).__name__}",)
        found: list[str] = []
        for item in self.fields:
            found.extend(item.violations(state))
        if self.closed:
            # Only top-level names participate: a dotted field addresses a key
            # inside a value the shape has already admitted.
            declared = {item.name.split(".", 1)[0] for item in self.fields}
            found.extend(f"unexpected key {key!r}" for key in sorted(set(state) - declared))
        return tuple(found)

    def as_dict(self) -> dict[str, Any]:
        return {"fields": [item.as_dict() for item in self.fields], "closed": self.closed}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Shape":
        _reject_unknown("shape", data, {"fields", "closed"})
        raw = data.get("fields", ())
        if isinstance(raw, Mapping) or not isinstance(raw, Iterable):
            raise ContractError("shape `fields` must be a list")
        return cls(
            fields=tuple(Field.from_dict(item) for item in raw),
            closed=bool(data.get("closed", False)),
        )


@dataclass(frozen=True)
class Clause:
    """One serializable predicate over a state mapping."""

    key: str
    op: str
    value: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _text("clause key", self.key))
        object.__setattr__(self, "op", _text("clause op", self.op))
        if self.op not in OPS:
            raise ContractError(f"unknown operator {self.op!r}; expected one of {OPS}")
        if self.op in _NULLARY:
            if self.value is not None:
                raise ContractError(f"operator {self.op!r} takes no value")
        object.__setattr__(self, "value", _json_value("clause value", self.value))

    def evaluate(self, state: Mapping[str, Any]) -> bool:
        """Fail closed, exactly as ``Check.evaluate`` does."""

        try:
            found = _lookup(state, self.key)
            if self.op == "present":
                return found is not _MISSING
            if self.op == "absent":
                return found is _MISSING
            if found is _MISSING:
                # Every remaining operator reads the value. A key that is not
                # there cannot satisfy one.
                return False
            if self.op == "truthy":
                return bool(found)
            if self.op == "falsy":
                return not bool(found)
            if self.op == "eq":
                return found == self.value
            if self.op == "ne":
                return found != self.value
            if self.op == "gt":
                return found > self.value
            if self.op == "gte":
                return found >= self.value
            if self.op == "lt":
                return found < self.value
            if self.op == "lte":
                return found <= self.value
            if self.op == "in":
                return found in self.value
            if self.op == "contains":
                return self.value in found
        except Exception:
            return False
        return False

    def describe(self) -> str:
        """Render in the portable form, not the Python one.

        A clause read back by a human or another host should look like what is
        in the file: `approved eq true`, never `approved eq True`.
        """

        if self.op in _NULLARY:
            return f"{self.key} {self.op}"
        return f"{self.key} {self.op} {json.dumps(self.value)}"

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"key": self.key, "op": self.op}
        if self.op not in _NULLARY:
            out["value"] = self.value
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Clause":
        _reject_unknown("clause", data, {"key", "op", "value"})
        return cls(key=data.get("key", ""), op=data.get("op", ""), value=data.get("value"))


@dataclass(frozen=True)
class Rule:
    """A named check stated as data, so it survives leaving this process."""

    name: str
    description: str
    clause: Clause
    kind: Literal["precondition", "invariant"] = "precondition"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text("rule name", self.name))
        object.__setattr__(self, "description", _text("rule description", self.description))
        if not isinstance(self.clause, Clause):
            raise ContractError(f"rule clause must be a Clause, got {type(self.clause).__name__}")
        if self.kind not in ("precondition", "invariant"):
            raise ContractError(f"unknown rule kind {self.kind!r}")

    def compile(self) -> Check:
        """Become an ordinary kernel check.

        The gate is not widened for contracts: ``admit`` evaluates a compiled
        rule with the code path it already had.
        """

        return Check(
            name=self.name,
            description=self.description,
            predicate=self.clause.evaluate,
            kind=self.kind,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "clause": self.clause.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Rule":
        _reject_unknown("rule", data, {"name", "description", "kind", "clause"})
        clause = data.get("clause")
        if not isinstance(clause, Mapping):
            raise ContractError("rule `clause` must be an object")
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            clause=Clause.from_dict(clause),
            kind=data.get("kind", "precondition"),
        )


@dataclass(frozen=True)
class Host:
    """What one environment declares it can do.

    A declaration, not an authentication. It closes the case where a contract is
    loaded somewhere it cannot run; it does not prove the host told the truth.
    """

    name: str
    capabilities: frozenset[str] = frozenset()
    authority: str = AUTHORITY_WRITABLE

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text("host name", self.name))
        object.__setattr__(
            self,
            "capabilities",
            frozenset(_text("capability", item) for item in self.capabilities),
        )
        if self.authority not in (AUTHORITY_READONLY, AUTHORITY_WRITABLE):
            raise ContractError(
                f"authority must be {AUTHORITY_READONLY!r} or {AUTHORITY_WRITABLE!r}, "
                f"got {self.authority!r}"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capabilities": sorted(self.capabilities),
            "authority": self.authority,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Host":
        _reject_unknown("host", data, {"name", "capabilities", "authority"})
        return cls(
            name=data.get("name", ""),
            capabilities=frozenset(data.get("capabilities", ())),
            authority=data.get("authority", AUTHORITY_WRITABLE),
        )


@dataclass(frozen=True)
class RequestContract:
    """The declared interface of one operation, as data.

    It is the same object in every host: the path it follows, the shape it
    reads, the shape it promises to make observable, the checks that open its
    gate, and what the host must be able to do to run it at all.
    """

    name: str
    intent: str
    path: tuple[str, ...]
    handle: str = "how do"
    target: str | None = None
    actor: Agency = "unspecified"
    mutates: bool = True
    crosses_boundary: bool = False
    accepts: Shape = Shape()
    expects: Shape = Shape()
    rules: tuple[Rule, ...] = ()
    requires: tuple[str, ...] = ()
    version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text("contract name", self.name))
        object.__setattr__(self, "intent", _text("contract intent", self.intent))
        object.__setattr__(self, "handle", _text("contract handle", self.handle))
        if self.target is not None:
            object.__setattr__(self, "target", _text("contract target", self.target))

        path = tuple(_text("path step", step) for step in self.path)
        if not path:
            raise ContractError("a contract declares the path it follows; path must not be empty")
        object.__setattr__(self, "path", path)

        for name, shape in (("accepts", self.accepts), ("expects", self.expects)):
            if not isinstance(shape, Shape):
                raise ContractError(f"`{name}` must be a Shape, got {type(shape).__name__}")

        rules = tuple(self.rules)
        for rule in rules:
            if not isinstance(rule, Rule):
                raise ContractError(f"rules must be Rule, got {type(rule).__name__}")
        names = [rule.name for rule in rules]
        duplicates = sorted({item for item in names if names.count(item) > 1})
        if duplicates:
            raise ContractError(f"contract declares duplicate rule names: {duplicates}")
        object.__setattr__(self, "rules", rules)

        object.__setattr__(
            self, "requires", tuple(sorted({_text("capability", item) for item in self.requires}))
        )
        if not isinstance(self.version, int) or self.version < 1:
            raise ContractError(f"version must be a positive int, got {self.version!r}")

        # The kernel refuses a consequential operation with no expected state
        # and no precondition. A portable contract has to refuse it earlier and
        # for a stronger reason: a contract that leans on a check the host
        # happens to supply is not the same contract in the next host.
        if self.consequential:
            if not self.expects:
                raise ContractError(
                    "a consequential contract must declare the shape of its observable result"
                )
            if not any(rule.kind == "precondition" for rule in self.rules):
                raise ContractError(
                    "a consequential contract must carry at least one precondition rule; "
                    "a gate supplied by the host does not travel with the contract"
                )

    @property
    def consequential(self) -> bool:
        return bool(self.mutates or self.crosses_boundary)

    # -- portability ----------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "version": self.version,
            "name": self.name,
            "handle": self.handle,
            "intent": self.intent,
            "actor": self.actor,
            "mutates": self.mutates,
            "crosses_boundary": self.crosses_boundary,
            "path": list(self.path),
            "accepts": self.accepts.as_dict(),
            "expects": self.expects.as_dict(),
            "rules": [rule.as_dict() for rule in self.rules],
            "requires": list(self.requires),
        }
        if self.target is not None:
            out["target"] = self.target
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RequestContract":
        if not isinstance(data, Mapping):
            raise ContractError(f"a contract loads from an object, got {type(data).__name__}")
        _reject_unknown(
            "contract",
            data,
            {
                "version",
                "name",
                "handle",
                "intent",
                "target",
                "actor",
                "mutates",
                "crosses_boundary",
                "path",
                "accepts",
                "expects",
                "rules",
                "requires",
            },
        )
        version = data.get("version", CONTRACT_VERSION)
        if version != CONTRACT_VERSION:
            raise ContractError(
                f"contract version {version!r} is not {CONTRACT_VERSION}; "
                "the canonical form this host knows how to read has moved"
            )
        for name in ("accepts", "expects"):
            if name in data and not isinstance(data[name], Mapping):
                raise ContractError(f"`{name}` must be an object")
        path = data.get("path", ())
        if isinstance(path, str) or not isinstance(path, Iterable):
            raise ContractError("`path` must be a list of steps")
        return cls(
            name=data.get("name", ""),
            intent=data.get("intent", ""),
            path=tuple(path),
            handle=data.get("handle", "how do"),
            target=data.get("target"),
            actor=data.get("actor", "unspecified"),
            mutates=bool(data.get("mutates", True)),
            crosses_boundary=bool(data.get("crosses_boundary", False)),
            accepts=Shape.from_dict(data.get("accepts", {})),
            expects=Shape.from_dict(data.get("expects", {})),
            rules=tuple(Rule.from_dict(item) for item in data.get("rules", ())),
            requires=tuple(data.get("requires", ())),
            version=version,
        )

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.as_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "RequestContract":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ContractError(f"contract is not valid JSON: {exc}") from exc
        return cls.from_dict(data)

    def canonical_bytes(self) -> bytes:
        """The exact bytes the digest commits to."""

        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

    def digest(self) -> str:
        """A stable identity for this contract, comparable across hosts."""

        return hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True)
class Unsupported:
    """This contract cannot be run here, established before anything resolved.

    A sibling of :class:`~howdo.core.Fizzle` one step earlier in the loop: a
    fizzle names a gate that would not open, this names a host the operation was
    never loadable into.
    """

    contract_name: str
    host: str
    missing_capabilities: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class BoundContract:
    """A contract that this host has been shown able to run."""

    contract: RequestContract
    host: Host

    def resolve(
        self,
        paradigm: Paradigm,
        *,
        inputs: Mapping[str, Any] | None = None,
        expected: Mapping[str, Any],
        checks: Sequence[Check] = (),
    ) -> Resolution:
        """Resolve against the declared shapes, then hand the kernel its Resolution.

        ``checks`` is the escape hatch for a predicate the clause set genuinely
        cannot state. It is additive: the contract's own rules always apply, so
        the portable gate cannot be replaced by a local one.
        """

        contract = self.contract
        inputs = dict(inputs or {})

        violations = contract.accepts.violations(inputs)
        if violations:
            raise ContractError(
                f"inputs do not match the shape {contract.name!r} accepts: "
                + "; ".join(violations)
            )
        violations = contract.expects.violations(expected)
        if violations:
            raise ContractError(
                f"expected result does not match the shape {contract.name!r} promises: "
                + "; ".join(violations)
            )

        request = Request(
            handle=contract.handle,
            intent=contract.intent,
            target=contract.target,
            actor=contract.actor,
            mutates=contract.mutates,
            crosses_boundary=contract.crosses_boundary,
            inputs=inputs,
        )
        return _resolve(
            request,
            paradigm,
            path=contract.path,
            expected=expected,
            checks=tuple(rule.compile() for rule in contract.rules) + tuple(checks),
        )

    def observe(
        self,
        outcome: Outcome,
        observer: Observer,
        *,
        world: Any,
        comparator: Comparator | None = None,
        observer_name: str = "observer",
    ) -> tuple[Observation, Residual]:
        """Observe, then separate "wrong result" from "incomparable result".

        A postcondition residual says the operation did something other than
        what it promised. An observation that does not match the declared shape
        says something weaker and more urgent: the prediction and the evidence
        are not about the same thing, so nothing has actually been tested yet.
        """

        observation, residual = _observe(
            outcome,
            observer,
            world=world,
            comparator=comparator,
            observer_name=observer_name,
        )
        # An invariant residual outranks a shape complaint: the paradigm is
        # already unsafe to continue under, and settle() must keep refusing it.
        if residual.route in ("none", "postcondition"):
            violations = self.contract.expects.violations(observation.observed)
            if violations:
                return observation, replace(
                    residual,
                    matched=False,
                    route="contract",
                    note="shape residual: " + "; ".join(violations),
                )
        return observation, residual


def bind(contract: RequestContract, host: Host) -> BoundContract | Unsupported:
    """Check a portable contract against one host before anything is resolved.

    This is what "loadable in multiple environments" has to mean if it is a
    property rather than a hope: the contract states what it needs, the host
    states what it has, and a mismatch is a result you can read rather than a
    failure you discover mid-operation.
    """

    if not isinstance(contract, RequestContract):
        raise ContractError(f"expected a RequestContract, got {type(contract).__name__}")
    if not isinstance(host, Host):
        raise ContractError(f"expected a Host, got {type(host).__name__}")

    missing = tuple(sorted(set(contract.requires) - host.capabilities))
    if missing:
        return Unsupported(
            contract_name=contract.name,
            host=host.name,
            missing_capabilities=missing,
            reason=f"host {host.name!r} does not offer: {', '.join(missing)}",
        )
    if contract.consequential and host.authority == AUTHORITY_READONLY:
        return Unsupported(
            contract_name=contract.name,
            host=host.name,
            missing_capabilities=(),
            reason=(
                f"contract {contract.name!r} is consequential and host {host.name!r} "
                f"is {AUTHORITY_READONLY}"
            ),
        )
    return BoundContract(contract=contract, host=host)


def _reject_unknown(what: str, data: Mapping[str, Any], allowed: set[str]) -> None:
    """A key nobody reads is a promise nobody keeps.

    Silently dropping it is how a contract comes to mean one thing in the file
    and another in the host that loaded it.
    """

    if not isinstance(data, Mapping):
        raise ContractError(f"{what} must be an object, got {type(data).__name__}")
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ContractError(f"unknown {what} keys: {unknown}")
