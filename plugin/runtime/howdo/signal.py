"""Signals: one logged line per operation, appended and never rewritten.

A signal is exactly what it sounds like -- a log entry with datums about an
operation. It is deliberately not a receipt, not a score, and not a judgement.
Whatever the graph eventually wants to say about a person's work is a
*projection* over these lines, computed later and recomputable when the
question changes. That is the same rule ``experiment/CROSSINGS.md`` states for
the skill graph, applied one layer down: freeze what cannot be recovered,
derive what can.

Two things produce a signal, and the pairing is the point:

- the **model declares** what an operation was, in a small YAML header on the
  artifact it wrote;
- the **hook observes**, from outside the model's context, that a file with
  that header actually landed on disk.

Neither half is the model grading its own work. ``SKILL.md`` refuses to treat
model output as independent evidence of its own success, and a declaration
nobody checked would be exactly that. The artifact existing is the check.

Signals are context-relevant, so they live beside the durable store rather than
inside the payload -- the payload is replaced on update and would discard them
with no error raised, which is the same trap ``CONTEXT.md`` is kept out of.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping
import json
import os
import re


# The log sits next to the store it describes. `CONTEXT.md` is prose a person
# settles; this is machine-appended lines about operations. Different shape and
# different lifetime, so a different file -- but the same directory, because
# they are about the same person and should travel together.
SIGNAL_BASENAME = "signals.jsonl"

# The header a How Do operation writes onto an artifact. Kept to two fields on
# purpose: what the operation was, and which stage of the loop it belongs to.
# Anything else is a projection waiting to be computed, not a datum that has to
# be frozen at write time.
HEADER_OPERATION = "howdo_operation"
HEADER_STAGE = "howdo_stage"

# The loop is the fixed shell every install runs, so a stage outside it is a
# typo rather than a new kind of work.
STAGES = ("map", "path", "check", "do", "look", "update")

_FRONTMATTER = re.compile(r"(?s)\A\s*---\s*\n(.*?)\n---\s*(?:\n|\Z)")
_FIELD = re.compile(r"(?m)^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")


class SignalError(ValueError):
    """A signal could not be formed from what was observed."""


@dataclass(frozen=True)
class Signal:
    """One operation, as observed.

    ``recorded_at`` is absent on purpose. A timestamp is the caller's to supply
    if it wants ordering by clock; the file itself already orders by append,
    which is the ordering that cannot be forged after the fact.
    """

    operation: str
    stage: str
    path: str
    tool: str = "unknown"
    session: str = ""
    datums: Mapping[str, Any] = field(default_factory=dict)

    def as_line(self) -> str:
        record: dict[str, Any] = {
            "operation": self.operation,
            "stage": self.stage,
            "path": self.path,
            "tool": self.tool,
        }
        if self.session:
            record["session"] = self.session
        if self.datums:
            record["datums"] = dict(self.datums)
        # Sorted keys and no spaces: a line that diffs cleanly and appends
        # identically regardless of who wrote it.
        return json.dumps(record, sort_keys=True, separators=(",", ":"))


def read_header(text: str) -> dict[str, str]:
    """Return the YAML header fields, or an empty mapping if there is none.

    This is a deliberately small reader rather than a YAML parser: the header
    is two scalar fields by contract, the runtime is zero-dependency, and a
    hook that imports a parser is a hook that fails on someone's machine.
    """
    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    return {key: value.strip().strip("\"'") for key, value in _FIELD.findall(match.group(1))}


def signal_from_header(
    text: str,
    *,
    path: str,
    tool: str = "unknown",
    session: str = "",
) -> Signal | None:
    """Form a signal from an artifact's header, or ``None`` if it declares none.

    Returning ``None`` rather than raising is the common case by a wide margin:
    most files a session writes have nothing to do with How Do, and a hook that
    complained about each of them would be unusable.
    """
    header = read_header(text)
    operation = header.get(HEADER_OPERATION, "").strip()
    if not operation:
        return None

    stage = header.get(HEADER_STAGE, "").strip().lower()
    if stage not in STAGES:
        raise SignalError(
            f"{path}: {HEADER_STAGE}={stage!r} is not one of {', '.join(STAGES)}"
        )
    return Signal(operation=operation, stage=stage, path=path, tool=tool, session=session)


def signal_log_path(store: str | Path) -> Path:
    """Where signals go, given the durable store's location."""
    return Path(store).expanduser().parent / SIGNAL_BASENAME


def append(signal: Signal, log: str | Path) -> Path:
    """Append one signal. Never rewrites, never reorders, never deduplicates.

    Opened in append mode so concurrent sessions interleave rather than
    truncate each other: two agents working at once is ordinary, and losing one
    of their histories to a last-writer-wins truncation would be silent.
    """
    destination = Path(log).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(signal.as_line() + "\n")
    return destination


def read(log: str | Path) -> Iterator[dict[str, Any]]:
    """Yield the signals in the order they were appended.

    A malformed line is skipped rather than fatal. This file is appended by
    hooks on machines we do not control, and one truncated write during a
    crash should not make the whole history unreadable.
    """
    source = Path(log).expanduser()
    if not source.is_file():
        return
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def by_stage(log: str | Path) -> dict[str, int]:
    """The smallest useful projection: how many operations per loop stage.

    It exists to make the point that projections are computed from the lines
    rather than maintained alongside them. Nothing stores this count.
    """
    counts = {stage: 0 for stage in STAGES}
    for record in read(log):
        stage = record.get("stage")
        if stage in counts:
            counts[stage] += 1
    return counts
