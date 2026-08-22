"""The evidence receipt: one trial, written once, never edited.

Receipts are primary state. Everything the research programme wants to say --
capability edges, interaction claims, levels, routing -- is a projection over
them, recomputable when the theory changes. The receipt is not recomputable,
which is why the rule is: a field belongs here if and only if it is gone once
the container exits.

The invariants below exist because each of them, unenforced, produces evidence
that looks correct and is not:

* A ``certifies`` flag a writer can set turns "deterministic verification only"
  into a convention. It is derived here and refused as an input.
* A ``failure_class`` optional on errors makes every unexplained error look like
  an ordinary failure in aggregate.
* A ``run_sequence_index`` that may repeat makes interleaving unverifiable after
  the fact, and drift over a long run is exactly what interleaving defends
  against.
* A trajectory stored as a path is a claim about a machine that will be
  reformatted. A digest survives it.
* A history that can be edited makes an analysis that benefited from an edit
  indistinguishable from one that did not.

See ``RECEIPT.md`` for the contract this implements, including the list of
things it deliberately does not enforce.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping
import hashlib
import json
import re

__all__ = [
    "ANALYSIS_CLASSES",
    "ARMS",
    "FAILURE_CLASSES",
    "RECEIPT_VERSION",
    "RECON_OUTCOMES",
    "RESULTS",
    "VERIFIER_KINDS",
    "ReceiptError",
    "append_receipt",
    "build_receipt",
    "correct_receipt",
    "corrections_for",
    "read_receipts",
    "verify_receipt",
]

RECEIPT_VERSION = 1

RESULTS = ("pass", "fail", "error", "excluded")
# ``error`` and ``excluded`` are the two that did not measure the treatment.
_NEEDS_FAILURE_CLASS = ("error", "excluded")

FAILURE_CLASSES = (
    "oom",
    "runtime_crash",
    "harness_timeout",
    "context_truncation",
    "verifier_infrastructure",
    "reconnaissance_failed",
    "preregistered_exclusion",
    "other",
)
VERIFIER_KINDS = ("deterministic", "judge")
ANALYSIS_CLASSES = ("confirmatory", "exploratory", "rehearsal")
ARMS = ("h0", "h1", "h2")
RECON_OUTCOMES = ("complete", "over_budget", "failed", "not_applicable")

_SECTIONS = {
    "experiment": (
        "experiment_id",
        "preregistration_digest",
        "analysis_class",
        "condition_label",
        "run_sequence_index",
        "trial_id",
    ),
    "benchmark": (
        "suite",
        "suite_version",
        "task_id",
        "task_version",
        "task_qualification_digest",
    ),
    "environment": ("image_ref", "image_digest", "environment_context_digest"),
    "organism": ("organism_version", "organism_fingerprint"),
    "treatment": (
        "arm",
        "skill_commit",
        "skill_content_digest",
        "recon_budget",
        "recon_used",
        "recon_outcome",
    ),
    "resolution": ("resolution_version", "resolution_digest"),
    "outcome": (
        "result",
        "verifier_kind",
        "verifier_exit_code",
        "verifier_output_digest",
    ),
    "resources": (
        "wall_clock_seconds",
        "prompt_tokens",
        "completion_tokens",
        "peak_vram_bytes",
    ),
    "custody": ("trajectory_digest", "artifact_digests"),
}

# Fields that may legitimately be absent because the arm does not have them.
_NULLABLE = {
    ("environment", "environment_context_digest"),
    ("outcome", "verifier_exit_code"),
    ("custody", "trajectory_digest"),
}

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class ReceiptError(ValueError):
    """A receipt that cannot be written honestly."""


def _fail(message: str) -> None:
    raise ReceiptError(message)


def _digest_field(where: str, value: Any, *, nullable: bool = False) -> None:
    if value is None:
        if nullable:
            return
        _fail(f"{where} must be a content address, got null")
    if not isinstance(value, str) or not _DIGEST.match(value):
        _fail(
            f"{where} must be a lowercase sha256 hex digest, got {value!r}. "
            "A path is a claim about a machine that will be reformatted"
        )


def _one_of(where: str, value: Any, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        _fail(f"{where} must be one of {', '.join(allowed)}; got {value!r}")


def _non_negative_int(where: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(f"{where} must be a non-negative int, got {value!r}")


def _validate(record: Mapping[str, Any]) -> None:
    unknown = set(record) - set(_SECTIONS) - {"receipt_version", "receipt_digest"}
    if unknown:
        _fail(f"unknown top-level sections: {', '.join(sorted(unknown))}")

    for name, fields in _SECTIONS.items():
        section = record.get(name)
        if not isinstance(section, Mapping):
            _fail(f"{name} must be an object, got {type(section).__name__}")
        missing = [key for key in fields if key not in section]
        if missing:
            _fail(f"{name} is missing required fields: {', '.join(sorted(missing))}")
        for key in fields:
            if section[key] is None and (name, key) not in _NULLABLE:
                _fail(f"{name}.{key} must be filled")

    experiment = record["experiment"]
    _one_of("experiment.analysis_class", experiment["analysis_class"], ANALYSIS_CLASSES)
    _non_negative_int("experiment.run_sequence_index", experiment["run_sequence_index"])
    if experiment["analysis_class"] == "confirmatory":
        # A confirmatory trial with no preregistration in force is an
        # exploratory trial wearing the word.
        _digest_field(
            "experiment.preregistration_digest", experiment["preregistration_digest"]
        )

    _digest_field(
        "benchmark.task_qualification_digest",
        record["benchmark"]["task_qualification_digest"],
    )

    treatment = record["treatment"]
    _one_of("treatment.arm", treatment["arm"], ARMS)
    _one_of("treatment.recon_outcome", treatment["recon_outcome"], RECON_OUTCOMES)
    if treatment["arm"] == "h0" and treatment["recon_outcome"] != "not_applicable":
        _fail("treatment.recon_outcome must be not_applicable in the h0 arm")
    if treatment["arm"] != "h0" and treatment["recon_outcome"] == "not_applicable":
        _fail(f"treatment.recon_outcome cannot be not_applicable in the {treatment['arm']} arm")

    outcome = record["outcome"]
    _one_of("outcome.result", outcome["result"], RESULTS)
    _one_of("outcome.verifier_kind", outcome["verifier_kind"], VERIFIER_KINDS)
    _digest_field("outcome.verifier_output_digest", outcome["verifier_output_digest"])

    needs_class = outcome["result"] in _NEEDS_FAILURE_CLASS
    has_class = outcome.get("failure_class") is not None
    if needs_class and not has_class:
        _fail(
            f"outcome.failure_class is required when result is {outcome['result']!r}; "
            "an untyped error is indistinguishable from an ordinary failure in aggregate"
        )
    if has_class and not needs_class:
        _fail(
            f"outcome.failure_class is refused when result is {outcome['result']!r}; "
            "a trial that measured the treatment did not fail infrastructurally"
        )
    if has_class:
        _one_of("outcome.failure_class", outcome["failure_class"], FAILURE_CLASSES)

    _digest_field(
        "custody.trajectory_digest", record["custody"]["trajectory_digest"], nullable=True
    )
    artifacts = record["custody"]["artifact_digests"]
    if not isinstance(artifacts, (list, tuple)):
        _fail("custody.artifact_digests must be a list")
    for index, digest in enumerate(artifacts):
        _digest_field(f"custody.artifact_digests[{index}]", digest)


def _certifies(record: Mapping[str, Any]) -> bool:
    """Whether this trial may advance a capability claim.

    Derived rather than declared. Deterministic verification only, at least
    through M3: a judge-scored trial informs research and never certifies. The
    rule is worth nothing if a writer can assert it.
    """
    return (
        record["outcome"]["result"] == "pass"
        and record["outcome"]["verifier_kind"] == "deterministic"
        and record["experiment"]["analysis_class"] == "confirmatory"
    )


def _canonical_bytes(record: Mapping[str, Any]) -> bytes:
    payload = {key: value for key, value in record.items() if key != "receipt_digest"}
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def build_receipt(
    *,
    experiment: Mapping[str, Any],
    benchmark: Mapping[str, Any],
    environment: Mapping[str, Any],
    organism: Mapping[str, Any],
    treatment: Mapping[str, Any],
    resolution: Mapping[str, Any],
    outcome: Mapping[str, Any],
    resources: Mapping[str, Any],
    custody: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the sections and return a digested, complete receipt."""
    if "certifies" in outcome:
        raise ReceiptError(
            "outcome.certifies is derived, not written. A writer that can assert "
            "certification makes 'deterministic verifiers only' a convention"
        )
    record: dict[str, Any] = {
        "receipt_version": RECEIPT_VERSION,
        "experiment": dict(experiment),
        "benchmark": dict(benchmark),
        "environment": dict(environment),
        "organism": dict(organism),
        "treatment": dict(treatment),
        "resolution": dict(resolution),
        "outcome": dict(outcome),
        "resources": dict(resources),
        "custody": dict(custody),
    }
    _validate(record)
    record["outcome"]["certifies"] = _certifies(record)
    record["receipt_digest"] = hashlib.sha256(_canonical_bytes(record)).hexdigest()
    return record


