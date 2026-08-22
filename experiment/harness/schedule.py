"""The trial schedule: the order the study runs in, decided once.

The preregistration makes interleaving the defence against drift -- a driver
update, a thermal shift, a Harbor version bump partway through -- and it only
defends if the arms are balanced *over time*, not merely in total. Running all
of H0 then all of H1 balances the totals perfectly and confounds the arm with
everything that changed in between.

So the schedule is round-based rather than a single shuffle. Each round contains
exactly one trial of every (task, arm) pair, shuffled within the round. After
any whole round, every task has the same number of trials in every arm, so
anything that drifts across the run hits both arms equally. A flat shuffle
balances only in expectation and can cluster badly on the one sample that
matters -- this one.

Three properties matter as much as the ordering:

* **Generated once.** ``build_or_load`` returns an existing schedule rather than
  making a new one, because a schedule regenerated on resume is a different
  study continued under the same name.
* **Persisted.** A schedule that lives only in a process's memory cannot be
  checked against the receipts afterwards, so "the arms were interleaved"
  becomes a claim rather than a fact.
* **Resumable.** A killed run continues the existing order from where the
  receipts stop.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import random

__all__ = [
    "ScheduleError",
    "ScheduledTrial",
    "TrialSchedule",
    "build_or_load",
    "build_schedule",
    "load_schedule",
    "remaining",
    "save_schedule",
]

SCHEDULE_VERSION = 1


class ScheduleError(ValueError):
    """A schedule that cannot be trusted to describe the run."""


@dataclass(frozen=True)
class ScheduledTrial:
    """One planned trial. ``index`` becomes the receipt's run_sequence_index."""

    index: int
    task_id: str
    arm: str
    replicate: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "task_id": self.task_id,
            "arm": self.arm,
            "replicate": self.replicate,
        }


@dataclass(frozen=True)
class TrialSchedule:
    experiment_id: str
    seed: int
    tasks: tuple[str, ...]
    arms: tuple[str, ...]
    trials_per_arm: int
    entries: tuple[ScheduledTrial, ...]
    version: int = SCHEDULE_VERSION

    def canonical_bytes(self) -> bytes:
        payload = {
            "schedule_version": self.version,
            "experiment_id": self.experiment_id,
            "seed": self.seed,
            "tasks": list(self.tasks),
            "arms": list(self.arms),
            "trials_per_arm": self.trials_per_arm,
            "entries": [entry.as_dict() for entry in self.entries],
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def __len__(self) -> int:
        return len(self.entries)


def build_schedule(
    *,
    experiment_id: str,
    tasks: Sequence[str],
    trials_per_arm: int,
    seed: int,
    arms: Sequence[str] = ("h0", "h1"),
) -> TrialSchedule:
    """One round per replicate; every (task, arm) pair shuffled within it."""
    if not tasks:
        raise ScheduleError("a schedule needs at least one task")
    if len(set(tasks)) != len(tasks):
        raise ScheduleError("duplicate task ids in the committed set")
    if trials_per_arm < 1:
        raise ScheduleError(f"trials_per_arm must be at least 1, got {trials_per_arm}")
    if len(set(arms)) != len(arms) or not arms:
        raise ScheduleError(f"arms must be distinct and non-empty, got {arms!r}")

    rng = random.Random(seed)
    entries: list[ScheduledTrial] = []
    index = 0
    for replicate in range(trials_per_arm):
        round_entries = [(task, arm) for task in tasks for arm in arms]
        rng.shuffle(round_entries)
        for task, arm in round_entries:
            entries.append(ScheduledTrial(index, task, arm, replicate))
            index += 1

    return TrialSchedule(
        experiment_id=experiment_id,
        seed=seed,
        tasks=tuple(tasks),
        arms=tuple(arms),
        trials_per_arm=trials_per_arm,
        entries=tuple(entries),
    )


def save_schedule(path: str | Path, schedule: TrialSchedule) -> str:
    """Write the schedule once. Refuses to overwrite an existing one."""
    target = Path(path)
    if target.exists():
        raise ScheduleError(
            f"{path} already exists; a regenerated schedule is a different study "
            "continued under the same name"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    document = json.loads(schedule.canonical_bytes())
    document["schedule_digest"] = schedule.digest
    target.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return schedule.digest


def load_schedule(path: str | Path) -> TrialSchedule:
    """Read a schedule and check it still hashes to its recorded digest."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScheduleError(f"{path} is not valid JSON: {exc}") from exc
    try:
        schedule = TrialSchedule(
            experiment_id=document["experiment_id"],
            seed=int(document["seed"]),
            tasks=tuple(document["tasks"]),
            arms=tuple(document["arms"]),
            trials_per_arm=int(document["trials_per_arm"]),
            entries=tuple(
                ScheduledTrial(
                    int(entry["index"]),
                    str(entry["task_id"]),
                    str(entry["arm"]),
                    int(entry["replicate"]),
                )
                for entry in document["entries"]
            ),
            version=int(document["schedule_version"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ScheduleError(f"{path} is not a schedule: {exc}") from exc
    recorded = document.get("schedule_digest")
    if recorded and recorded != schedule.digest:
        raise ScheduleError(
            f"{path} has been edited since it was written: it records "
            f"{recorded} but hashes to {schedule.digest}"
        )
    return schedule


def build_or_load(
    path: str | Path,
    *,
    experiment_id: str,
    tasks: Sequence[str],
    trials_per_arm: int,
    seed: int,
    arms: Sequence[str] = ("h0", "h1"),
) -> TrialSchedule:
    """The only entry point a runner should use.

    On a fresh run it builds and persists. On a resumed run it returns what is
    already on disk, and refuses if the caller's parameters have drifted from
    it -- a resume under different parameters is a new study, and continuing it
    silently would put two studies in one receipt log.
    """
    target = Path(path)
    if not target.exists():
        schedule = build_schedule(
            experiment_id=experiment_id,
            tasks=tasks,
            trials_per_arm=trials_per_arm,
            seed=seed,
            arms=arms,
        )
        save_schedule(target, schedule)
        return schedule

    existing = load_schedule(target)
    drift = []
    if existing.experiment_id != experiment_id:
        drift.append(f"experiment_id {existing.experiment_id!r} != {experiment_id!r}")
    if existing.seed != seed:
        drift.append(f"seed {existing.seed} != {seed}")
    if existing.tasks != tuple(tasks):
        drift.append("committed task set differs")
    if existing.trials_per_arm != trials_per_arm:
        drift.append(f"trials_per_arm {existing.trials_per_arm} != {trials_per_arm}")
    if existing.arms != tuple(arms):
        drift.append(f"arms {existing.arms} != {tuple(arms)}")
    if drift:
        raise ScheduleError(
            "the schedule on disk does not match the parameters given: "
            + "; ".join(drift)
            + ". Resuming under different parameters would put two studies in "
            "one receipt log"
        )
    return existing


def remaining(
    schedule: TrialSchedule, receipts: Iterable[Mapping[str, Any]]
) -> tuple[ScheduledTrial, ...]:
    """The entries not yet recorded, in schedule order.

    Matched on ``run_sequence_index`` rather than on (task, arm), because two
    entries in the same round are otherwise indistinguishable and a resume
    would re-run the wrong one.
    """
    done = set()
    for receipt in receipts:
        if "correction" in receipt:
            continue
        section = receipt.get("experiment")
        if not isinstance(section, Mapping):
            continue
        if section.get("experiment_id") != schedule.experiment_id:
            continue
        index = section.get("run_sequence_index")
        if isinstance(index, int):
            done.add(index)
    return tuple(entry for entry in schedule.entries if entry.index not in done)
