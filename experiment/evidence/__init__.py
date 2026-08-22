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
from .resolution import (
    RESOLUTION_VERSION,
    Resolution,
    ResolutionOperand,
    resolution_fields,
    verify_resolution,
)

__all__ = [
    "ORGANISM_VERSION",
    "OrganismError",
    "OrganismLock",
    "RESOLUTION_VERSION",
    "Resolution",
    "ResolutionOperand",
    "load_organism",
    "organism_fields",
    "resolution_fields",
    "verify_organism",
    "verify_resolution",
]
