"""The Harbor seam: what a trial result is allowed to become.

Every refusal here corresponds to a way ingestion could invent evidence that
Harbor never reported.
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import verify_receipt  # noqa: E402
from harness import (  # noqa: E402
    BlobError,
    BlobStore,
    IngestError,
    ingest_trial,
    read_trial_result,
    wall_clock_seconds,
)

D = lambda c: c * 64  # noqa: E731

# Shaped after harbor.models.trial.result.TrialResult at
# harbor-framework/harbor@39b8587.
TRIAL = {
    "task_name": "adaptive-rejection-sampler",
    "task_checksum": D("7"),
    "agent_info": {
        "name": "terminus",
        "version": "2.0",
        "model_info": {"name": "gemma-12b-it-Q8_0", "provider": "local"},
    },
    "agent_result": {
        "n_input_tokens": 8100,
        "n_cache_tokens": 2000,
        "n_output_tokens": 1450,
        "cost_usd": 0.0,
    },
    "verifier_result": {"rewards": {"reward": 1}},
    "started_at": "2026-09-01T10:00:00+00:00",
    "finished_at": "2026-09-01T10:14:30+00:00",
    "environment_setup": {
        "started_at": "2026-09-01T10:00:00+00:00",
        "finished_at": "2026-09-01T10:01:00+00:00",
    },
    "agent_execution": {
        "started_at": "2026-09-01T10:01:00+00:00",
        "finished_at": "2026-09-01T10:13:00+00:00",
    },
}

CONTEXT = dict(
    experiment={
        "experiment_id": "PILOT-0001",
        "preregistration_digest": D("1"),
        "analysis_class": "confirmatory",
        "condition_label": "h1-howdo-recon",
        "run_sequence_index": 0,
        "trial_id": "t-0001",
    },
    organism={
        "organism_version": 1,
        "organism_fingerprint": D("5"),
        "organism_model_name": "gemma-12b-it-Q8_0",
    },
    treatment={
        "arm": "h1",
        "skill_commit": "a" * 40,
        "skill_content_digest": D("6"),
        "recon_budget": 8000,
        "recon_used": 3120,
        "recon_outcome": "complete",
    },
    resolution={"resolution_version": 1, "resolution_digest": D("9")},
    suite="terminal-bench",
    suite_version="2.0",
    task_qualification_digest=D("2"),
    image_ref="ghcr.io/example/task:1",
    image_digest=D("3"),
    environment_context_digest=D("4"),
    verifier_kind="deterministic",
    verifier_output_digest=D("8"),
    trajectory_digest=D("a"),
)


def trial(**overrides):
    built = copy.deepcopy(TRIAL)
    for key, value in overrides.items():
        if value is None:
            built.pop(key, None)
        else:
            built[key] = value
    return built


def receipt(**overrides):
    return ingest_trial(trial(**overrides), **CONTEXT)


class OutcomeTests(unittest.TestCase):
    def test_reward_one_is_a_pass(self):
        r = receipt()
        self.assertEqual(r["outcome"]["result"], "pass")
        self.assertTrue(r["outcome"]["certifies"])
        self.assertTrue(verify_receipt(r))

    def test_reward_zero_is_a_fail(self):
        r = receipt(verifier_result={"rewards": {"reward": 0}})
        self.assertEqual(r["outcome"]["result"], "fail")
        self.assertFalse(r["outcome"]["certifies"])

    def test_a_partial_reward_is_refused_rather_than_rounded(self):
        """Rounding invents an outcome the verifier did not report, and it is
        invisible in the aggregate afterwards."""
        for value in (0.5, 0.99, 0.01):
            with self.subTest(reward=value):
                with self.assertRaises(IngestError) as caught:
                    receipt(verifier_result={"rewards": {"reward": value}})
                self.assertIn("partial reward", str(caught.exception))

    def test_an_unknown_reward_vocabulary_is_refused(self):
        with self.assertRaises(IngestError):
            receipt(verifier_result={"rewards": {"score": 1}})

    def test_a_trial_with_neither_verifier_nor_exception_is_refused(self):
        with self.assertRaises(IngestError):
            receipt(verifier_result=None)


class ExceptionTests(unittest.TestCase):
    """A crash did not measure the treatment."""

    def _with(self, kind):
        return receipt(
            verifier_result=None,
            exception_info={
                "exception_type": kind,
                "exception_message": "boom",
                "exception_traceback": "...",
                "occurred_at": "2026-09-01T10:05:00+00:00",
            },
        )

    def test_an_exception_is_an_error_not_a_failure(self):
        r = self._with("DockerException")
        self.assertEqual(r["outcome"]["result"], "error")
        self.assertEqual(r["outcome"]["failure_class"], "runtime_crash")

    def test_known_exceptions_map_to_the_closed_vocabulary(self):
        for kind, expected in (
            ("TimeoutError", "harness_timeout"),
            ("MemoryError", "oom"),
            ("VerifierError", "verifier_infrastructure"),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(self._with(kind)["outcome"]["failure_class"], expected)

    def test_an_unknown_exception_becomes_other_not_a_neighbour(self):
        """Forcing it into a nearby class makes the tally wrong in a way nobody
        can see later."""
        self.assertEqual(self._with("SomeNovelError")["outcome"]["failure_class"], "other")

    def test_an_exception_wins_over_a_reward(self):
        r = receipt(
            exception_info={
                "exception_type": "TimeoutError",
                "exception_message": "x",
                "exception_traceback": "",
                "occurred_at": "2026-09-01T10:05:00+00:00",
            }
        )
        self.assertEqual(r["outcome"]["result"], "error")


class OrganismTests(unittest.TestCase):
    """Part of the gap RECEIPT.md declared open is mechanically checkable."""

    def test_a_model_mismatch_is_refused(self):
        other = dict(CONTEXT)
        other["organism"] = dict(CONTEXT["organism"], organism_model_name="qwen-7b-Q4")
        with self.assertRaises(IngestError) as caught:
            ingest_trial(trial(), **other)
        self.assertIn("never pooled", str(caught.exception))

    def test_a_matching_model_passes(self):
        self.assertTrue(verify_receipt(receipt()))

    def test_an_absent_model_name_is_not_a_mismatch(self):
        """Harbor does not always record one, and refusing would block ingestion
        on a field the runner controls."""
        self.assertTrue(verify_receipt(receipt(agent_info={"name": "x", "version": "1"})))


class ResourceTests(unittest.TestCase):
    def test_wall_clock_is_end_to_end_not_agent_only(self):
        """Container setup is real time and hours-per-100-trials must see it."""
        self.assertEqual(wall_clock_seconds(TRIAL), 870.0)

    def test_wall_clock_falls_back_to_summing_phases(self):
        partial = trial(started_at=None, finished_at=None)
        self.assertEqual(wall_clock_seconds(partial), 60.0 + 720.0)

    def test_a_trial_with_no_timing_at_all_is_refused(self):
        bare = trial(started_at=None, finished_at=None)
        bare.pop("environment_setup")
        bare.pop("agent_execution")
        with self.assertRaises(IngestError):
            wall_clock_seconds(bare)

    def test_cache_tokens_are_not_added_to_input(self):
        """n_input_tokens is documented as total input including cache."""
        self.assertEqual(receipt()["resources"]["prompt_tokens"], 8100)

    def test_missing_token_counts_become_zero_not_null(self):
        r = receipt(agent_result={})
        self.assertEqual(r["resources"]["prompt_tokens"], 0)


class TaskIdentityTests(unittest.TestCase):
    def test_a_sha256_checksum_passes_through_unchanged(self):
        """So Harbor and the receipt agree on one identity."""
        self.assertEqual(receipt()["benchmark"]["task_version"], D("7")[:12])

    def test_a_non_sha256_checksum_is_hashed_rather_than_faked(self):
        r = receipt(task_checksum="v1.2.3-abc")
        self.assertEqual(len(r["benchmark"]["task_version"]), 12)
        self.assertNotEqual(r["benchmark"]["task_version"], "v1.2.3-abc"[:12])

    def test_a_missing_checksum_is_refused(self):
        with self.assertRaises(IngestError):
            receipt(task_checksum=None)


class ReadingTests(unittest.TestCase):
    def test_a_result_file_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text(json.dumps(TRIAL), encoding="utf-8")
            self.assertEqual(read_trial_result(path)["task_name"], TRIAL["task_name"])

    def test_malformed_json_names_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text("{oops", encoding="utf-8")
            with self.assertRaises(IngestError):
                read_trial_result(path)


class BlobStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BlobStore(Path(self.tmp.name) / "blobs")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bytes_round_trip_by_digest(self):
        digest = self.store.put_bytes(b"trajectory")
        self.assertEqual(self.store.get(digest), b"trajectory")
        self.assertTrue(self.store.has(digest))

    def test_storing_twice_is_a_no_op(self):
        one = self.store.put_bytes(b"same")
        two = self.store.put_bytes(b"same")
        self.assertEqual(one, two)

    def test_a_tree_hashes_the_same_twice(self):
        """Two machines archiving one trajectory must agree, so timestamps and
        ownership are zeroed."""
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("b.txt", "a.txt"):
                (Path(tmp) / name).write_text(name)
            first = self.store.put_tree(tmp)
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a.txt", "b.txt"):
                (Path(tmp) / name).write_text(name)
            second = self.store.put_tree(tmp)
        self.assertEqual(first, second)

    def test_a_missing_blob_raises_rather_than_returning_empty(self):
        with self.assertRaises(BlobError):
            self.store.get(D("f"))

    def test_a_path_is_not_a_content_address(self):
        with self.assertRaises(BlobError):
            self.store.get("/var/runs/trial.jsonl")

    def test_an_edited_blob_is_detected_on_read(self):
        """Custody means the bytes have not changed since they were addressed."""
        digest = self.store.put_bytes(b"original")
        target = self.store.root / digest[:2] / digest[2:4] / digest
        target.write_bytes(b"tampered")
        with self.assertRaises(BlobError) as caught:
            self.store.get(digest)
        self.assertIn("unverifiable", str(caught.exception))

    def test_verify_all_finds_the_edited_blob(self):
        digest = self.store.put_bytes(b"original")
        self.assertEqual(self.store.verify_all(), [])
        (self.store.root / digest[:2] / digest[2:4] / digest).write_bytes(b"x")
        self.assertEqual(self.store.verify_all(), [digest])

    def test_a_receipt_digest_resolves_in_the_store(self):
        """The check the runbook runs after collection."""
        digest = self.store.put_bytes(b"the trajectory")
        r = ingest_trial(trial(), **dict(CONTEXT, trajectory_digest=digest))
        self.assertTrue(self.store.has(r["custody"]["trajectory_digest"]))


if __name__ == "__main__":
    unittest.main()


class QualificationDriverTests(unittest.TestCase):
    """Counting the two ways an error biases the pool in opposite directions."""

    OK = {"verifier_result": {"rewards": {"reward": 1}}}
    NO = {"verifier_result": {"rewards": {"reward": 0}}}
    ERR = {"exception_info": {"exception_type": "DockerException"}}
    PARTIAL = {"verifier_result": {"rewards": {"reward": 0.5}}}

    def _qualify(self, oracle, noop, kind="deterministic"):
        from harness import qualify_task

        return qualify_task(
            suite="terminal-bench",
            suite_version="2.0",
            task_id="adaptive-rejection-sampler",
            task_version="1",
            task_definition_digest=D("7"),
            harbor_version="0.4.2",
            image_digest=D("3"),
            verifier_kind=kind,
            oracle_results=oracle,
            noop_results=noop,
        )

    def test_a_clean_task_qualifies(self):
        held = self._qualify([self.OK] * 5, [self.NO] * 3)
        self.assertEqual(held.outcome, "qualified")

    def test_a_judged_task_is_research_only(self):
        held = self._qualify([self.OK] * 5, [self.NO] * 3, kind="judge")
        self.assertEqual(held.outcome, "research_only")

    def test_an_oracle_error_is_not_an_oracle_failure(self):
        """Otherwise a solvable task looks unsolvable and leaves a small pool."""
        counts = self._qualify([self.OK] * 4 + [self.ERR], [self.NO] * 3)
        self.assertEqual(counts.oracle_attempts, 4)
        self.assertEqual(counts.oracle_passes, 4)
        self.assertEqual(counts.infrastructure_errors, 1)

    def test_a_noop_error_is_not_a_noop_failure(self):
        """Otherwise a vacuous verifier looks strict and dilutes both arms."""
        counts = self._qualify([self.OK] * 5, [self.NO] * 2 + [self.ERR])
        self.assertEqual(counts.noop_attempts, 2)
        self.assertEqual(counts.noop_failures, 2)
        self.assertEqual(counts.infrastructure_errors, 1)

    def test_short_runs_are_not_padded_to_the_target(self):
        """The rejection is the rule working; inventing attempts defeats it."""
        held = self._qualify([self.OK] * 4 + [self.ERR], [self.NO] * 3)
        self.assertEqual(held.outcome, "rejected")
        self.assertIn("oracle ran 4 times", held.rejection_reason)

    def test_a_partial_reward_counts_as_neither(self):
        """The verifier is telling you it is not the binary instrument assumed."""
        counts = self._qualify([self.OK] * 4 + [self.PARTIAL], [self.NO] * 3)
        self.assertEqual(counts.oracle_attempts, 4)
        self.assertEqual(counts.infrastructure_errors, 1)

    def test_a_noop_that_passes_disqualifies(self):
        held = self._qualify([self.OK] * 5, [self.NO] * 2 + [self.OK])
        self.assertEqual(held.outcome, "rejected")
        self.assertIn("accepts the initial state", held.rejection_reason)

    def test_the_digest_is_citable_by_a_receipt(self):
        held = self._qualify([self.OK] * 5, [self.NO] * 3)
        self.assertEqual(len(held.digest), 64)
        built = ingest_trial(trial(), **dict(CONTEXT, task_qualification_digest=held.digest))
        self.assertEqual(built["benchmark"]["task_qualification_digest"], held.digest)
