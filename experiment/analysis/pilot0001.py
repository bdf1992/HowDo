"""PILOT-0001: the preregistered analysis, written before the data.

Zero dependencies, seeded throughout, and deliberately assumption-light. The
design is paired -- the same tasks appear in both arms -- so the test permutes
arm labels *within* each task, which is exactly the exchangeability the null
asserts and requires nothing about the distribution of pass rates.

Two choices here are the analysis rather than implementation detail:

* **The task is the unit, not the trial.** Trials within a task are not
  independent: a task the organism cannot do fails every time, and pooling
  trials would count that as many separate pieces of evidence. Both the
  statistic and the bootstrap resample tasks.
* **The decision is computed, not read off a plot.** ``decide()`` implements the
  preregistered rule literally, so GO, STOP, and INCONCLUSIVE come out of the
  numbers rather than out of a discussion about the numbers.

``synthetic_trials()`` exists so this module can be shown to recover a known
effect before it is ever pointed at real receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
import random

__all__ = [
    "Outcome",
    "PilotAnalysis",
    "analyse",
    "decide",
    "per_task_rates",
    "synthetic_trials",
]

# Trials that did not measure the treatment. Per the preregistration these are
# excluded and re-run; they never enter the estimate.
_NOT_MEASURED = ("error", "excluded")

Outcome = str  # "GO" | "STOP" | "INCONCLUSIVE"


@dataclass(frozen=True)
class PilotAnalysis:
    """Everything the gate needs, and nothing it has to interpret."""

    tasks: tuple[str, ...]
    differences: tuple[float, ...]
    effect: float
    ci_low: float
    ci_high: float
    p_value: float
    wins: int
    losses: int
    ties: int
    excluded_rate_h0: float
    excluded_rate_h1: float
    permutations: int
    resamples: int
    seed: int

    def harm_rate(self, delta_star: float) -> float:
        """Fraction of tasks that got *meaningfully* worse.

        Thresholded at -δ* rather than at zero. Under a true null roughly half
        of all tasks regress by chance, so a harm rate counting any negative
        difference is near 0.5 whatever the treatment does -- it would fire on a
        genuine positive as readily as on nothing. Counting only regressions as
        large as the effect we would have acted on keeps the ceiling a statement
        about damage rather than about sample size.
        """
        return sum(1 for value in self.differences if value <= -delta_star) / len(
            self.differences
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tasks": list(self.tasks),
            "differences": list(self.differences),
            "effect": self.effect,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_value": self.p_value,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "excluded_rate_h0": self.excluded_rate_h0,
            "excluded_rate_h1": self.excluded_rate_h1,
            "permutations": self.permutations,
            "resamples": self.resamples,
            "seed": self.seed,
        }


def _trials(receipts: Iterable[Mapping]) -> list[tuple[str, str, int | None]]:
    """(task_id, arm, measured outcome) for every confirmatory trial.

    ``None`` marks a trial that did not measure the treatment, so the exclusion
    rate can be checked against its ceiling from the same pass over the log.
    """
    rows = []
    for receipt in receipts:
        if "correction" in receipt:
            continue
        if receipt.get("experiment", {}).get("analysis_class") != "confirmatory":
            continue
        result = receipt["outcome"]["result"]
        rows.append(
            (
                receipt["benchmark"]["task_id"],
                receipt["treatment"]["arm"],
                None if result in _NOT_MEASURED else int(result == "pass"),
            )
        )
    return rows


def per_task_rates(
    rows: Sequence[tuple[str, str, int | None]]
) -> dict[str, dict[str, float]]:
    """Pass rate per task per arm, over trials that measured the treatment."""
    totals: dict[str, dict[str, list[int]]] = {}
    for task, arm, measured in rows:
        if measured is None:
            continue
        totals.setdefault(task, {}).setdefault(arm, []).append(measured)
    return {
        task: {arm: sum(values) / len(values) for arm, values in arms.items()}
        for task, arms in totals.items()
    }


def _effect(rates: Mapping[str, Mapping[str, float]], tasks: Sequence[str]) -> float:
    return sum(rates[task]["h1"] - rates[task]["h0"] for task in tasks) / len(tasks)


def _permute(
    rows: Sequence[tuple[str, str, int | None]], rng: random.Random
) -> list[tuple[str, str, int | None]]:
    """Shuffle arm labels within each task, leaving the outcomes where they are."""
    by_task: dict[str, list[int]] = {}
    for index, (task, _, _) in enumerate(rows):
        by_task.setdefault(task, []).append(index)
    permuted = list(rows)
    for indices in by_task.values():
        labels = [rows[index][1] for index in indices]
        rng.shuffle(labels)
        for index, label in zip(indices, labels):
            task, _, measured = rows[index]
            permuted[index] = (task, label, measured)
    return permuted


def analyse(
    receipts: Iterable[Mapping],
    *,
    seed: int,
    permutations: int = 10_000,
    resamples: int = 10_000,
) -> PilotAnalysis:
    """The primary endpoint, its interval, and the secondary counts."""
    rows = _trials(receipts)
    if not rows:
        raise ValueError("no confirmatory trials in the log")

    rates = per_task_rates(rows)
    tasks = tuple(sorted(task for task, arms in rates.items() if {"h0", "h1"} <= set(arms)))
    if not tasks:
        raise ValueError("no task has measured trials in both arms")

    observed = _effect(rates, tasks)

    rng = random.Random(seed)
    at_least_as_extreme = 0
    for _ in range(permutations):
        shuffled = per_task_rates(_permute(rows, rng))
        usable = [task for task in tasks if {"h0", "h1"} <= set(shuffled[task])]
        if not usable:
            continue
        if abs(_effect(shuffled, usable)) >= abs(observed):
            at_least_as_extreme += 1
    # The +1s keep the p-value from ever being exactly zero: 10,000 permutations
    # cannot license a claim stronger than 1/10,001.
    p_value = (at_least_as_extreme + 1) / (permutations + 1)

    boot = random.Random(seed + 1)
    differences = [rates[task]["h1"] - rates[task]["h0"] for task in tasks]
    draws = []
    for _ in range(resamples):
        sample = [boot.choice(differences) for _ in differences]
        draws.append(sum(sample) / len(sample))
    draws.sort()
    ci_low = draws[int(0.025 * (resamples - 1))]
    ci_high = draws[int(0.975 * (resamples - 1))]

    wins = sum(1 for value in differences if value > 0)
    losses = sum(1 for value in differences if value < 0)
    ties = sum(1 for value in differences if value == 0)

    per_arm: dict[str, list[int | None]] = {"h0": [], "h1": []}
    for _, arm, measured in rows:
        if arm in per_arm:
            per_arm[arm].append(measured)
    excluded = {
        arm: (sum(1 for value in values if value is None) / len(values)) if values else 0.0
        for arm, values in per_arm.items()
    }

    return PilotAnalysis(
        tasks=tasks,
        differences=tuple(differences),
        effect=observed,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        wins=wins,
        losses=losses,
        ties=ties,
        excluded_rate_h0=excluded["h0"],
        excluded_rate_h1=excluded["h1"],
        permutations=permutations,
        resamples=resamples,
        seed=seed,
    )


def decide(
    analysis: PilotAnalysis,
    *,
    delta_star: float,
    harm_ceiling: float,
    exclusion_ceiling: float = 0.10,
) -> tuple[Outcome, str]:
    """Apply the preregistered stopping rule. Returns the outcome and why.

    The order matters: a run whose exclusion rate is over the ceiling has a
    selected sample, and no reading of its interval is worth making.

    **Harm does not gate.** It was drafted as one, and running this module
    against synthetic nulls before any real data existed showed why it cannot
    be. With trials-per-arm in the single digits, one trial is worth more than
    δ\* of a per-task pass rate, so under a true null 30-40% of tasks "regress
    by at least δ\*" purely by chance. A ceiling at 20% would then fire on
    nothing at all — and, worse, would fire on a genuine positive too, since
    real effects are not uniform across tasks. Distinguishing real harm from
    that noise needs a per-task sample the pilot does not have.

    So harm is computed, reported with the other secondary endpoints, and
    flagged in the reason string when it exceeds the advisory ceiling. It is
    something for a person to look at before M1, not a rule that decides.
    Protection against a treatment that lifts the mean while breaking tasks
    comes instead from GO requiring the interval's *lower* bound to clear
    δ\*: broad damage widens the interval and drops that bound.
    """
    if max(analysis.excluded_rate_h0, analysis.excluded_rate_h1) > exclusion_ceiling:
        return (
            "INCONCLUSIVE",
            f"exclusion rate exceeds {exclusion_ceiling:.0%}; the remaining sample "
            "is a selected one and the run is void",
        )
    interval = f"[{analysis.ci_low:.3f}, {analysis.ci_high:.3f}]"
    if analysis.ci_low >= delta_star:
        outcome, reason = "GO", f"the interval {interval} lies at or above δ* = {delta_star}"
    elif analysis.ci_high < delta_star:
        outcome, reason = (
            "STOP",
            f"the interval {interval} lies wholly below δ* = {delta_star}; the effect "
            "is absent or too small to act on",
        )
    else:
        outcome, reason = (
            "INCONCLUSIVE",
            f"the interval {interval} spans δ* = {delta_star}; this run cannot tell a "
            "worthwhile effect from none",
        )

    # Harm is reported, not decisive. See the note on ``harm_ceiling`` below.
    harm_rate = analysis.harm_rate(delta_star)
    if harm_rate > harm_ceiling:
        reason += (
            f". Flag: {harm_rate:.0%} of tasks regressed by at least δ*, over the "
            f"{harm_ceiling:.0%} advisory ceiling — investigate before M1, and do not "
            "read this as a gate (see the docstring)"
        )
    return outcome, reason


def synthetic_trials(
    *,
    tasks: int,
    trials_per_arm: int,
    h0_rate: float,
    lift: float,
    seed: int,
) -> list[dict]:
    """Receipt-shaped records with a known effect, for validating this module.

    Not a fixture for convenience: the preregistration requires the analysis to
    be shown recovering an effect it was told about before it is pointed at an
    effect it was not.
    """
    rng = random.Random(seed)
    records = []
    index = 0
    for task in range(tasks):
        task_id = f"synthetic-{task:03d}"
        for arm, rate in (("h0", h0_rate), ("h1", min(1.0, h0_rate + lift))):
            for _ in range(trials_per_arm):
                records.append(
                    {
                        "experiment": {
                            "analysis_class": "confirmatory",
                            "run_sequence_index": index,
                        },
                        "benchmark": {"task_id": task_id},
                        "treatment": {"arm": arm},
                        "outcome": {"result": "pass" if rng.random() < rate else "fail"},
                    }
                )
                index += 1
    return records
