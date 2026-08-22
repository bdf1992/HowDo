"""What can be learned about a person from what was observed of their work.

This module exists to answer one question honestly: do recorded signals carry
what onboarding actually needs? It is written as the *consumer* deliberately,
because a producer with no consumer records whatever was easy rather than
whatever was wanted, and nothing catches the difference.

Onboarding establishes four things, and it is explicit about what turns a guess
into evidence: a preference someone states is a hypothesis; predicting from it
and watching whether the prediction held is what makes it evident. So an
observation here is only worth the name when it names a prediction and its
outcome. Anything else is a usage count wearing the word.

Two grades of evidence, and the difference is the whole point:

- **Observed.** Something happened on disk that the model did not author the
  verdict on -- a file rewritten after it was checked, work abandoned before it
  ran. This is admissible.
- **Declared.** The model said the prediction held. This is a hypothesis about
  a hypothesis, and the discipline refuses model output as independent evidence
  of its own success, so it is recorded and never counted.

The gap report is as much the product as the observations. A reading nobody can
support should be visible as unsupported, not absent.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .signal import read


# The four things onboarding establishes, and the loop stage each one tunes.
ANCHOR = "anchor"
BUILD_DIRECTION = "build_direction"
UNDERSTOOD = "understood"
CORRECTION = "correction"

DIMENSIONS = {
    ANCHOR: "a domain known well enough to judge an explanation — tunes Map",
    BUILD_DIRECTION: "instance-first or principle-first — tunes Path",
    UNDERSTOOD: "what convinces this person they have it — tunes Check and Look",
    CORRECTION: "how a correction should land — tunes Update",
}

OBSERVED = "observed"
DECLARED = "declared"


@dataclass(frozen=True)
class Observation:
    """One reading, with what supports it and how strongly."""

    dimension: str
    reading: str
    basis: str
    support: int
    grade: str = OBSERVED

    def admissible(self) -> bool:
        """Declared readings are hypotheses, not evidence.

        Kept rather than dropped so that the difference between "nothing
        happened" and "the model asserted something nobody checked" stays
        visible to whoever reads this.
        """
        return self.grade == OBSERVED


@dataclass(frozen=True)
class Gap:
    """A dimension the record cannot speak to, and what it would take."""

    dimension: str
    why: str
    needs: str


@dataclass(frozen=True)
class Reading:
    observations: tuple[Observation, ...] = ()
    gaps: tuple[Gap, ...] = ()

    def admissible(self) -> tuple[Observation, ...]:
        return tuple(o for o in self.observations if o.admissible())


def _sessions(records: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("session", ""))].append(record)
    return grouped


# The loop is ordered, and that order is what tells a residual from progress.
# Map, Path, Check, Do, Look, Update: moving forward through it is the
# discipline working. Moving *backwards* -- returning to Do after a Look, or
# restating a Check that was already looked at -- is the earlier stage having
# failed to hold.
_ORDER = {"map": 0, "path": 1, "check": 2, "do": 3, "look": 4, "update": 5}


def _regressions(records: Sequence[dict[str, Any]]) -> list[str]:
    """Artefacts the work returned to an earlier stage on.

    This replaces a cruder reading -- "written again after Look" -- which was
    wrong in the most ordinary case there is. `Look` is followed by `Update` in
    every complete pass of the loop, so counting any later write as a failure
    scored the discipline working correctly as the check having failed.

    Going backwards is different. Nothing in the loop sends you from Look to Do
    except the Do not having satisfied the Check, and that is observed from the
    sequence rather than reported by anyone.
    """
    furthest: dict[str, int] = {}
    regressed: list[str] = []
    for record in records:
        path = str(record.get("path", ""))
        stage = _ORDER.get(str(record.get("stage", "")))
        if stage is None:
            continue
        if path in furthest and stage < furthest[path]:
            regressed.append(path)
            furthest[path] = stage
        else:
            furthest[path] = max(stage, furthest.get(path, stage))
    return regressed


def _abandoned(records: Sequence[dict[str, Any]]) -> int:
    """Sessions that mapped or pathed but never reached Do."""
    stages = {record.get("stage") for record in records}
    return 1 if stages & {"map", "path"} and "do" not in stages else 0


def _calibration(sessions: dict[str, list[dict[str, Any]]]) -> tuple[int, int]:
    """How often the model said a check held, and how often the loop disagreed.

    Disagreement means the work went *back* afterwards, not merely that the
    artefact was touched again. Settling an Update after a Look is the pass
    completing, and counting it as a contradiction made a well-run loop look
    like a failed one.
    """
    claimed = contradicted = 0
    for group in sessions.values():
        regressed = set(_regressions(group))
        for record in group:
            if record.get("stage") == "look" and record.get("held") is True:
                claimed += 1
                if str(record.get("path", "")) in regressed:
                    contradicted += 1
    return claimed, contradicted


def _shapes(records: Sequence[dict[str, Any]]) -> list[tuple[str, int, int]]:
    """Per declared shape: how many artefacts landed, out of how many used it.

    Counted by artefact rather than by signal. Drafting a document saves it
    several times, and counting saves turned one explanation into three -- which
    inflated every support number the report showed, in the direction that makes
    thin evidence look sturdy.
    """
    by_shape: dict[str, dict[str, bool]] = defaultdict(dict)
    grouped = _sessions(records)
    regressed = {p for group in grouped.values() for p in _regressions(group)}
    for record in records:
        shape = str(record.get("shape", ""))
        path = str(record.get("path", ""))
        if not shape or not path:
            continue
        by_shape[shape][path] = path not in regressed
    return [
        (shape, sum(paths.values()), len(paths))
        for shape, paths in sorted(by_shape.items())
    ]


def observe(log: str | Path) -> Reading:
    """Read the record and say what it does and does not support.

    The gaps are computed from the shape of the records rather than hardcoded,
    so that extending what a signal carries closes them automatically instead
    of requiring this list to be maintained alongside.
    """
    records = list(read(log))
    observations: list[Observation] = []

    sessions = _sessions(records)
    regressed = {p for group in sessions.values() for p in _regressions(group)}
    if regressed:
        observations.append(Observation(
            dimension=UNDERSTOOD,
            reading="work has returned to an earlier stage rather than settling",
            basis=f"{len(regressed)} artefact(s) went back down the loop after reaching a later stage",
            support=len(regressed),
            grade=OBSERVED,
        ))

    # The model's verdict, held against what the disk did. This is the only
    # place a declared value earns its keep: on its own it is self-report, but
    # compared with an observed rewrite it makes the model's confidence itself
    # something that can be wrong in a countable way.
    claimed, contradicted = _calibration(sessions)
    if claimed:
        observations.append(Observation(
            dimension=UNDERSTOOD,
            reading=(
                f"{contradicted} of {claimed} checks the model called satisfied "
                f"were followed by the work going back down the loop"
                if contradicted else
                f"all {claimed} checks the model called satisfied survived"
            ),
            basis="declared outcome compared against what happened on disk",
            support=claimed,
            grade=OBSERVED,
        ))

    for shape, landed, total in _shapes(records):
        observations.append(Observation(
            dimension=BUILD_DIRECTION,
            reading=f"{shape} held in {landed} of {total} explanations that used it",
            basis="declared shape, scored by whether the artefact needed the loop re-entered",
            support=total,
            grade=OBSERVED if total > 1 else DECLARED,
        ))

    known = {str(r.get("domain")) for r in records if r.get("domain")}
    if known:
        observations.append(Observation(
            dimension=ANCHOR,
            reading=f"work declared in: {', '.join(sorted(known))}",
            basis="declared by the operation; whether these are domains they can "
                  "judge an explanation in is not observable here",
            support=len(known),
            grade=DECLARED,
        ))

    abandoned = sum(_abandoned(group) for group in sessions.values())
    if abandoned:
        observations.append(Observation(
            dimension=BUILD_DIRECTION,
            reading="work is mapped more often than it is executed",
            basis=f"{abandoned} session(s) reached Map or Path but never Do",
            support=abandoned,
            grade=OBSERVED,
        ))

    return Reading(observations=tuple(observations), gaps=tuple(gaps(records)))


def gaps(records: Sequence[dict[str, Any]]) -> list[Gap]:
    """What the record cannot answer, and the datum each answer would need.

    Derived from the fields actually present, so this stops reporting a gap the
    moment signals start carrying what closes it. That is the point of writing
    the consumer first: the requirement is stated here, in the thing that wants
    it, rather than guessed at by the producer.
    """
    present: set[str] = set()
    for record in records:
        present.update(record)

    found: list[Gap] = []

    if "expects" not in present:
        found.append(Gap(
            dimension=UNDERSTOOD,
            why=(
                "no signal carries what a Check committed to, so nothing can be "
                "tested against what actually happened"
            ),
            needs="a prediction recorded at Check, and its outcome recorded at Look",
        ))

    if "held" not in present:
        found.append(Gap(
            dimension=CORRECTION,
            why=(
                "whether a reading survived contact is never recorded, so a "
                "correction cannot be told from a continuation"
            ),
            needs="the outcome of a Look, and what it indicted",
        ))

    if "domain" not in present:
        found.append(Gap(
            dimension=ANCHOR,
            why=(
                "a file path is where work happened, not a domain the person "
                "can judge an explanation in -- and the anchor's whole value is "
                "that they can check the work"
            ),
            needs="the domain an operation belonged to, and whether it is one they know",
        ))

    if "shape" not in present:
        found.append(Gap(
            dimension=BUILD_DIRECTION,
            why=(
                "stage order describes how the agent proceeded, not whether the "
                "case or the rule came first for the reader"
            ),
            needs="whether an explanation went instance-first or principle-first, and whether it landed",
        ))

    return found
