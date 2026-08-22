"""Durable context settlement is atomic and stale-write resistant.

The lifecycle module is semantically careful; these tests guard the byte-level
half of the promise: a settlement that lands cannot be silently erased by a
writer holding a stale read, a replacement is atomic to readers, and a refused
write leaves the prior bytes intact. One fixture watches a genuine
multiprocessing race rather than a mocked sequence.
"""

import multiprocessing
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))

from howdo import (  # noqa: E402
    ContextLockError,
    complete_onboarding,
    decline_onboarding,
    defer_onboarding,
    ensure_context,
    inspect_context,
)
from howdo import context as context_module  # noqa: E402

TEMPLATE = PAYLOAD / "CONTEXT.template.md"


def _fresh_store(directory: Path) -> Path:
    status = ensure_context(directory / "CONTEXT.md", template=TEMPLATE)
    assert status.state == "onboarding_required", status.reason
    return status.path


def _race_complete(barrier, path: str, marker: str, results):
    """Child process body: everyone reads the same pre-state, then writes.

    A spawned child re-imports this module, whose top-level path insert makes
    ``howdo`` importable again in the fresh interpreter.
    """
    barrier.wait()
    try:
        complete_onboarding(
            path,
            calibration_domain=f"domain settled by {marker}",
            representation_observation=f"observation from {marker}",
            landed_example=f"landed for {marker}",
            rejected_example=f"rejected for {marker}",
        )
        results.put(("settled", marker))
    except ValueError as exc:
        results.put(("refused", f"{marker}: {exc}"))
    except Exception as exc:  # pragma: no cover - diagnostic only
        results.put(("error", f"{marker}: {exc!r}"))


class RacingWriterTests(unittest.TestCase):
    def test_concurrent_completions_settle_exactly_once(self):
        """A genuine race: N processes released together onto one fresh store.

        Exactly one settlement may land. Every other writer held the same
        pre-state and must be refused by its own state guard rather than
        silently erase the winner.
        """
        writers = 4
        ctx = multiprocessing.get_context("spawn")
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            barrier = ctx.Barrier(writers)
            results = ctx.Queue()
            processes = [
                ctx.Process(
                    target=_race_complete,
                    args=(barrier, str(store), f"writer-{i}", results),
                )
                for i in range(writers)
            ]
            for proc in processes:
                proc.start()
            for proc in processes:
                proc.join(timeout=60)
                self.assertFalse(proc.is_alive(), "a racing writer hung")

            outcomes = [results.get(timeout=10) for _ in range(writers)]
            settled = [m for kind, m in outcomes if kind == "settled"]
            refused = [m for kind, m in outcomes if kind == "refused"]
            errors = [m for kind, m in outcomes if kind == "error"]

            self.assertEqual(errors, [])
            self.assertEqual(len(settled), 1, f"outcomes: {outcomes}")
            self.assertEqual(len(refused), writers - 1)
            for reason in refused:
                self.assertIn("already complete", reason)

            status = inspect_context(store)
            self.assertEqual(status.state, "ready", status.reason)
            text = store.read_text(encoding="utf-8")
            self.assertIn(f"domain settled by {settled[0]}", text)
            losers = [m for m in (f"writer-{i}" for i in range(writers)) if m != settled[0]]
            for loser in losers:
                self.assertNotIn(loser, text)


class StaleAuthorTests(unittest.TestCase):
    def test_a_stale_author_is_refused_and_the_prior_bytes_survive(self):
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            complete_onboarding(
                store,
                calibration_domain="incident response",
                representation_observation="relation first",
                landed_example="boundary diagram landed",
                rejected_example="taxonomy prose did not",
            )
            settled = store.read_text(encoding="utf-8")
            # A second author whose read predates the settlement re-validates
            # under the lock and fails instead of overwriting.
            with self.assertRaisesRegex(ValueError, "already complete"):
                complete_onboarding(
                    store,
                    calibration_domain="something else entirely",
                    representation_observation="rule first",
                    landed_example="other",
                    rejected_example="other still",
                )
            self.assertEqual(store.read_text(encoding="utf-8"), settled)

    def test_a_stale_decline_cannot_erase_a_settlement(self):
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            complete_onboarding(
                store,
                calibration_domain="incident response",
                representation_observation="relation first",
                landed_example="landed",
                rejected_example="rejected",
            )
            settled = store.read_text(encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot be converted"):
                decline_onboarding(store)
            self.assertEqual(store.read_text(encoding="utf-8"), settled)

    def test_settlements_leave_no_temp_or_lock_droppings(self):
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            defer_onboarding(store)
            complete_onboarding(
                store,
                calibration_domain="incident response",
                representation_observation="relation first",
                landed_example="landed",
                rejected_example="rejected",
            )
            with self.assertRaises(ValueError):
                decline_onboarding(store)  # refused: the context is ready
            strays = [p.name for p in Path(td).iterdir() if p.name != "CONTEXT.md"]
            self.assertEqual(strays, [], f"settlement left droppings: {strays}")


class LockLifecycleTests(unittest.TestCase):
    def test_a_live_lock_makes_the_writer_fail_rather_than_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            lock = store.with_name(store.name + context_module._LOCK_SUFFIX)
            lock.touch()
            try:
                with self.assertRaises(ContextLockError):
                    with context_module._context_lock(store, timeout=0.2):
                        pass
            finally:
                lock.unlink()

    def test_a_lock_abandoned_by_a_dead_writer_is_broken(self):
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            lock = store.with_name(store.name + context_module._LOCK_SUFFIX)
            lock.touch()
            stale = time.time() - (context_module._LOCK_STALE_S + 5)
            os.utime(lock, (stale, stale))
            # The writer must not deadlock on a corpse: the stale lock is
            # broken and the settlement proceeds.
            defer_onboarding(store)
            self.assertEqual(inspect_context(store).state, "deferred")

    def test_settlement_releases_the_lock(self):
        with tempfile.TemporaryDirectory() as td:
            store = _fresh_store(Path(td))
            defer_onboarding(store)
            lock = store.with_name(store.name + context_module._LOCK_SUFFIX)
            self.assertFalse(lock.exists(), "settlement left the store locked")


if __name__ == "__main__":
    unittest.main()
