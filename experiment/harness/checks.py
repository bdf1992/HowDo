"""The runbook's post-collection checks, as code rather than as a list.

The runbook says to run these *before* looking at the difference, so that what
they find cannot be influenced by knowing which way it cuts. A checklist a
person walks through under time pressure, on a run that took three weeks, is
exactly the thing that gets walked through quickly. So it is mechanical, it
returns findings rather than a verdict, and it never raises -- a check that
crashes on a malformed log is a check that stops the audit at the first problem
instead of listing all of them.

Nothing here decides GO, STOP, or INCONCLUSIVE. That is the preregistration's
job and ``analysis/pilot0001.py`` implements it. This only answers: *is this log
a faithful record of the study that was planned?* A run that fails these is not
a run with a caveat, it is a run whose numbers mean something other than what
they will be read to mean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from evidence import verify_receipt

from .schedule import TrialSchedule

__all__ = ["Finding", "RunReport", "check_run"]


@dataclass(frozen=True)
class Finding:
    """One thing wrong with the log, and why it matters."""

    check: str
    detail: str
    fatal: bool

    def __str__(self) -> str:  # pragma: no cover - display only
        mark = "FATAL" if self.fatal else "warn "
        return f"[{mark}] {self.check}: {self.detail}"


@dataclass
class RunReport:
    receipts: int = 0
    corrections: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def fatal(self) -> list[Finding]:
        return [f for f in self.findings if f.fatal]

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def analysable(self) -> bool:
        """Whether the primary endpoint may be computed at all.

        Warnings are for a person to read. A fatal finding means the log does
        not describe the planned study, and an estimate from it would be an
        estimate of something nobody specified.
        """
        return not self.fatal

    def __str__(self) -> str:  # pragma: no cover - display only
        head = f"{self.receipts} receipts, {self.corrections} corrections"
        if self.clean:
            return head + " — clean"
        return "\n".join([head] + [str(f) for f in self.findings])


def _add(report: RunReport, check: str, detail: str, *, fatal: bool = True) -> None:
    report.findings.append(Finding(check, detail, fatal))


def check_run(
    receipts: Iterable[Mapping[str, Any]],
    *,
    schedule: TrialSchedule | None = None,
    committed_tasks: Sequence[str] | None = None,
    exclusion_ceiling: float = 0.10,
    expected_analysis_class: str = "confirmatory",
) -> RunReport:
    """Everything the runbook asks for, in one pass. Never raises."""
    report = RunReport()
    records = list(receipts)
    trials = [r for r in records if isinstance(r, Mapping) and "correction" not in r]
    corrections = [r for r in records if isinstance(r, Mapping) and "correction" in r]
    report.receipts = len(trials)
    report.corrections = len(corrections)

    if not trials:
        _add(report, "empty", "the log contains no trial receipts")
        return report

    # 1. Every receipt verifies. A log with an unverifiable entry cannot be
    #    trusted anywhere, because the tampering is not localised.
    broken = [
        r.get("receipt_digest", "<no digest>") for r in trials if not verify_receipt(r)
    ]
    if broken:
        _add(report, "digests", f"{len(broken)} receipt(s) fail verification: {broken[:3]}")

    # 2. One organism throughout. Receipts under two fingerprints are never
    #    pooled, so a second one silently makes this two studies.
    fingerprints = {
        r.get("organism", {}).get("organism_fingerprint")
        for r in trials
        if isinstance(r.get("organism"), Mapping)
    }
    if len(fingerprints) > 1:
        _add(report, "organism", f"{len(fingerprints)} distinct fingerprints in one log")

    # 3. One preregistration in force. Two means the commitments moved while the
    #    data was arriving, which is the failure the digest exists to expose.
    digests = {
        r.get("experiment", {}).get("preregistration_digest")
        for r in trials
        if isinstance(r.get("experiment"), Mapping)
    }
    if len(digests) > 1:
        _add(report, "preregistration", f"{len(digests)} distinct digests in one log")

    # 4. Everything is the class it claims. A stray exploratory or rehearsal
    #    receipt in a confirmatory log is a trial that was never committed to.
    classes = {
        r.get("experiment", {}).get("analysis_class")
        for r in trials
        if isinstance(r.get("experiment"), Mapping)
    }
    stray = classes - {expected_analysis_class}
    if stray:
        _add(report, "analysis_class", f"unexpected classes present: {sorted(map(str, stray))}")

    # 5. Sequence indices are unique. Duplicates make the order unreconstructable,
    #    and the order is the only evidence the arms were interleaved.
    indices = [
        r["experiment"]["run_sequence_index"]
        for r in trials
        if isinstance(r.get("experiment"), Mapping)
        and isinstance(r["experiment"].get("run_sequence_index"), int)
    ]
    if len(set(indices)) != len(indices):
        _add(report, "sequence", f"{len(indices) - len(set(indices))} duplicate index/indices")

    # 6. Exclusions under the ceiling, per arm. Above it the remaining sample is
    #    a selected one, whichever way the difference points.
    per_arm: dict[str, list[bool]] = {}
    for r in trials:
        arm = (r.get("treatment") or {}).get("arm")
        result = (r.get("outcome") or {}).get("result")
        if isinstance(arm, str):
            per_arm.setdefault(arm, []).append(result in ("error", "excluded"))
    for arm, flags in sorted(per_arm.items()):
        rate = sum(flags) / len(flags)
        if rate > exclusion_ceiling:
            _add(
                report,
                "exclusions",
                f"arm {arm}: {rate:.0%} excluded, over the {exclusion_ceiling:.0%} ceiling; "
                "the remaining sample is a selected one",
            )

    # 7. Only committed tasks. A task outside the set was never preregistered,
    #    and including it converts the study into a different one.
    if committed_tasks is not None:
        allowed = set(committed_tasks)
        seen = {
            (r.get("benchmark") or {}).get("task_id")
            for r in trials
            if isinstance(r.get("benchmark"), Mapping)
        }
        extra = {t for t in seen if t not in allowed}
        if extra:
            _add(report, "task set", f"{len(extra)} task(s) outside the committed set: {sorted(extra)[:3]}")
        missing = allowed - seen
        if missing:
            _add(
                report,
                "task set",
                f"{len(missing)} committed task(s) have no trials: {sorted(missing)[:3]}",
                fatal=False,
            )

    # 8. The run matches the plan.
    if schedule is not None:
        planned = {entry.index: (entry.task_id, entry.arm) for entry in schedule.entries}
        if len(trials) != len(schedule):
            _add(
                report,
                "coverage",
                f"{len(trials)} receipts against {len(schedule)} scheduled trials",
                fatal=len(trials) > len(schedule),
            )
        mismatched = []
        for r in trials:
            section = r.get("experiment")
            if not isinstance(section, Mapping):
                continue
            index = section.get("run_sequence_index")
            if index not in planned:
                mismatched.append((index, "not in the schedule"))
                continue
            task, arm = planned[index]
            actual = (
                (r.get("benchmark") or {}).get("task_id"),
                (r.get("treatment") or {}).get("arm"),
            )
            if actual != (task, arm):
                mismatched.append((index, f"scheduled {task}/{arm}, ran {actual[0]}/{actual[1]}"))
        if mismatched:
            _add(
                report,
                "schedule",
                f"{len(mismatched)} receipt(s) do not match the plan: {mismatched[:3]}",
            )

    # 9. Corrections point at real entries. One that does not is an assertion
    #    about a receipt nobody can find.
    known = {r.get("receipt_digest") for r in trials}
    dangling = [
        c["correction"].get("corrects_digest")
        for c in corrections
        if isinstance(c.get("correction"), Mapping)
        and c["correction"].get("corrects_digest") not in known
    ]
    if dangling:
        _add(report, "corrections", f"{len(dangling)} correction(s) name no receipt in this log")

    return report
