"""The organism fingerprint: what a receipt means when it names a machine.

A fingerprint that can be produced from an unfilled form, or that changes when
an irrelevant observation changes, cannot support the rule it exists for --
that receipts under two fingerprints are never pooled.
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import (  # noqa: E402
    ORGANISM_VERSION,
    OrganismError,
    OrganismLock,
    load_organism,
    organism_fields,
    verify_organism,
)

TEMPLATE = ROOT / "experiment" / "M-1" / "ORGANISM.template.json"
PROTOCOL = ROOT / "experiment" / "M-1" / "PROTOCOL.md"

FILLED = {
    "organism_version": ORGANISM_VERSION,
    "identity": {
        "model_file": "gemma-4-12b-it-Q8_0.gguf",
        "model_sha256": "a" * 64,
        "model_parameters": "12B",
        "quantization": "Q8_0",
        "runtime_name": "llama.cpp",
        "runtime_version": "b4321",
        "runtime_commit": "c" * 40,
        "runtime_build_flags": "-DGGML_CUDA=ON",
        "harbor_version": "0.4.2",
        "harness_config_digest": "d" * 64,
    },
    "configuration": {
        "context_cap": 32768,
        "gpu_layers": 49,
        "offload_split": "all-gpu",
        "batch_size": 512,
        "concurrency": 1,
        "sampling": {
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 0,
            "seed": 7,
            "repeat_penalty": 1.0,
            "greedy": True,
        },
    },
    "hardware": {
        "gpu_model": "RTX 4090",
        "gpu_vram_total": 25769803776,
        "cpu_model": "Ryzen 9 7950X",
        "system_ram_total": 137438953472,
        "os": "Ubuntu 24.04",
        "kernel": "6.8.0-45",
        "driver_version": "550.107.02",
    },
    "envelope": {
        "repeats": 3,
        "peak_vram_bytes": 21000000000,
        "hours_per_100_trials_median": 6.5,
        "determinism_check": "divergent",
        "failures": [],
    },
}


def lock(**overrides) -> dict:
    document = copy.deepcopy(FILLED)
    document.update(overrides)
    return document


class TemplateTests(unittest.TestCase):
    """The shipped form must not be mistakable for a filled one."""

    def test_the_template_is_valid_json(self):
        json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_the_unfilled_template_is_refused(self):
        with self.assertRaises(OrganismError):
            load_organism(TEMPLATE)

    def test_every_required_field_is_actually_checked(self):
        """A validator that checks the first field and stops looks identical to
        one that checks all of them, until the day a field is left blank."""
        for section, keys in (
            ("identity", FILLED["identity"]),
            ("configuration", FILLED["configuration"]),
            ("hardware", FILLED["hardware"]),
        ):
            for key in keys:
                if key == "sampling":
                    continue
                with self.subTest(field=f"{section}.{key}"):
                    document = copy.deepcopy(FILLED)
                    document[section][key] = "TODO"
                    with self.assertRaises(OrganismError):
                        OrganismLock(document)

    def test_every_sampling_field_is_checked(self):
        for key in FILLED["configuration"]["sampling"]:
            with self.subTest(field=key):
                document = copy.deepcopy(FILLED)
                document["configuration"]["sampling"][key] = None
                with self.assertRaises(OrganismError):
                    OrganismLock(document)

    def test_a_missing_field_is_refused_not_defaulted(self):
        document = copy.deepcopy(FILLED)
        del document["identity"]["model_sha256"]
        with self.assertRaises(OrganismError):
            OrganismLock(document)

    def test_a_missing_section_is_refused(self):
        for section in ("identity", "configuration", "hardware"):
            with self.subTest(section=section):
                document = copy.deepcopy(FILLED)
                del document[section]
                with self.assertRaises(OrganismError):
                    OrganismLock(document)


class FingerprintTests(unittest.TestCase):
    def test_a_filled_lock_fingerprints(self):
        digest = OrganismLock(FILLED).fingerprint
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(character in "0123456789abcdef" for character in digest))

    def test_key_order_does_not_change_the_fingerprint(self):
        """Canonical where it must be: a re-serialized lock file is the same
        organism, and a fingerprint that disagreed would split one machine's
        receipts into two pools for no reason."""
        shuffled = json.loads(json.dumps(FILLED))
        shuffled["identity"] = dict(reversed(list(shuffled["identity"].items())))
        self.assertEqual(OrganismLock(shuffled).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_quantization_changes_the_fingerprint(self):
        other = copy.deepcopy(FILLED)
        other["identity"]["quantization"] = "Q4_K_M"
        self.assertNotEqual(OrganismLock(other).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_context_cap_changes_the_fingerprint(self):
        other = copy.deepcopy(FILLED)
        other["configuration"]["context_cap"] = 16384
        self.assertNotEqual(OrganismLock(other).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_driver_version_changes_the_fingerprint(self):
        other = copy.deepcopy(FILLED)
        other["hardware"]["driver_version"] = "555.00.00"
        self.assertNotEqual(OrganismLock(other).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_the_observed_envelope_does_not_change_the_fingerprint(self):
        """Peak memory is an observation about the organism, not part of what it
        is. If it were hashed, the same machine would fingerprint differently on
        every probe and nothing could ever be pooled."""
        other = copy.deepcopy(FILLED)
        other["envelope"]["peak_vram_bytes"] = 1
        other["envelope"]["determinism_check"] = "identical"
        self.assertEqual(OrganismLock(other).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_the_version_is_inside_the_hashed_payload(self):
        other = copy.deepcopy(FILLED)
        other["organism_version"] = ORGANISM_VERSION + 1
        self.assertNotEqual(OrganismLock(other).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_a_bad_version_is_refused(self):
        for bad in (0, -1, "1", None, 1.0, True):
            with self.subTest(version=bad):
                with self.assertRaises(OrganismError):
                    OrganismLock(lock(organism_version=bad))


class LoadingTests(unittest.TestCase):
    def _write(self, document) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(document, handle)
        handle.close()
        return Path(handle.name)

    def test_a_filled_file_round_trips(self):
        path = self._write(FILLED)
        self.assertEqual(load_organism(path).fingerprint, OrganismLock(FILLED).fingerprint)

    def test_malformed_json_names_the_file(self):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        handle.write("{not json")
        handle.close()
        with self.assertRaises(OrganismError):
            load_organism(handle.name)

    def test_the_receipt_block_carries_the_fingerprint(self):
        path = self._write(FILLED)
        block = organism_fields(path)
        self.assertEqual(block["organism_fingerprint"], OrganismLock(FILLED).fingerprint)
        self.assertEqual(block["organism_quantization"], "Q8_0")
        self.assertEqual(block["organism_context_cap"], 32768)


class VerificationTests(unittest.TestCase):
    """A later reader checks the digest rather than trusting the writer."""

    def test_a_matching_block_verifies(self):
        held = OrganismLock(FILLED)
        self.assertTrue(verify_organism(held.as_receipt_block(), held))

    def test_a_lock_edited_after_the_fact_fails_verification(self):
        block = OrganismLock(FILLED).as_receipt_block()
        edited = copy.deepcopy(FILLED)
        edited["configuration"]["context_cap"] = 8192
        self.assertFalse(verify_organism(block, OrganismLock(edited)))

    def test_malformed_blocks_return_false_rather_than_raising(self):
        held = OrganismLock(FILLED)
        for block in ({}, {"organism_fingerprint": "x"}, {"organism_version": "one"}):
            with self.subTest(block=block):
                self.assertFalse(verify_organism(block, held))


class ProtocolTests(unittest.TestCase):
    """M-1 has to be executable, not descriptive."""

    def _protocol(self) -> str:
        return PROTOCOL.read_text(encoding="utf-8")

    def test_the_protocol_exists_and_names_its_output(self):
        text = self._protocol()
        self.assertIn("ORGANISM.lock.json", text)
        self.assertIn("organism_fingerprint", text)

    def test_it_separates_what_varies_from_what_is_held_constant(self):
        text = self._protocol()
        self.assertIn("## What is varied", text)
        self.assertIn("## What is held constant", text)

    def test_it_defines_stability_before_the_probe_runs(self):
        """Otherwise 'stable' is decided by looking at the numbers obtained."""
        text = self._protocol()
        self.assertIn("## What counts as stable", text)
        for criterion in ("offload transition", "truncation", "coefficient of variation"):
            with self.subTest(criterion=criterion):
                self.assertIn(criterion, text.lower())

    def test_hours_per_100_trials_is_derived_from_wall_clock_not_token_rate(self):
        text = self._protocol()
        self.assertIn("Hours per 100 trials", text)
        self.assertIn("never from token rates", text)

    def test_an_unstable_result_is_an_outcome_rather_than_a_retry(self):
        text = self._protocol()
        self.assertIn("The pilot does not run.", text)
        self.assertIn("Lowering the stability bar", text)

    def test_the_probe_set_is_excluded_from_the_pilot(self):
        """Tuning on tasks the pilot will score is selection on the outcome."""
        self.assertIn("explicitly excluded from PILOT-0001", self._protocol())


if __name__ == "__main__":
    unittest.main()
