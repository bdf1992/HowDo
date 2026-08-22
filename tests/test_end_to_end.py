"""The whole chain, once, on a synthetic Harbor jobs directory.

Every module here is unit-tested in isolation and none of them had ever been
run against each other. That gap is exactly what `REHEARSAL.md` exists to close
before real trials are spent, and most of the rehearsal needs no containers:
a directory shaped like Harbor's output exercises the walk, the blob store, the
ingest, the append-only log, the schedule, the audit, and the analysis in the
order a real run would.

What this cannot do is prove Harbor writes what the fixture writes. That is
still the real rehearsal's job, and `REHEARSAL.md` still asks for it.
"""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from analysis import analyse, decide  # noqa: E402
from evidence import append_receipt, read_receipts  # noqa: E402
from harness import (  # noqa: E402
    BlobStore,
    JobsError,
    build_or_load,
    check_run,
    find_trials,
    ordered_trials,
    ingest_trial,
    remaining,
    store_artifacts,
)

D = lambda c: c * 64  # noqa: E731

TASKS = ("adaptive-rejection-sampler", "crack-7z-hash", "dna-assembly", "qemu-alpine-ssh")
TRIALS_PER_ARM = 4
SEED = 20260822


def write_harbor_job(root: Path, entries, *, lift: float, base_rate: float, seed: int):
    """A directory shaped exactly like Harbor's, including the job result.json
    that sits beside the trials and must not be mistaken for one."""
    rng = random.Random(seed)
    job = root / "jobs" / "pilot-0001"
    job.mkdir(parents=True)
    (job / "config.json").write_text("{}", encoding="utf-8")
    # The trap: a job-level result.json beside the trial directories.
    (job / "result.json").write_text(
        json.dumps({"job_name": "pilot-0001", "n_trials": len(entries)}), encoding="utf-8"
    )

    for entry in entries:
        rate = base_rate + (lift if entry.arm == "h1" else 0.0)
        solved = rng.random() < rate
        trial = job / f"{entry.task_id}.{entry.arm}.{entry.replicate}"
        (trial / "agent").mkdir(parents=True)
        (trial / "verifier").mkdir(parents=True)
        (trial / "agent" / "trajectory.json").write_text(
            json.dumps({"steps": [{"i": entry.index}]}), encoding="utf-8"
        )
        (trial / "agent" / "recording.cast").write_bytes(b"x" * 5000)
        (trial / "verifier" / "reward.txt").write_text("1" if solved else "0", encoding="utf-8")
        (trial / "verifier" / "test-stdout.txt").write_text("...", encoding="utf-8")
        (trial / "config.json").write_text("{}", encoding="utf-8")
        (trial / "result.json").write_text(
            json.dumps(
                {
                    "task_name": entry.task_id,
                    "task_checksum": D(str(abs(hash(entry.task_id)) % 10)),
                    "agent_info": {
                        "name": "terminus", "version": "2.0",
                        "model_info": {"name": "gemma-12b-it-Q8_0", "provider": "local"},
                    },
                    "agent_result": {
                        "n_input_tokens": 8000 + entry.index,
                        "n_cache_tokens": 100,
                        "n_output_tokens": 1200,
                    },
                    "verifier_result": {"rewards": {"reward": 1 if solved else 0}},
                    "started_at": "2026-09-01T10:00:00+00:00",
                    "finished_at": "2026-09-01T10:15:00+00:00",
                }
            ),
            encoding="utf-8",
        )
    return job


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = BlobStore(self.root / "blobs")
        self.log = self.root / "receipts.jsonl"
        self.schedule = build_or_load(
            self.root / "schedule.json",
            experiment_id="PILOT-0001",
            tasks=TASKS,
            trials_per_arm=TRIALS_PER_ARM,
            seed=SEED,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *, lift: float, base_rate: float = 0.35, seed: int = 1):
        job = write_harbor_job(
            self.root, self.schedule.entries, lift=lift, base_rate=base_rate, seed=seed
        )
        # The runner persists this as it goes; nothing in Harbor's output
        # records which scheduled trial a directory was.
        by_name = {
            f"{e.task_id}.{e.arm}.{e.replicate}": e for e in self.schedule.entries
        }
        index_of = {name: e.index for name, e in by_name.items()}
        by_index = {e.index: e for e in self.schedule.entries}
        for index, trial_dir, result in ordered_trials(self.root / "jobs", index_of):
            entry = by_index[index]
            artifacts = store_artifacts(trial_dir, self.store)
            receipt = ingest_trial(
                result,
                experiment={
                    "experiment_id": "PILOT-0001",
                    "preregistration_digest": D("1"),
                    "analysis_class": "confirmatory",
                    "condition_label": f"{entry.arm}-arm",
                    "run_sequence_index": entry.index,
                    "trial_id": f"t-{entry.index:04d}",
                },
                organism={
                    "organism_version": 1,
                    "organism_fingerprint": D("5"),
                    "organism_model_name": "gemma-12b-it-Q8_0",
                },
                treatment={
                    "arm": entry.arm, "skill_commit": "a" * 40,
                    "skill_content_digest": D("6"), "recon_budget": 8000,
                    "recon_used": 0 if entry.arm == "h0" else 3000,
                    "recon_outcome": "not_applicable" if entry.arm == "h0" else "complete",
                },
                resolution={"resolution_version": 1, "resolution_digest": D("7")},
                suite="terminal-bench", suite_version="2.0",
                task_qualification_digest=D("2"),
                image_ref="img", image_digest=D("3"),
                environment_context_digest=None if entry.arm == "h0" else D("4"),
                verifier_kind="deterministic",
                verifier_output_digest=artifacts.verifier_output_digest,
                trajectory_digest=artifacts.trajectory_digest,
            )
            append_receipt(self.log, receipt)
        return job

    def test_the_whole_chain_runs_and_audits_clean(self):
        self._run(lift=0.0)
        receipts = read_receipts(self.log)
        self.assertEqual(len(receipts), len(self.schedule))
        report = check_run(receipts, schedule=self.schedule, committed_tasks=TASKS)
        self.assertTrue(report.clean, str(report))

    def test_the_job_result_is_not_mistaken_for_a_trial(self):
        """A job directory carries its own result.json beside the trials'."""
        self._run(lift=0.0)
        self.assertEqual(len(read_receipts(self.log)), len(self.schedule))

    def test_every_custody_digest_resolves_to_bytes_that_rehash(self):
        """The runbook's post-collection check, actually executed."""
        self._run(lift=0.0)
        for receipt in read_receipts(self.log):
            for digest in (
                receipt["custody"]["trajectory_digest"],
                receipt["outcome"]["verifier_output_digest"],
            ):
                with self.subTest(digest=digest):
                    self.assertTrue(self.store.has(digest))
                    self.store.get(digest)  # raises if the bytes moved
        self.assertEqual(self.store.verify_all(), [])

    def test_the_recording_is_not_stored(self):
        """The terminal recording is the same information the trajectory already
        carries, at far more bytes.

        Asserted by reading the archive rather than by total store size: tar
        pads every archive to a 10 KB block, so size is dominated by padding and
        would hide the recording rather than reveal it.
        """
        import io
        import tarfile

        self._run(lift=0.0)
        for receipt in read_receipts(self.log):
            archive = tarfile.open(
                fileobj=io.BytesIO(self.store.get(receipt["custody"]["trajectory_digest"]))
            )
            names = archive.getnames()
            with self.subTest(trial=receipt["experiment"]["trial_id"]):
                self.assertIn("trajectory.json", names)
                self.assertNotIn("recording.cast", names)

    def test_the_log_is_in_schedule_order_and_complete(self):
        self._run(lift=0.0)
        receipts = read_receipts(self.log)
        self.assertEqual(
            [r["experiment"]["run_sequence_index"] for r in receipts],
            [e.index for e in self.schedule.entries],
        )
        self.assertEqual(remaining(self.schedule, receipts), ())

    def test_a_real_lift_reaches_the_analysis(self):
        self._run(lift=0.45, base_rate=0.25, seed=3)
        receipts = read_receipts(self.log)
        report = check_run(receipts, schedule=self.schedule, committed_tasks=TASKS)
        self.assertTrue(report.analysable, str(report))
        result = analyse(receipts, seed=1, permutations=200, resamples=400)
        self.assertGreater(result.effect, 0.0)

    def test_a_null_does_not_reach_go(self):
        self._run(lift=0.0, seed=11)
        result = analyse(read_receipts(self.log), seed=1, permutations=200, resamples=400)
        self.assertNotEqual(decide(result, delta_star=0.10, harm_ceiling=1.0)[0], "GO")

    def test_a_resumed_run_continues_rather_than_restarting(self):
        self._run(lift=0.0)
        partial = read_receipts(self.log)[:9]
        left = remaining(self.schedule, partial)
        self.assertEqual(len(left), len(self.schedule) - 9)
        self.assertEqual(left[0].index, 9)
        reloaded = build_or_load(
            self.root / "schedule.json",
            experiment_id="PILOT-0001", tasks=TASKS,
            trials_per_arm=TRIALS_PER_ARM, seed=SEED,
        )
        self.assertEqual(reloaded.digest, self.schedule.digest)

    def test_an_arm_swapped_after_the_fact_is_caught_by_the_audit(self):
        """The one failure no single module can see: every receipt verifies,
        every digest resolves, and the run is still not the planned study."""
        self._run(lift=0.0)
        receipts = read_receipts(self.log)
        report = check_run(receipts, schedule=self.schedule, committed_tasks=TASKS)
        self.assertTrue(report.clean)

        swapped = self.schedule.entries[5]
        forged = dict(receipts[5])
        forged["treatment"] = dict(forged["treatment"])
        forged["treatment"]["arm"] = "h1" if swapped.arm == "h0" else "h0"
        receipts[5] = forged
        report = check_run(receipts, schedule=self.schedule, committed_tasks=TASKS)
        self.assertFalse(report.analysable)
        self.assertTrue(any(f.check in ("digests", "schedule") for f in report.findings))


