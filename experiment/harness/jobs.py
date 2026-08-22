"""Walking a Harbor jobs directory.

Harbor writes one directory per job and one subdirectory per trial:

.. code-block:: text

    jobs/job-name/
    ├── config.json
    ├── result.json          <- the JOB result
    └── trial-name/
        ├── config.json
        ├── result.json      <- the TRIAL result, which is what we want
        ├── agent/           <- trajectory.json, recording.cast
        └── verifier/        <- ctrf.json, reward.txt, test-stdout.txt

The trap is on line four. A job directory carries its own ``result.json``
beside the trials', so the obvious ``rglob("result.json")`` picks it up and the
run silently gains a phantom trial. It would be caught downstream -- the job
result has no ``task_checksum``, so ``ingest_trial`` would refuse it -- but the
failure would arrive as a confusing ingestion error rather than as what it is.

So trials are identified by content, not by depth: a trial result names a task.
That also means this works whether it is pointed at one job directory or at a
whole ``jobs/`` root holding many.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
import json

from .blobs import BlobStore

__all__ = [
    "JobsError",
    "TrialArtifacts",
    "find_trials",
    "ordered_trials",
    "store_artifacts",
]


class JobsError(ValueError):
    """A jobs directory that cannot be read honestly."""


@dataclass(frozen=True)
class TrialArtifacts:
    """Where one trial's bytes live, and what they hash to once stored."""

    trial_dir: Path
    trajectory_digest: str | None
    verifier_output_digest: str | None
    artifact_digests: tuple[str, ...]


def _is_trial_result(document: Any) -> bool:
    # A trial result names a task; a job result does not.
    return isinstance(document, dict) and "task_name" in document


def find_trials(root: str | Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Yield ``(trial_dir, trial_result)`` for every trial under ``root``.

    Sorted by path, so two walks of the same directory agree. **That is
    discovery order, not run order**, and the two are different: Harbor names
    trial directories after the task, so the filesystem sorts them
    alphabetically while the study ran them interleaved. Appending in this
    order is refused by ``append_receipt``, which requires the recorded
    sequence to be the order trials actually ran in.

    Use :func:`ordered_trials` to ingest. This function is for inspection.
    """
    base = Path(root)
    if not base.is_dir():
        raise JobsError(f"{root} is not a directory")
    for path in sorted(base.rglob("result.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise JobsError(f"{path} could not be read: {exc}") from exc
        if _is_trial_result(document):
            yield path.parent, document


def store_artifacts(
    trial_dir: str | Path, store: BlobStore, *, include_recording: bool = False
) -> TrialArtifacts:
    """Put one trial's trajectory and verifier output into the blob store.

    The agent directory goes in whole rather than just ``trajectory.json``: what
    an agent writes there is agent-specific, and a receipt that addressed only
    the file we happened to know about would claim custody of a fraction of the
    evidence.

    ``recording.cast`` is excluded by default. Terminal recordings are large,
    they are the same information the trajectory already carries, and receipts
    are the hot path for every projection.
    """
    directory = Path(trial_dir)
    agent_dir = directory / "agent"
    verifier_dir = directory / "verifier"

    trajectory = None
    if agent_dir.is_dir():
        if include_recording:
            trajectory = store.put_tree(agent_dir)
        else:
            keep = [p for p in sorted(agent_dir.rglob("*")) if p.is_file()
                    and p.name != "recording.cast"]
            if keep:
                # Archive the filtered set by staging it, so the digest covers
                # exactly what was kept rather than what happened to be there.
                import io
                import tarfile

                buffer = io.BytesIO()
                with tarfile.open(fileobj=buffer, mode="w") as archive:
                    for member in keep:
                        info = tarfile.TarInfo(str(member.relative_to(agent_dir)))
                        data = member.read_bytes()
                        info.size = len(data)
                        info.mtime = 0
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mode = 0o644
                        archive.addfile(info, io.BytesIO(data))
                trajectory = store.put_bytes(buffer.getvalue())

    verifier_output = store.put_tree(verifier_dir) if verifier_dir.is_dir() else None

    extras = tuple(
        store.put_file(path)
        for path in sorted(directory.glob("*"))
        if path.is_file() and path.name not in {"result.json", "config.json"}
    )
    return TrialArtifacts(directory, trajectory, verifier_output, extras)


def ordered_trials(
    root: str | Path, index_of: Mapping[str, int]
) -> list[tuple[int, Path, dict[str, Any]]]:
    """Every trial under ``root``, in the order the study ran them.

    ``index_of`` maps a trial directory name to its ``run_sequence_index``.
    The runner must persist it, because nothing in Harbor's output records
    which scheduled trial a directory was: Harbor names directories after the
    task, and a task appears once per replicate per arm. Without the mapping,
    post-hoc ingestion can only guess at the order, and the order is the sole
    evidence that the arms were interleaved.

    Refuses an unmapped directory rather than skipping it. A trial that ran and
    cannot be placed in the schedule is either a trial the plan did not contain
    or a lost mapping, and both are things to stop for.
    """
    found = []
    unmapped = []
    for trial_dir, result in find_trials(root):
        if trial_dir.name not in index_of:
            unmapped.append(trial_dir.name)
            continue
        found.append((index_of[trial_dir.name], trial_dir, result))
    if unmapped:
        raise JobsError(
            f"{len(unmapped)} trial directory/directories are not in the run "
            f"mapping and cannot be placed in the schedule: {sorted(unmapped)[:3]}"
        )
    duplicates = len(found) - len({index for index, _, _ in found})
    if duplicates:
        raise JobsError(f"{duplicates} trial(s) share a run_sequence_index")
    return sorted(found, key=lambda row: row[0])