def verify_receipt(record: Mapping[str, Any]) -> bool:
    """Recompute the digest and the derived certification. Never raises.

    Checking ``certifies`` here as well as at write time is the point: a
    receipt hand-edited to certify a judge-scored trial fails verification even
    though its digest was recomputed to match.
    """
    if not isinstance(record, Mapping):
        return False
    try:
        if hashlib.sha256(_canonical_bytes(record)).hexdigest() != record["receipt_digest"]:
            return False
        return record["outcome"]["certifies"] == _certifies(record)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def read_receipts(path: str | Path) -> list[dict[str, Any]]:
    """Every receipt in the log, in written order."""
    target = Path(path)
    if not target.exists():
        return []
    records = []
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ReceiptError(f"{path} line {number} is not valid JSON: {exc}") from exc
    return records


def _last_index(records: Iterable[Mapping[str, Any]], experiment_id: str) -> int | None:
    highest = None
    for record in records:
        section = record.get("experiment", {})
        if section.get("experiment_id") != experiment_id:
            continue
        index = section.get("run_sequence_index")
        if isinstance(index, int) and (highest is None or index > highest):
            highest = index
    return highest


def append_receipt(path: str | Path, record: Mapping[str, Any]) -> dict[str, Any]:
    """Append one receipt. Never rewrites, never reorders.

    Refuses an out-of-order ``run_sequence_index`` because the order trials ran
    in is the only evidence that the arms were interleaved, and it cannot be
    reconstructed from a file that accepted them in any order.
    """
    if not verify_receipt(record):
        raise ReceiptError("refusing to append a receipt that does not verify")
    target = Path(path)
    experiment_id = record["experiment"]["experiment_id"]
    index = record["experiment"]["run_sequence_index"]
    previous = _last_index(read_receipts(target), experiment_id)
    if previous is not None and index <= previous:
        raise ReceiptError(
            f"run_sequence_index {index} is not after {previous} for {experiment_id!r}; "
            "the log records the order trials actually ran in"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return dict(record)


def correct_receipt(
    path: str | Path,
    *,
    corrects_digest: str,
    reason: str,
    corrected_fields: Mapping[str, Any],
) -> dict[str, Any]:
    """Append a correction. The original stays exactly where it is.

    Deleting or editing the original would make an analysis that benefited from
    the edit indistinguishable from one that did not, so a correction is another
    entry in the log rather than a change to it.
    """
    if not _DIGEST.match(corrects_digest or ""):
        raise ReceiptError("corrects_digest must be a sha256 hex digest")
    if not reason or not reason.strip():
        raise ReceiptError("a correction must say why")
    existing = {record.get("receipt_digest") for record in read_receipts(path)}
    if corrects_digest not in existing:
        raise ReceiptError(
            f"no receipt with digest {corrects_digest} in this log; "
            "a correction must name the entry it corrects"
        )
    correction: dict[str, Any] = {
        "receipt_version": RECEIPT_VERSION,
        "correction": {
            "corrects_digest": corrects_digest,
            "reason": reason.strip(),
            "corrected_fields": dict(corrected_fields),
        },
    }
    correction["receipt_digest"] = hashlib.sha256(_canonical_bytes(correction)).hexdigest()
    target = Path(path)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(correction, sort_keys=True, ensure_ascii=False) + "\n")
    return correction


def corrections_for(path: str | Path, digest: str) -> Iterator[dict[str, Any]]:
    """Every correction appended against one receipt, in order."""
    for record in read_receipts(path):
        correction = record.get("correction")
        if isinstance(correction, Mapping) and correction.get("corrects_digest") == digest:
            yield record
