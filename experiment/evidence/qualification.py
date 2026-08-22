"""Task qualification: what earns a benchmark task the authority to count.

Two kinds of unqualified task bias a study rather than merely adding noise to
it. A task nothing can solve scores zero in every arm and shrinks the effective
sample while the task count says otherwise. A task that passes without being
solved scores one in every arm and pulls any real effect toward zero. Both look
ordinary in an aggregate score, and neither is detectable afterwards without
running the trials that would have detected them beforehand.

So the outcome here is derived from counts, exactly as ``certifies`` is derived
in the receipt. A field a writer can assert is a field that will eventually be
asserted by a script under deadline pressure.

See ``TASK-QUALIFICATION.md`` for the procedure and for what qualification does
not establish.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

__all__ = [
    "MAX_INFRASTRUCTURE_ERROR_RATE",
    "NOOP_ATTEMPTS",
    "ORACLE_ATTEMPTS",
    "OUTCOMES",
    "Qualification",
    "QualificationError",
    "qualification_fields",
    "verify_qualification",
]

QUALIFICATION_VERSION = 1

# Five, not one: a task passing 4/5 under a known-good solution is not a
# solvable task with a flake, it is a task whose fixture or verifier is
# nondeterministic, and that variance will land in the study attributed to the
# treatment.
ORACLE_ATTEMPTS = 5

# Three is enough. One no-op pass is already disqualifying, so the repeats are
# only there to catch a verifier that accepts the initial state intermittently.
NOOP_ATTEMPTS = 3

MAX_INFRASTRUCTURE_ERROR_RATE = 0.20

OUTCOMES = ("qualified", "research_only", "rejected")
VERIFIER_KINDS = ("deterministic", "judge")


class QualificationError(ValueError):
    """A qualification record that cannot be committed to honestly."""


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QualificationError(f"{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _count(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise QualificationError(f"{name} must be a non-negative int, got {value!r}")
    return value


@dataclass(frozen=True)
class Qualification:
    """One task's qualification record.

    ``outcome`` and ``rejection_reason`` are properties, not fields. The record
    holds what was observed; what it means is recomputed by anyone reading it.
    """

    suite: str
    suite_version: str
    task_id: str
    task_version: str
    task_definition_digest: str
    harbor_version: str
    image_digest: str
    verifier_kind: str
    oracle_attempts: int
    oracle_passes: int
    noop_attempts: int
    noop_failures: int
    infrastructure_errors: int
    version: int = QUALIFICATION_VERSION

    def __post_init__(self) -> None:
        for name in (
            "suite",
            "suite_version",
            "task_id",
            "task_version",
            "task_definition_digest",
            "harbor_version",
            "image_digest",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.verifier_kind not in VERIFIER_KINDS:
            raise QualificationError(
                f"verifier_kind must be one of {', '.join(VERIFIER_KINDS)}; "
                f"got {self.verifier_kind!r}"
            )
        for name in (
            "oracle_attempts",
            "oracle_passes",
            "noop_attempts",
            "noop_failures",
            "infrastructure_errors",
        ):
            object.__setattr__(self, name, _count(name, getattr(self, name)))
        if self.oracle_passes > self.oracle_attempts:
            raise QualificationError("oracle_passes cannot exceed oracle_attempts")
        if self.noop_failures > self.noop_attempts:
            raise QualificationError("noop_failures cannot exceed noop_attempts")
        if not isinstance(self.version, int) or self.version < 1:
            raise QualificationError(f"version must be a positive int, got {self.version!r}")

    @property
    def total_attempts(self) -> int:
        return self.oracle_attempts + self.noop_attempts + self.infrastructure_errors

    @property
    def infrastructure_error_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.infrastructure_errors / self.total_attempts

    @property
    def rejection_reason(self) -> str | None:
        """Why this task cannot count, or None. Checked in a fixed order so two
        readers of the same record give the same reason."""
        if self.oracle_attempts < ORACLE_ATTEMPTS:
            return (
                f"oracle ran {self.oracle_attempts} times; {ORACLE_ATTEMPTS} are required "
                "to separate a solvable task from a nondeterministic one"
            )
        if self.oracle_passes < self.oracle_attempts:
            return (
                f"oracle passed {self.oracle_passes}/{self.oracle_attempts}; a "
                "known-good solution that does not always pass indicts the fixture "
                "or the verifier, not the solution"
            )
        if self.noop_attempts < NOOP_ATTEMPTS:
            return f"no-op ran {self.noop_attempts} times; {NOOP_ATTEMPTS} are required"
        if self.noop_failures < self.noop_attempts:
            passes = self.noop_attempts - self.noop_failures
            return (
                f"a no-op agent passed {passes} time(s); the verifier accepts the "
                "initial state, so the task measures nothing and dilutes both arms"
            )
        if self.infrastructure_error_rate > MAX_INFRASTRUCTURE_ERROR_RATE:
            return (
                f"infrastructure error rate {self.infrastructure_error_rate:.0%} exceeds "
                f"{MAX_INFRASTRUCTURE_ERROR_RATE:.0%}; the exclusions it produces are "
                "decisions made after the data is visible"
            )
        return None

    @property
    def outcome(self) -> str:
        if self.rejection_reason is not None:
            return "rejected"
        # A judge-scored task informs research and never certifies. The judge
        # configuration has changed across Harbor eras, so its numbers are not
        # comparable across time even against themselves.
        if self.verifier_kind == "judge":
            return "research_only"
        return "qualified"

    @property
    def certifies(self) -> bool:
        return self.outcome == "qualified"

    def canonical_bytes(self) -> bytes:
        payload = {
            "qualification_version": self.version,
            "suite": self.suite,
            "suite_version": self.suite_version,
            "task_id": self.task_id,
            "task_version": self.task_version,
            "task_definition_digest": self.task_definition_digest,
            "harbor_version": self.harbor_version,
            "image_digest": self.image_digest,
            "verifier_kind": self.verifier_kind,
            "oracle_attempts": self.oracle_attempts,
            "oracle_passes": self.oracle_passes,
            "noop_attempts": self.noop_attempts,
            "noop_failures": self.noop_failures,
            "infrastructure_errors": self.infrastructure_errors,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        """The ``task_qualification_digest`` a receipt carries.

        It commits to the counts, so a receipt is citing the evidence that
        granted the authority rather than a claim that qualification happened.
        """
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def as_record(self) -> dict[str, Any]:
        record = json.loads(self.canonical_bytes())
        record["outcome"] = self.outcome
        record["rejection_reason"] = self.rejection_reason
        record["certifies"] = self.certifies
        record["task_qualification_digest"] = self.digest
        return record


def qualification_fields(**kwargs: Any) -> dict[str, Any]:
    """Build the stored record from loose keyword arguments."""
    return Qualification(**kwargs).as_record()


def verify_qualification(record: Mapping[str, Any]) -> bool:
    """Recompute the digest and the derived outcome. Never raises.

    Rechecking the outcome as well as the digest means a record edited to
    promote a rejected task fails even if its digest was recomputed to match.
    """
    if not isinstance(record, Mapping):
        return False
    try:
        rebuilt = Qualification(
            suite=record["suite"],
            suite_version=record["suite_version"],
            task_id=record["task_id"],
            task_version=record["task_version"],
            task_definition_digest=record["task_definition_digest"],
            harbor_version=record["harbor_version"],
            image_digest=record["image_digest"],
            verifier_kind=record["verifier_kind"],
            oracle_attempts=record["oracle_attempts"],
            oracle_passes=record["oracle_passes"],
            noop_attempts=record["noop_attempts"],
            noop_failures=record["noop_failures"],
            infrastructure_errors=record["infrastructure_errors"],
            version=record["qualification_version"],
        )
    except (AttributeError, KeyError, TypeError, QualificationError):
        return False
    return (
        rebuilt.digest == record.get("task_qualification_digest")
        and rebuilt.outcome == record.get("outcome")
        and rebuilt.certifies == record.get("certifies")
    )
