"""Harbor trial result -> evidence receipt.

Harbor owns execution. This is the seam, and nothing more: it reads what Harbor
already wrote and produces the receipt the experiment commits to. It does not
run trials, does not retry, and does not decide anything the preregistration
decides.

Everything here refuses rather than guesses, because every guess in this file
becomes evidence:

* **A reward that is neither 0 nor 1 is refused.** Harbor allows partial
  rewards. Rounding one into a pass or a fail invents an outcome the verifier
  did not report, and it would be invisible in the aggregate afterwards. If a
  suite with partial credit is ever committed, the preregistration must say how
  it maps, before the data exists.
* **A model that does not match the organism lock is refused.** ``RECEIPT.md``
  declares that no structural check can tell a receipt saying ``arm: h1`` from a
  harness that ran H0. That is true of the arm. It is *not* true of the
  organism: Harbor records which model ran, the lock records which model was
  frozen, and a disagreement is mechanically visible. Checking it closes part of
  a gap the contract declared open.
* **An exception is an error, never a failure.** A trial that crashed did not
  measure the treatment. Filing it as a failed attempt would let infrastructure
  trouble read as the organism being bad at the task.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import re

from evidence import build_receipt

__all__ = [
    "IngestError",
    "ingest_trial",
    "read_trial_result",
    "wall_clock_seconds",
]

_DIGEST = re.compile(r"^[0-9a-f]{64}$")

# Harbor's scalar outcome. See ``rewards["reward"]`` in its CLI and uploader:
# 1 is solved, 0 is not.
_REWARD_KEY = "reward"

# Harbor exception type -> the receipt's closed failure vocabulary. Anything
# unmapped becomes ``other``, which is honest, rather than being forced into a
# neighbouring class that would make the tally wrong.
_FAILURE_BY_EXCEPTION = {
    "TimeoutError": "harness_timeout",
    "AgentTimeoutError": "harness_timeout",
    "asyncio.TimeoutError": "harness_timeout",
    "OutOfMemoryError": "oom",
    "MemoryError": "oom",
    "DockerException": "runtime_crash",
    "ContainerError": "runtime_crash",
    "ImageNotFound": "runtime_crash",
    "BuildError": "runtime_crash",
    "VerifierError": "verifier_infrastructure",
}


class IngestError(ValueError):
    """A Harbor result that cannot honestly become a receipt."""


def read_trial_result(path: str | Path) -> dict[str, Any]:
    """Load one Harbor ``TrialResult`` JSON document."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IngestError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(document, Mapping):
        raise IngestError(f"{path} is not a trial result object")
    return dict(document)


def _timing(result: Mapping[str, Any], key: str) -> float | None:
    from datetime import datetime

    block = result.get(key)
    if not isinstance(block, Mapping):
        return None
    start, finish = block.get("started_at"), block.get("finished_at")
    if not start or not finish:
        return None
    parse = lambda value: datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return (parse(finish) - parse(start)).total_seconds()


def wall_clock_seconds(result: Mapping[str, Any]) -> float:
    """End-to-end trial time, including setup and verification.

    Not agent execution alone. A configuration spending ninety seconds per trial
    in container setup is a slow configuration, and hours-per-100-trials has to
    see that.
    """
    from datetime import datetime

    start, finish = result.get("started_at"), result.get("finished_at")
    if start and finish:
        parse = lambda value: datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (parse(finish) - parse(start)).total_seconds()
    phases = [
        _timing(result, name)
        for name in ("environment_setup", "agent_setup", "agent_execution", "verifier")
    ]
    measured = [value for value in phases if value is not None]
    if not measured:
        raise IngestError("the trial result carries no timing at all")
    return sum(measured)


def _outcome(result: Mapping[str, Any]) -> tuple[str, str | None]:
    """(result, failure_class). Refuses anything it cannot read exactly."""
    exception = result.get("exception_info")
    if isinstance(exception, Mapping) and exception.get("exception_type"):
        kind = str(exception["exception_type"])
        return "error", _FAILURE_BY_EXCEPTION.get(kind, "other")

    verifier = result.get("verifier_result")
    if not isinstance(verifier, Mapping):
        raise IngestError(
            "no verifier_result and no exception: the trial neither completed "
            "nor failed, and guessing which would invent the evidence"
        )
    rewards = verifier.get("rewards")
    if not isinstance(rewards, Mapping) or _REWARD_KEY not in rewards:
        raise IngestError(
            f"verifier_result has no {_REWARD_KEY!r} key; refusing to infer an "
            "outcome from a reward vocabulary this study has not declared"
        )
    reward = rewards[_REWARD_KEY]
    if reward == 1:
        return "pass", None
    if reward == 0:
        return "fail", None
    raise IngestError(
        f"partial reward {reward!r}: rounding it would invent an outcome the "
        "verifier did not report. Declare the mapping in the preregistration "
        "before committing a suite that awards partial credit"
    )


