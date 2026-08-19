#!/usr/bin/env python3
"""Install How Do as a skill directory, keeping the durable context out of it.

Two things live in different places on purpose:

    template  <skills-dir>/how-do/CONTEXT.template.md   shipped artifact; replaced on update
    store     per-user application data                 per-person lineage; never touched

The store defaults to where the platform keeps per-user state --
``%APPDATA%/howdo/CONTEXT.md`` on Windows, ``~/.howdo/CONTEXT.md`` elsewhere --
and ``HOWDO_CONTEXT`` or ``--context`` overrides it.

The directory name comes from ``name:`` in ``SKILL.md`` rather than from the
repository folder, because a loader that matches on the frontmatter name will
not find a directory called ``HowDo``.

Usage:
    python install.py                 install, then report store state
    python install.py --target DIR    install into a different skills directory
    python install.py --context PATH  use a specific durable context file
    python install.py --shared        opt in to one generic store inside the payload
    python install.py --verify        check an existing install; change nothing
    python install.py --dry-run       print what would happen
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "runtime"))

from howdo.context import (  # noqa: E402
    default_store_path,
    ensure_context,
    inspect_context,
    payload_root,
    resolve_context_path,
)

DEFAULT_SKILLS_DIR = Path.home() / ".claude" / "skills"

# The payload is what a host loads. Tests, packaging, and contributor docs are
# repository concerns and are deliberately not shipped into the skill directory.
PAYLOAD = ("SKILL.md", "CONTEXT.template.md", "QUICKSTART.md", "LICENSE",
           "references", "runtime", "examples")

# Build and tool droppings are not part of the skill. The README tells people to
# run the tests, so without this an install ships whatever bytecode that left
# behind -- stale, platform-specific, and never loaded by the host.
NOISE = shutil.ignore_patterns(
    "__pycache__", "*.py[cod]", "*.egg-info", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".DS_Store",
)


def skill_name(skill_md: Path) -> str:
    """Read ``name:`` from the skill frontmatter; the install dir must match it."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{skill_md} has no frontmatter")
    end = text.find("\n---", 3)
    front = text[3 : end if end != -1 else len(text)]
    match = re.search(r"(?m)^name:\s*(\S+)\s*$", front)
    if not match:
        raise ValueError(f"{skill_md} frontmatter has no name")
    return match.group(1).strip().strip("\"'")


def copy_payload(destination: Path, *, dry_run: bool) -> list[str]:
    actions = []
    for item in PAYLOAD:
        source = REPO / item
        if not source.exists():
            raise FileNotFoundError(source)
        target = destination / item
        actions.append(f"copy {item} -> {target}")
        if dry_run:
            continue
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True, ignore=NOISE)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return actions


# Addressed to the person at the keyboard, not to the agent. It explains a
# pending conversation, so it prints on a fresh install only: `--verify` stays
# terse, and a reinstall over a settled context has nothing to explain.
# ASCII only. This prints to whatever console the user has, and a legacy
# codepage would turn an install into a UnicodeEncodeError.
CONFIGURATION_NOTE = """
What happens next, and why:

  This skill works better once it knows how you, in particular, come to
  understand something. That cannot be read off your machine or your task,
  so the first conversation works it out with you. Four things:

    1. a subject you already know well, so you can judge for yourself
       whether an explanation of it was any good
    2. whether a concrete case lands better before the general rule, or
       after it
    3. what convinces you that you have actually got something: predicting
       the next result, reproducing the steps, watching it break, or
       saying it back in your own words
    4. how you want to be corrected when you are wrong

  It is meant to feel like a conversation rather than a form, it happens
  once, and you can correct any of it later.

  You can also say no. Say you are not interested and that is recorded;
  you will not be asked again. Say not now and the offer stays open while
  the work gets going. Everything else works either way; what you lose is
  the tailoring.
"""


def report(payload: Path, store_path: Path, *, shared: bool = False) -> int:
    """Print the state of an install. Returns a process exit code."""
    print(f"payload  {payload}")
    print(f"store    {store_path}")

    problems = 0

    if not (payload / "SKILL.md").is_file():
        print("  FAIL  no SKILL.md in payload; nothing is installed")
        return 1

    expected = skill_name(payload / "SKILL.md")
    if payload.name != expected:
        print(f"  FAIL  directory is {payload.name!r} but SKILL.md declares {expected!r}")
        problems += 1

    inside_payload = payload_root(store_path) is not None
    if inside_payload and not shared:
        print("  FAIL  store is inside the payload; an update would discard it")
        problems += 1
    elif inside_payload:
        print("  NOTE  shared store: one generic context for every user of this install")
        print("        it survives `install.py` re-runs, but is lost if the skill")
        print("        directory is deleted or replaced wholesale")

    status = inspect_context(store_path)
    print(f"  state {status.state} — {status.reason}")
    if status.state in {"invalid", "fork_required"}:
        problems += 1
    elif status.state == "onboarding_required":
        print("  next  a short setup conversation, before the first real task")
    elif status.state == "deferred":
        print("  next  calibration was deferred; work without learned context, offer stays open")
    elif status.state == "declined":
        print("  next  calibration was declined; do not ask again, do not use as learned context")
    elif status.state == "ready":
        print("  next  nothing; load this context and work")

    print("ok" if problems == 0 else f"{problems} problem(s)")
    return 0 if problems == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=Path, default=DEFAULT_SKILLS_DIR,
                        help=f"skills directory (default: {DEFAULT_SKILLS_DIR})")
    parser.add_argument("--context", type=Path, default=None,
                        help=f"durable context file (default: $HOWDO_CONTEXT, else {default_store_path()})")
    parser.add_argument("--shared", action="store_true",
                        help="opt in to one generic store inside the payload, shared by every "
                             "user of this install (default: a per-user store outside it)")
    parser.add_argument("--verify", action="store_true", help="check an install without changing it")
    parser.add_argument("--dry-run", action="store_true", help="print planned actions only")
    args = parser.parse_args(argv)

    name = skill_name(REPO / "SKILL.md")
    payload = args.target / name

    # The skill is per-person by design: it records how one reader takes
    # explanations, so the default store is per-user and lives outside the
    # replaceable payload. A generic, install-wide context is a real use (a
    # shared machine, a team image), but it is never the silent default.
    if args.shared and args.context is None:
        store_path = payload / "CONTEXT.md"
    else:
        store_path = resolve_context_path(args.context)

    if args.verify:
        return report(payload, store_path, shared=args.shared)

    if payload_root(store_path) is not None and not args.shared:
        print(f"refusing: chosen context {store_path} is inside a skill payload", file=sys.stderr)
        print("pick a path outside the install, set HOWDO_CONTEXT, or pass --shared", file=sys.stderr)
        return 1

    for action in copy_payload(payload, dry_run=args.dry_run):
        print(action)

    if args.dry_run:
        existing = "exists; would be left untouched" if store_path.exists() else "would be created"
        print(f"store {store_path} ({existing})")
        return 0

    # ensure_context never overwrites, so reinstalling cannot clobber settled context.
    status = ensure_context(
        store_path,
        template=payload / "CONTEXT.template.md",
        scope="shared" if args.shared else "user",
    )
    print()
    code = report(payload, status.path, shared=args.shared)
    if status.state == "onboarding_required":
        print(CONFIGURATION_NOTE)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
