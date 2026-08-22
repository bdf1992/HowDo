"""Evidence-layer primitives for the benchmark experiment.

Deliberately outside ``runtime/``: nothing here is part of the How Do
discipline, and ``experiment/`` is not in the install payload.
"""

from .organism import (
    ORGANISM_VERSION,
    OrganismError,
    OrganismLock,
    load_organism,
    organism_fields,
    verify_organism,
)
from .qualification import (
    MAX_INFRASTRUCTURE_ERROR_RATE,
    NOOP_ATTEMPTS,
    ORACLE_ATTEMPTS,
    OUTCOMES,
    Qualification,
    QualificationError,
    qualification_fields,
    verify_qualification,
)
from .receipt import (
    ANALYSIS_CLASSES,
    ARMS,
    FAILURE_CLASSES,
    RECEIPT_VERSION,
    RECON_OUTCOMES,
    RESULTS,
    VERIFIER_KINDS,
    ReceiptError,
    append_receipt,
    build_receipt,
    correct_receipt,
    corrections_for,
    read_receipts,
    verify_receipt,
)
from .resolution import (
    RESOLUTION_VERSION,
    Resolution,
    ResolutionOperand,
    resolution_fields,
    verify_resolution,
)

__all__ = [
    "ANALYSIS_CLASSES",
    "ARMS",
    "FAILURE_CLASSES",
    "MAX_INFRASTRUCTURE_ERROR_RATE",
    "NOOP_ATTEMPTS",
    "ORACLE_ATTEMPTS",
    "ORGANISM_VERSION",
    "OUTCOMES",
    "OrganismError",
    "Qualification",
    "QualificationError",
    "OrganismLock",
    "RECEIPT_VERSION",
    "RECON_OUTCOMES",
    "RESOLUTION_VERSION",
    "RESULTS",
    "ReceiptError",
    "VERIFIER_KINDS",
    "Resolution",
    "ResolutionOperand",
    "append_receipt",
    "build_receipt",
    "correct_receipt",
    "corrections_for",
    "load_organism",
    "organism_fields",
    "qualification_fields",
    "read_receipts",
    "resolution_fields",
    "verify_receipt",
    "verify_organism",
    "verify_qualification",
    "verify_resolution",
]
