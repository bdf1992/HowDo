"""The seam between Harbor and the evidence layer.

Harbor already owns execution: containers, agents, verifiers, retries, the task
registry. Rebuilding any of that would be a second runner to keep correct, and
the roadmap says so explicitly. This package reads what Harbor wrote and turns
it into receipts, and stores trajectories where a digest can find them.
"""

from .blobs import BlobError, BlobStore
from .checks import Finding, RunReport, check_run
from .jobs import (
    JobsError,
    TrialArtifacts,
    find_trials,
    ordered_trials,
    store_artifacts,
)
from .schedule import (
    ScheduleError,
    ScheduledTrial,
    TrialSchedule,
    build_or_load,
    build_schedule,
    load_schedule,
    remaining,
    save_schedule,
)
from .qualify import (
    QualificationCounts,
    count_runs,
    qualify_task,
)
from .ingest import IngestError, ingest_trial, read_trial_result, wall_clock_seconds

__all__ = [
    "BlobError",
    "BlobStore",
    "Finding",
    "RunReport",
    "ScheduleError",
    "ScheduledTrial",
    "TrialSchedule",
    "IngestError",
    "JobsError",
    "TrialArtifacts",
    "QualificationCounts",
    "build_or_load",
    "build_schedule",
    "check_run",
    "count_runs",
    "find_trials",
    "load_schedule",
    "ordered_trials",
    "remaining",
    "save_schedule",
    "store_artifacts",
    "ingest_trial",
    "qualify_task",
    "read_trial_result",
    "wall_clock_seconds",
]
