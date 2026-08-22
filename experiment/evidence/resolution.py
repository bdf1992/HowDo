"""The resolution block: what participated in a trial's resolved work context.

A crossing is a projection over evidence, not a persisted object. ``Skill x
Environment`` names a hypothesis about interaction between receipt dimensions;
it is instantiated by querying receipts, and every property derived that way --
strength, directionality, invariance, higher-order structure -- can be
recomputed when the research model changes.

One part of that cannot be recomputed: which resolution a trial actually ran
against. The operands, their order, and the resolver that assembled them are
gone the moment the container exits. So they are the only part that is frozen
into the receipt.

Nothing here interprets a resolution. Whether a given set of operands
represents an interaction, an invariance, a confound, or a coincidence is a
downstream question, answered from many receipts rather than declared in one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping
import hashlib
import json
import re

__all__ = [
    "RESOLUTION_VERSION",
    "Resolution",
    "ResolutionOperand",
    "resolution_fields",
    "verify_resolution",
]

# Canonicalization rules are exactly the sort of thing that changes. Without a
# version in the hashed payload, a historical digest becomes uninterpretable:
# you could not tell a different resolution from the same resolution serialized
# under different rules.
RESOLUTION_VERSION = 1

# ``role`` and ``kind`` are our vocabulary, so they are constrained: an
# uppercase "Environment" and a lowercase "environment" would otherwise hash
# differently and silently fork the same resolution into two. ``identity`` and
# ``digest`` come from outside and are left alone.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ResolutionError(ValueError):
    """A resolution that cannot be committed to honestly."""


def _required(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ResolutionError(f"{name} must be a string, got {type(value).__name__}")
    cleaned = value.strip()
    if not cleaned:
        raise ResolutionError(f"{name} must not be empty")
    return cleaned


def _slug(name: str, value: str) -> str:
    cleaned = _required(name, value)
    if not _SLUG.match(cleaned):
        raise ResolutionError(
            f"{name} must match {_SLUG.pattern} so casing cannot fork the digest; "
            f"got {value!r}"
        )
    return cleaned


@dataclass(frozen=True)
class ResolutionOperand:
    """One participant in a resolved work context.

    ``role`` is what it played here; ``kind`` is what sort of thing it is. They
    are separate because the same kind can play different roles, and because
    ``Skill(foo) + Environment(bar)`` must not be confusable with
    ``Environment(foo) + Skill(bar)``.
    """

    role: str
    kind: str
    identity: str
    digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _slug("role", self.role))
        object.__setattr__(self, "kind", _slug("kind", self.kind))
        object.__setattr__(self, "identity", _required("identity", self.identity))
        object.__setattr__(self, "digest", _required("digest", self.digest))

    def as_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "kind": self.kind,
            "identity": self.identity,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class Resolution:
    """An ordered, resolver-attributed commitment to one trial's work context.

    Order is recorded even though nothing currently treats ``A x B`` and
    ``B x A`` differently. It costs four bytes of JSON and it is the evidence
    needed to discover later that orientation mattered; recovering it after the
    fact is impossible.

    The resolver is recorded because resolution may be generated rather than
    declared. Two trials can carry the same skill, environment, and task while
    one resolver orders verification before planning and the other reverses
    them. If resolution is part of the treatment, that difference is part of
    the evidence.
    """

    builder_id: str
    builder_digest: str
    operands: tuple[ResolutionOperand, ...]
    version: int = RESOLUTION_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "builder_id", _slug("builder_id", self.builder_id))
        object.__setattr__(
            self, "builder_digest", _required("builder_digest", self.builder_digest)
        )
        operands = tuple(self.operands)
        if not operands:
            raise ResolutionError("a resolution needs at least one operand")
        for operand in operands:
            if not isinstance(operand, ResolutionOperand):
                raise ResolutionError(
                    f"operands must be ResolutionOperand, got {type(operand).__name__}"
                )
        object.__setattr__(self, "operands", operands)
        if not isinstance(self.version, int) or self.version < 1:
            raise ResolutionError(f"version must be a positive int, got {self.version!r}")

    def canonical_bytes(self) -> bytes:
        """The exact bytes the digest commits to.

        JSON with sorted object keys and preserved array order: canonical where
        it must be, ordered where the ordering is the evidence. Every field is
        a quoted, escaped string inside a typed structure, so arity, role, and
        kind are all committed and no value can be crafted to impersonate the
        surrounding syntax.
        """
        payload = {
            "resolution_version": self.version,
            "builder_id": self.builder_id,
            "builder_digest": self.builder_digest,
            "operands": [operand.as_dict() for operand in self.operands],
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def as_receipt_block(self) -> dict[str, object]:
        """The immutable block, shaped for the evidence receipt."""
        return {
            "resolution_version": self.version,
            "resolution_builder_id": self.builder_id,
            "resolution_builder_digest": self.builder_digest,
            "resolution_operands": [operand.as_dict() for operand in self.operands],
            "resolution_digest": self.digest,
        }


def resolution_fields(
    *,
    builder_id: str,
    builder_digest: str,
    operands: Iterable[Mapping[str, str] | ResolutionOperand],
    version: int = RESOLUTION_VERSION,
) -> dict[str, object]:
    """Build the receipt block from loosely-typed operand records."""
    built = tuple(
        operand
        if isinstance(operand, ResolutionOperand)
        else ResolutionOperand(
            role=operand["role"],
            kind=operand["kind"],
            identity=operand["identity"],
            digest=operand["digest"],
        )
        for operand in operands
    )
    return Resolution(
        builder_id=builder_id,
        builder_digest=builder_digest,
        operands=built,
        version=version,
    ).as_receipt_block()


def verify_resolution(block: Mapping[str, object]) -> bool:
    """Recompute a stored block's digest and report whether it still holds.

    The point of a digest in an append-only log is that a later reader can
    check it without trusting the writer.
    """
    try:
        rebuilt = Resolution(
            builder_id=str(block["resolution_builder_id"]),
            builder_digest=str(block["resolution_builder_digest"]),
            operands=tuple(
                ResolutionOperand(
                    role=str(entry["role"]),
                    kind=str(entry["kind"]),
                    identity=str(entry["identity"]),
                    digest=str(entry["digest"]),
                )
                for entry in block["resolution_operands"]  # type: ignore[union-attr]
            ),
            version=int(block["resolution_version"]),  # type: ignore[arg-type]
        )
    except (KeyError, TypeError, ResolutionError):
        return False
    return rebuilt.digest == block.get("resolution_digest")
