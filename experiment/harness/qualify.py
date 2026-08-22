"""Turn Harbor oracle and no-op runs into a qualification record.

Qualification is the cheap half of the programme and the half most worth doing
first: it needs no model inference at all. The oracle run executes the task's
own ``solution/solve.sh``; the no-op run executes nothing. Both are container
work, so the whole candidate pool can be qualified in hours rather than the
weeks a screening pass costs.

Nothing here decides an outcome. ``evidence/qualification.py`` derives that from
the counts, and this module only counts -- carefully, because the two counts it
gets wrong in opposite directions are the two that bias a study:

* An infrastructure error counted as an oracle failure makes a solvable task
  look unsolvable, and it is dropped from a pool that is already small.
* An infrastructure error counted as a no-op failure makes a vacuous verifier
  look strict, and the task stays in and dilutes both arms.

So errors are counted as errors, in their own bucket, against the flake cap.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from evidence import NOOP_ATTEMPTS, ORACLE_ATTEMPTS, Qualification

__all__ = ["QualificationCounts", "count_runs", "qualify_task"]


class QualificationCounts:
    """What the oracle and no-op runs actually did."""

    __slots__ = ("oracle_attempts", "oracle_passes", "noop_attempts", "noop_failures",
                 "infrastructure_errors")

    def __init__(self) -> None:
        self.oracle_attempts = 0
        self.oracle_passes = 0
        self.noop_attempts = 0
        self.noop_failures = 0
        self.infrastructure_errors = 0

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"QualificationCounts(oracle={self.oracle_passes}/{self.oracle_attempts}, "
            f"noop_failed={self.noop_failures}/{self.noop_attempts}, "
            f"errors={self.infrastructure_errors})"
        )


def _errored(result: Mapping[str, Any]) -> bool:
    exception = result.get("exception_info")
    return isinstance(exception, Mapping) and bool(exception.get("exception_type"))


def _solved(result: Mapping[str, Any]) -> bool | None:
    """True, False, or None when the run produced no readable outcome."""
    verifier = result.get("verifier_result")
    if not isinstance(verifier, Mapping):
        return None
    rewards = verifier.get("rewards")
    if not isinstance(rewards, Mapping) or "reward" not in rewards:
        return None
    reward = rewards["reward"]
    if reward == 1:
        return True
    if reward == 0:
        return False
    # A partial reward during qualification is the verifier telling you it is not
    # the binary instrument this study assumes. Neither bucket is honest.
    return None


def count_runs(
    oracle_results: Iterable[Mapping[str, Any]],
    noop_results: Iterable[Mapping[str, Any]],
) -> QualificationCounts:
    counts = QualificationCounts()
    for result in oracle_results:
        if _errored(result):
            counts.infrastructure_errors += 1
            continue
        solved = _solved(result)
        if solved is None:
            counts.infrastructure_errors += 1
            continue
        counts.oracle_attempts += 1
        counts.oracle_passes += int(solved)
    for result in noop_results:
        if _errored(result):
            counts.infrastructure_errors += 1
            continue
        solved = _solved(result)
        if solved is None:
            counts.infrastructure_errors += 1
            continue
        counts.noop_attempts += 1
        counts.noop_failures += int(not solved)
    return counts


def qualify_task(
    *,
    suite: str,
    suite_version: str,
    task_id: str,
    task_version: str,
    task_definition_digest: str,
    harbor_version: str,
    image_digest: str,
    verifier_kind: str,
    oracle_results: Iterable[Mapping[str, Any]],
    noop_results: Iterable[Mapping[str, Any]],
) -> Qualification:
    """Count the runs and hand them to the deriving record.

    A short-of-target run is not padded here. ``Qualification`` rejects a task
    whose oracle ran fewer than the required number of times, and inventing the
    missing attempts to get past that would be the whole point of the rule
    defeated in one line.
    """
    counts = count_runs(oracle_results, noop_results)
    return Qualification(
        suite=suite,
        suite_version=suite_version,
        task_id=task_id,
        task_version=task_version,
        task_definition_digest=task_definition_digest,
        harbor_version=harbor_version,
        image_digest=image_digest,
        verifier_kind=verifier_kind,
        oracle_attempts=counts.oracle_attempts,
        oracle_passes=counts.oracle_passes,
        noop_attempts=counts.noop_attempts,
        noop_failures=counts.noop_failures,
        infrastructure_errors=counts.infrastructure_errors,
    )


REQUIRED_ORACLE_ATTEMPTS = ORACLE_ATTEMPTS
REQUIRED_NOOP_ATTEMPTS = NOOP_ATTEMPTS
