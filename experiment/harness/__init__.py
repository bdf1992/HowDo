"""The seam between Harbor and the evidence layer.

Harbor already owns execution: containers, agents, verifiers, retries, the task
registry. Rebuilding any of that would be a second runner to keep correct, and
the roadmap says so explicitly. This package reads what Harbor wrote and turns
it into receipts, and stores trajectories where a digest can find them.
"""

from .blobs import BlobError, BlobStore
from .qualify import (
    QualificationCounts,
    count_runs,
    qualify_task,
)
from .ingest import IngestError, ingest_trial, read_trial_result, wall_clock_seconds

__all__ = [
    "BlobError",
    "BlobStore",
    "IngestError",
    "QualificationCounts",
    "count_runs",
    "ingest_trial",
    "qualify_task",
    "read_trial_result",
    "wall_clock_seconds",
]