def _task_definition_digest(result: Mapping[str, Any]) -> str:
    """Harbor's ``task_checksum``, normalised to a content address.

    Harbor does not promise the checksum is a bare SHA-256 hex string. When it
    is, it passes through unchanged so the two systems agree on one identity;
    when it is not, it is hashed, which keeps the receipt's format invariant
    without pretending the value came from somewhere it did not.
    """
    checksum = str(result.get("task_checksum") or "").strip().lower()
    if not checksum:
        raise IngestError("the trial result carries no task_checksum")
    if _DIGEST.match(checksum):
        return checksum
    return hashlib.sha256(checksum.encode("utf-8")).hexdigest()


def _check_organism(result: Mapping[str, Any], organism: Mapping[str, Any]) -> None:
    agent = result.get("agent_info")
    model = (agent or {}).get("model_info") if isinstance(agent, Mapping) else None
    if not isinstance(model, Mapping) or not model.get("name"):
        # Harbor does not always record a model name. Absent is not a mismatch,
        # and refusing here would block ingestion on a field the runner controls.
        return
    ran = str(model["name"])
    frozen = str(organism.get("organism_model_name") or organism.get("organism_model_file") or "")
    if not frozen:
        return
    if ran not in frozen and frozen not in ran:
        raise IngestError(
            f"Harbor ran model {ran!r} but the organism lock froze {frozen!r}. "
            "Receipts under two organisms are never pooled, so this trial cannot "
            "carry this fingerprint"
        )


def ingest_trial(
    result: Mapping[str, Any],
    *,
    experiment: Mapping[str, Any],
    organism: Mapping[str, Any],
    treatment: Mapping[str, Any],
    resolution: Mapping[str, Any],
    suite: str,
    suite_version: str,
    task_qualification_digest: str,
    image_ref: str,
    image_digest: str,
    environment_context_digest: str | None,
    verifier_kind: str,
    verifier_output_digest: str,
    trajectory_digest: str | None = None,
    artifact_digests: tuple[str, ...] = (),
    peak_vram_bytes: int | None = None,
) -> dict[str, Any]:
    """Build one receipt from one Harbor trial result.

    Everything Harbor knows is read from ``result``. Everything Harbor cannot
    know -- which arm this was, which preregistration was in force, which
    organism was frozen -- is passed in by the runner, because inferring any of
    it from the trial output would be inventing it.
    """
    outcome_result, failure_class = _outcome(result)
    _check_organism(result, organism)

    tokens = result.get("agent_result") or {}
    if not isinstance(tokens, Mapping):
        tokens = {}
    # ``n_input_tokens`` is documented as total input *including* cache, so cache
    # is not added to it.
    prompt_tokens = tokens.get("n_input_tokens")
    completion_tokens = tokens.get("n_output_tokens")

    outcome: dict[str, Any] = {
        "result": outcome_result,
        "verifier_kind": verifier_kind,
        "verifier_exit_code": None if outcome_result == "error" else int(outcome_result != "pass"),
        "verifier_output_digest": verifier_output_digest,
    }
    if failure_class is not None:
        outcome["failure_class"] = failure_class

    return build_receipt(
        experiment=dict(experiment),
        benchmark={
            "suite": suite,
            "suite_version": suite_version,
            "task_id": str(result.get("task_name") or ""),
            "task_version": _task_definition_digest(result)[:12],
            "task_qualification_digest": task_qualification_digest,
        },
        environment={
            "image_ref": image_ref,
            "image_digest": image_digest,
            "environment_context_digest": environment_context_digest,
        },
        organism=dict(organism),
        treatment=dict(treatment),
        resolution=dict(resolution),
        outcome=outcome,
        resources={
            "wall_clock_seconds": wall_clock_seconds(result),
            "prompt_tokens": prompt_tokens if prompt_tokens is not None else 0,
            "completion_tokens": completion_tokens if completion_tokens is not None else 0,
            "peak_vram_bytes": peak_vram_bytes if peak_vram_bytes is not None else 0,
        },
        custody={
            "trajectory_digest": trajectory_digest,
            "artifact_digests": list(artifact_digests),
        },
    )
