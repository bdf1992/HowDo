"""Locate the payload and make its runtime importable.

Both entry points in this directory need exactly this, and the first copy of it
had already drifted from the second -- one printed a diagnostic when the
runtime was missing, the other exited silently. One copy, so a fix reaches
both.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def plugin_root(entry: str) -> Path:
    """The payload ``entry`` was shipped inside.

    ``CLAUDE_PLUGIN_ROOT`` is authoritative when a host sets it, and is not
    resolved: the value only becomes a ``sys.path`` entry, so walking symlinks
    costs a syscall per component and buys nothing. Falling back to the file's
    own parent keeps these scripts working under ``--plugin-dir``, a direct
    checkout, and a plain skills directory, none of which export it.
    """
    declared = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if declared:
        return Path(declared).expanduser()
    return Path(entry).resolve().parent.parent


def add_runtime(entry: str) -> Path:
    """Put the payload's runtime on ``sys.path`` and return the payload root."""
    root = plugin_root(entry)
    sys.path.insert(0, str(root / "runtime"))
    return root
