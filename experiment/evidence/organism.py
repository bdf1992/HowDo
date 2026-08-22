"""The organism fingerprint: which machine produced a trial.

Every later comparison is a difference between two arms. If the execution
configuration moved between them -- a different quantization, a raised context
cap, a driver update, one more layer offloaded to CPU -- the difference is
partly the machine, and no analysis performed afterwards can separate the two.

So M-1 freezes one configuration into ``ORGANISM.lock.json`` and every receipt
carries its digest. Receipts under different fingerprints are not pooled. That
rule is only enforceable if the fingerprint is computed from the configuration
rather than asserted alongside it, which is what this module does.

What the digest covers is deliberately narrow: identity, configuration, and
hardware. The observed envelope -- peak memory, throughput, the failures seen
during the probe -- is recorded in the lock file but excluded from the hash,
because it is an observation *about* the organism and varies between repeats of
the same organism. Including it would give the same machine a different
fingerprint on every probe.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json

__all__ = [
    "ORGANISM_VERSION",
    "OrganismError",
    "OrganismLock",
    "load_organism",
    "organism_fields",
    "verify_organism",
]

# Same reason as ``RESOLUTION_VERSION``: canonicalization rules change, and a
# historical digest computed under different rules is uninterpretable rather
# than merely different.
ORGANISM_VERSION = 1

# Hashed. Everything that decides what the machine *is*.
_HASHED_SECTIONS = ("identity", "configuration", "hardware")

_REQUIRED = {
    "identity": (
        "model_file",
        "model_sha256",
        "model_parameters",
        "quantization",
        "runtime_name",
        "runtime_version",
        "runtime_commit",
        "runtime_build_flags",
        "harbor_version",
        "harness_config_digest",
    ),
    "configuration": (
        "context_cap",
        "gpu_layers",
        "offload_split",
        "batch_size",
        "concurrency",
        "sampling",
    ),
    "hardware": (
        "gpu_model",
        "gpu_vram_total",
        "cpu_model",
        "system_ram_total",
        "os",
        "kernel",
        "driver_version",
    ),
}

_REQUIRED_SAMPLING = ("temperature", "top_p", "top_k", "seed", "repeat_penalty", "greedy")

# A lock file full of template text hashes to something that looks exactly like
# a real fingerprint. Refusing the placeholders is the only thing standing
# between "we recorded the organism" and "we recorded the form we meant to fill
# in".
_PLACEHOLDERS = frozenset(
    {"", "tbd", "todo", "pending", "none", "unknown", "n/a", "na", "fill", "xxx", "?"}
)
_PLACEHOLDER_PREFIXES = ("<", "fill ", "todo", "your ", "example")


class OrganismError(ValueError):
    """A lock file that cannot honestly identify an organism."""


def _check_value(where: str, value: Any) -> None:
    if value is None:
        raise OrganismError(f"{where} is null; every field must be filled")
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in _PLACEHOLDERS or cleaned.startswith(_PLACEHOLDER_PREFIXES):
            raise OrganismError(
                f"{where} is still a placeholder ({value!r}); a fingerprint over "
                "placeholders certifies nothing while looking like one that does"
            )


def _check_section(name: str, section: Any) -> Mapping[str, Any]:
    if not isinstance(section, Mapping):
        raise OrganismError(f"{name} must be an object, got {type(section).__name__}")
    missing = [key for key in _REQUIRED[name] if key not in section]
    if missing:
        raise OrganismError(f"{name} is missing required fields: {', '.join(sorted(missing))}")
    for key in _REQUIRED[name]:
        _check_value(f"{name}.{key}", section[key])
    return section


def _check_sampling(configuration: Mapping[str, Any]) -> None:
    sampling = configuration["sampling"]
    if not isinstance(sampling, Mapping):
        raise OrganismError(
            f"configuration.sampling must be an object, got {type(sampling).__name__}"
        )
    missing = [key for key in _REQUIRED_SAMPLING if key not in sampling]
    if missing:
        raise OrganismError(
            f"configuration.sampling is missing required fields: {', '.join(sorted(missing))}"
        )
    for key in _REQUIRED_SAMPLING:
        _check_value(f"configuration.sampling.{key}", sampling[key])


@dataclass(frozen=True)
class OrganismLock:
    """One frozen execution configuration.

    Constructed from a parsed lock file rather than from keyword arguments,
    because the file is the artifact M-1 produces and the thing a later reader
    audits. A constructor that accepted fields directly would let code emit a
    fingerprint for a configuration no file records.
    """

    document: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.document, Mapping):
            raise OrganismError(
                f"a lock file must be an object, got {type(self.document).__name__}"
            )
        version = self.document.get("organism_version")
        # ``bool`` is an ``int`` in Python, and ``true`` serializes to something
        # that is not a version number.
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise OrganismError(f"organism_version must be a positive int, got {version!r}")
        for name in _HASHED_SECTIONS:
            if name not in self.document:
                raise OrganismError(f"a lock file must carry a {name!r} section")
            _check_section(name, self.document[name])
        _check_sampling(self.document["configuration"])

    @property
    def version(self) -> int:
        return int(self.document["organism_version"])

    def canonical_bytes(self) -> bytes:
        """The exact bytes the fingerprint commits to.

        The observed envelope is not here. See the module docstring: it is an
        observation about the organism, not part of its identity.
        """
        payload: dict[str, Any] = {"organism_version": self.version}
        for name in _HASHED_SECTIONS:
            payload[name] = self.document[name]
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def as_receipt_block(self) -> dict[str, Any]:
        """The immutable block, shaped for the evidence receipt."""
        return {
            "organism_version": self.version,
            "organism_fingerprint": self.fingerprint,
            "organism_model_sha256": self.document["identity"]["model_sha256"],
            "organism_quantization": self.document["identity"]["quantization"],
            "organism_context_cap": self.document["configuration"]["context_cap"],
            "organism_runtime_commit": self.document["identity"]["runtime_commit"],
        }


def load_organism(path: str | Path) -> OrganismLock:
    """Read and validate a lock file. Raises rather than returning a bad lock."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OrganismError(f"{path} is not valid JSON: {exc}") from exc
    return OrganismLock(document)


def organism_fields(path: str | Path) -> dict[str, Any]:
    """Build the receipt block straight from the lock file on disk."""
    return load_organism(path).as_receipt_block()


def verify_organism(block: Mapping[str, Any], lock: OrganismLock) -> bool:
    """Check a stored receipt block still matches the lock it names.

    A reader who has both should not have to trust that the writer computed the
    digest honestly, and should be able to notice a lock file edited after the
    fact.
    """
    try:
        return (
            int(block["organism_version"]) == lock.version
            and str(block["organism_fingerprint"]) == lock.fingerprint
        )
    except (KeyError, TypeError, ValueError):
        return False
