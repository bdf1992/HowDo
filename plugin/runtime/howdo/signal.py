"""Signals: one logged line per operation, appended and never rewritten.

A signal is what it sounds like -- a log entry with datums about an operation.
It is not a receipt, not a score, and not a judgement. Whatever a graph
eventually says about a person's work is a *projection* over these lines,
computed later and recomputable when the question changes. The rule is: freeze
what cannot be recovered, derive what can. Anything a query could reconstruct
from these lines does not belong in them, because storing it fixes an answer to
a question that has not been asked yet.

Two things produce a signal, and the pairing is the point:

- the **model declares** what an operation was, in a small header on the
  artifact it wrote;
- the **hook observes**, from outside the model's context, that a file with
  that header actually landed on disk.

Neither half is the model grading its own work. ``SKILL.md`` refuses to treat
model output as independent evidence of its own success, and a declaration
nobody checked would be exactly that. The artifact existing is the check.

Two things *are* frozen into each line, because they cannot be recovered
afterwards. **When** an operation happened is not derivable from append order:
several sessions append to one file concurrently, so position orders writes
rather than events, and nothing relates a signal to a receipt or a run without
a clock. And the **format version**, because the first change to the line shape
would otherwise make every earlier line ambiguous -- with malformed-tolerant
reading hiding the ambiguity instead of surfacing it. A version in the line is
what lets a later reader skip a dialect it does not understand rather than
misread it as the current one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
import json

from .context import payload_root, read_frontmatter, resolve_context_path


# Bump when the line shape changes. Readers use it to skip dialects they do not
# understand rather than silently mixing them.
SIGNAL_VERSION = 1

# The log sits beside the store it describes. ``CONTEXT.md`` is prose a person
# settles; this is machine-appended lines about operations. Different shape,
# different lifetime, so a different file -- same directory, because they are
# about the same person and should travel together.
SIGNAL_BASENAME = "signals.jsonl"
SIGNAL_ENV = "HOWDO_SIGNALS"

# The header a How Do operation writes onto an artifact. Two fields on purpose:
# what the operation was, and which stage of the loop it belongs to. Anything
# else is a projection waiting to be computed, not a datum to freeze at write
# time.
HEADER_OPERATION = "howdo_operation"
HEADER_STAGE = "howdo_stage"

# Optional, and the difference between a usage log and something a person can
# be learned from. Onboarding is explicit that a stated preference is a
# hypothesis and only a prediction that was watched becomes evidence, so the
# record has to carry the prediction and what became of it.
#
# `held` is the model's own verdict on its own work, which the discipline
# refuses as evidence. It is recorded anyway, and never counted as observed:
# holding it beside what actually happened on disk is what makes the model's
# self-assessment itself measurable.
HEADER_EXPECTS = "howdo_expects"   # at Check: what this commits to
HEADER_HELD = "howdo_held"         # at Look: the model's verdict, declared
HEADER_DOMAIN = "howdo_domain"     # which domain, for the anchor
HEADER_SHAPE = "howdo_shape"       # instance-first or principle-first

SHAPES = ("instance-first", "principle-first")
HELD = {"yes": True, "no": False, "true": True, "false": False}

# The loop is the fixed shell every install runs, so a stage outside it is a
# typo rather than a new kind of work.
STAGES = ("map", "path", "check", "do", "look", "update")

# Which payload key holds the path each writing tool actually wrote. A table
# rather than one inline lookup because the tools do not agree on the key, so a
# hook that assumed a single shape would be wired up and permanently silent for
# whichever tool disagreed.
#
# NotebookEdit is deliberately absent. A ``.ipynb`` is JSON: it begins with
# ``{``, so it can never carry a header at byte 0, and wiring it up would add a
# process spawn on every notebook edit that can only ever decline to record.
# Notebooks would need a different mechanism -- a declaration in notebook
# metadata, not frontmatter -- and that is a separate decision, not an
# extension of this one.
TOOL_PATH_KEYS = {
    "Write": "file_path",
    "Edit": "file_path",
    "MultiEdit": "file_path",
}

# A header is two short lines at the top of a file. Reading more than this to
# find it is wasted work on a path taken for every edit in every session, and
# an unbounded read is also what makes a malformed file expensive.
HEADER_BYTES = 4096


class SignalError(ValueError):
    """A signal could not be formed from what was observed."""


@dataclass(frozen=True)
class Signal:
    """One operation, as observed."""

    operation: str
    stage: str
    path: str
    tool: str
    recorded_at: float
    session: str = ""
    expects: str = ""
    held: bool | None = None
    domain: str = ""
    shape: str = ""

    def as_line(self) -> str:
        record: dict[str, Any] = {
            "v": SIGNAL_VERSION,
            "operation": self.operation,
            "stage": self.stage,
            "path": self.path,
            "tool": self.tool,
            "recorded_at": round(self.recorded_at, 3),
        }
        if self.session:
            record["session"] = self.session
        # Absent rather than empty: a reader distinguishes "not declared" from
        # "declared as nothing", and only the first is a gap.
        for key, value in (("expects", self.expects), ("domain", self.domain),
                           ("shape", self.shape)):
            if value:
                record[key] = value
        if self.held is not None:
            record["held"] = self.held
        # Sorted keys and no spaces: a line that diffs cleanly and appends
        # identically regardless of who wrote it.
        return json.dumps(record, sort_keys=True, separators=(",", ":"))


def written_path(payload: dict[str, Any]) -> str | None:
    """The path a writing tool reported, or ``None`` if this tool wrote nothing.

    A signal is about an artifact existing, so a tool with no artifact -- a
    read, a search -- has nothing to record.
    """
    key = TOOL_PATH_KEYS.get(str(payload.get("tool_name", "")))
    if key is None:
        return None
    written = (payload.get("tool_input") or {}).get(key)
    return str(written) if written else None


def read_header(text: str) -> dict[str, str]:
    """Return the artifact's header fields, or an empty mapping if there is none.

    Delegates to the one frontmatter parser this project has. A second dialect
    would diverge from it on exactly the malformed files nobody tests with.
    """
    return read_frontmatter(text)


def signal_from_header(
    text: str,
    *,
    path: str,
    tool: str,
    recorded_at: float,
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
    shape = header.get(HEADER_SHAPE, "").strip().lower()
    if shape and shape not in SHAPES:
        raise SignalError(
            f"{path}: {HEADER_SHAPE}={shape!r} is not one of {', '.join(SHAPES)}"
        )

    declared = header.get(HEADER_HELD, "").strip().lower()
    if declared and declared not in HELD:
        raise SignalError(
            f"{path}: {HEADER_HELD}={declared!r} is not one of {', '.join(sorted(HELD))}"
        )

    return Signal(
        operation=operation,
        stage=stage,
        path=path,
        tool=tool,
        recorded_at=recorded_at,
        session=session,
        expects=header.get(HEADER_EXPECTS, "").strip(),
        held=HELD.get(declared) if declared else None,
        domain=header.get(HEADER_DOMAIN, "").strip(),
        shape=shape,
    )


def resolve_signal_log(
    explicit: str | Path | None = None,
    *,
    env: Any = None,
    context_path: str | Path | None = None,
) -> Path:
    """Where signals go. Beside the store, overridable, never in the payload.

    The payload refusal is not defensive tidiness. ``install.py --shared`` puts
    the store *inside* the payload on purpose, and an append-only log that
    followed it there would be deleted by the next update with no error raised
    -- which is the exact trap this module claims to keep the log out of.
    """
    if explicit is not None:
        return Path(explicit).expanduser()

    import os  # noqa: PLC0415 - only needed when no path was handed in

    environ = os.environ if env is None else env
    configured = environ.get(SIGNAL_ENV)
    if configured:
        return Path(configured).expanduser()

    store = Path(context_path) if context_path is not None else resolve_context_path()
    candidate = store.expanduser().parent / SIGNAL_BASENAME
    if payload_root(candidate) is not None:
        raise SignalError(
            f"{candidate} is inside a skill payload; an update would discard it. "
            f"Point {SIGNAL_ENV} somewhere outside the install."
        )
    return candidate


def append(signal: Signal, log: str | Path) -> Path:
    """Append one signal. Never rewrites, never reorders, never deduplicates.

    Opened in append mode so concurrent sessions interleave rather than
    truncate each other: two agents working at once is ordinary, and losing one
    of their histories to a last-writer-wins truncation would be silent.
    """
    destination = Path(log).expanduser()
    line = signal.as_line() + "\n"
    try:
        with destination.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except FileNotFoundError:
        # The directory is the store's own parent and so exists in every
        # ordinary case. Creating it on the exception rather than on every
        # append keeps a syscall off the recording path.
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as handle:
            handle.write(line)
    return destination


def read(log: str | Path) -> Iterator[dict[str, Any]]:
    """Yield the signals in the order they were appended.

    A malformed line is skipped rather than fatal: this file is appended by
    hooks on machines we do not control, and one truncated write during a crash
    should not make the whole history unreadable. A line from a dialect this
    version does not know is skipped for the same reason -- better absent than
    silently misread as the current shape.
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
            if isinstance(record, dict) and record.get("v") == SIGNAL_VERSION:
                yield record