if __name__ == "__main__":
    unittest.main()


class OrderingTests(unittest.TestCase):
    """The bug this file found on its first run.

    Harbor names trial directories after the task, so a filesystem walk returns
    them alphabetically while the study ran them interleaved. Appending in walk
    order hits the append-only log's sequence rule and stops the ingestion --
    correctly, but with an error that reads like a corrupt log rather than like
    a caller iterating in the wrong order.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.schedule = build_or_load(
            self.root / "schedule.json",
            experiment_id="PILOT-0001", tasks=TASKS,
            trials_per_arm=2, seed=SEED,
        )
        write_harbor_job(self.root, self.schedule.entries, lift=0.0, base_rate=0.5, seed=1)
        self.index_of = {
            f"{e.task_id}.{e.arm}.{e.replicate}": e.index for e in self.schedule.entries
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_discovery_order_is_not_run_order(self):
        walked = [d.name for d, _ in find_trials(self.root / "jobs")]
        ran = sorted(self.index_of, key=lambda n: self.index_of[n])
        self.assertNotEqual(walked, ran)

    def test_ordered_trials_returns_run_order(self):
        rows = ordered_trials(self.root / "jobs", self.index_of)
        self.assertEqual([i for i, _, _ in rows], sorted(self.index_of.values()))

    def test_an_unmapped_trial_is_refused_not_skipped(self):
        """A trial that ran and cannot be placed is either outside the plan or
        a lost mapping. Both are worth stopping for."""
        partial = dict(self.index_of)
        partial.pop(next(iter(partial)))
        with self.assertRaises(JobsError) as caught:
            ordered_trials(self.root / "jobs", partial)
        self.assertIn("not in the run mapping", str(caught.exception))

    def test_a_duplicated_index_is_refused(self):
        broken = dict(self.index_of)
        keys = list(broken)
        broken[keys[1]] = broken[keys[0]]
        with self.assertRaises(JobsError):
            ordered_trials(self.root / "jobs", broken)
