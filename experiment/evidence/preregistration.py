"""The preregistration digest: which commitments were in force when a trial ran.

Every confirmatory receipt carries this digest. That is the whole mechanism by
which "we said in advance what would count" becomes checkable instead of
remembered: a later reader recomputes the digest of the document as it stands,
compares it with the one in the receipt, and learns whether the commitments
moved after the data started arriving.

Two refusals make it worth something.

A document with an undeclared commitment cannot be digested. A preregistration
whose effect threshold is still a proposal is not a preregistration, and a
digest over it would look exactly like a digest over a real one. The markers
are removed by a person deciding, not by a script.

A document frozen in two stages carries two digests, and the second is not
optional. Stage A fixes what M0.0 must not be allowed to influence; Stage B
fills what only M0.0 can supply. A receipt collected under Stage A while Stage B
is still open is not a confirmatory trial.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import re

__all__ = [
    "PreregistrationError",
    "UNDECLARED",
    "preregistration_digest",
    "undeclared_markers",
]

# ``<<DECLARE: ...>>`` is a value a person still has to choose.
# ``<<STAGE-A: ...>>`` and ``<<STAGE-B: ...>>`` are freeze records not yet made.
UNDECLARED = re.compile(r"<<(DECLARE|STAGE-A|STAGE-B)\b[^>]*>*", re.DOTALL)


class PreregistrationError(ValueError):
    """A preregistration that cannot be cited honestly."""


def undeclared_markers(path: str | Path) -> list[str]:
    """Every unfilled commitment in the document, shortened for reporting."""
    text = Path(path).read_text(encoding="utf-8")
    found = []
    for match in UNDECLARED.finditer(text):
        fragment = " ".join(match.group(0).split())
        found.append(fragment[:96] + ("…" if len(fragment) > 96 else ""))
    return found


def preregistration_digest(path: str | Path, *, stage: str = "B") -> str:
    """Digest the document, refusing one that still has open commitments.

    ``stage`` selects how much must be settled. ``"A"`` allows Stage B fields to
    remain open, which is the state the document is legitimately in between the
    two freezes; ``"B"`` — the default, and what a confirmatory receipt requires
    — allows nothing open at all.
    """
    if stage not in ("A", "B"):
        raise PreregistrationError(f"stage must be 'A' or 'B', got {stage!r}")
    text = Path(path).read_text(encoding="utf-8")
    open_markers = [
        " ".join(match.group(0).split())[:96]
        for match in UNDECLARED.finditer(text)
        if not (stage == "A" and match.group(1) == "STAGE-B")
    ]
    if open_markers:
        raise PreregistrationError(
            f"{len(open_markers)} commitment(s) still undeclared at stage {stage}; "
            "a digest over an unfilled preregistration looks exactly like a digest "
            "over a real one:\n  - " + "\n  - ".join(open_markers)
        )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
