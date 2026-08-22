"""Evidence-layer primitives for the benchmark experiment.

Deliberately outside ``runtime/``: nothing here is part of the How Do
discipline, and ``experiment/`` is not in the install payload.
"""

from .resolution import (
    RESOLUTION_VERSION,
    Resolution,
    ResolutionOperand,
    resolution_fields,
    verify_resolution,
)

__all__ = [
    "RESOLUTION_VERSION",
    "Resolution",
    "ResolutionOperand",
    "resolution_fields",
    "verify_resolution",
]
