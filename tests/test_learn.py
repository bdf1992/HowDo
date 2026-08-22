"""What the record supports, and the line between evidence and self-report.

The reader was written before the record was finished, on purpose. A producer
with no consumer records whatever was easy rather than whatever was wanted, and
nothing catches the difference -- so these tests are as much about what the
reader *refuses* to conclude as what it concludes.

One rule carries the design: a value the model authored is never counted as
evidence for itself. It earns its place only when something on disk can
contradict it.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))

from howdo.learn import (  # noqa: E402
    ANCHOR,
    BUILD_DIRECTION,
    DECLARED,
    DIMENSIONS,
    OBSERVED,
    UNDERSTOOD,
    observe,
)
from howdo.signal import Signal, append  # noqa: E402

AGENT = PAYLOAD / "agents" / "analyst.md"


def _flatten(text: str) -> str:
    """Lowercase, drop emphasis, collapse whitespace.

    These are contracts about what the agent is told, not about where the
    lines wrap. Asserting on raw text makes a reflow look like a broken
    promise -- which it did, the first time these ran.
    """
    return re.sub(r"\s+", " ", text.replace("*", "")).lower()


def _log(tmp, *signals: Signal) -> Path:
    log = Path(tmp) / "signals.jsonl"
    for signal in signals:
        append(signal, log)
    return log


def _s(stage: str, path: str = "a.md", *, at: float = 0.0, **extra) -> Signal:
    fields = {"operation": "an operation", "stage": stage, "path": path,
              "tool": "Write", "recorded_at": at, "session": "s1"}
    fields.update(extra)
    return Signal(**fields)


class EvidenceGradeTests(unittest.TestCase):
    """The distinction the whole module exists to hold."""

    def test_a_rewrite_after_look_is_observed_evidence(self):
        """Look runs the test Check wrote. A file rewritten afterwards is that
        test failing, witnessed from outside rather than reported from inside."""
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("check"), _s("look", at=1), _s("do", at=2))
            found = [o for o in observe(log).observations if o.dimension == UNDERSTOOD]
            self.assertTrue(found)
            self.assertTrue(all(o.grade == OBSERVED for o in found))

    def test_the_models_own_verdict_is_never_evidence_on_its_own(self):
        """`held: yes` with nothing able to contradict it must not become a
        finding graded observed. That would be the model certifying itself."""
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("look", held=True))
            for observation in observe(log).observations:
                if observation.dimension == ANCHOR:
                    continue
                self.assertIn("declared outcome compared", observation.basis,
                              "a self-reported verdict became a finding unchallenged")

    def test_a_verdict_the_disk_contradicts_is_counted(self):
        """The one use for a declared value: something can prove it wrong."""
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("look", held=True), _s("do", at=1))
            readings = [o.reading for o in observe(log).observations]
            self.assertTrue(any("1 of 1" in r and "rewritten" in r for r in readings),
                            f"the contradiction was not caught: {readings}")

    def test_a_verdict_the_disk_supports_is_also_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("look", held=True))
            readings = [o.reading for o in observe(log).observations]
            self.assertTrue(any("survived" in r for r in readings), readings)

    def test_a_domain_is_reported_as_declared_not_observed(self):
        """Nothing on disk shows whether a domain is one they can judge an
        explanation in, and that is the only property that makes it an anchor."""
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("do", domain="http clients"))
            anchors = [o for o in observe(log).observations if o.dimension == ANCHOR]
            self.assertTrue(anchors)
            self.assertTrue(all(o.grade == DECLARED for o in anchors))

    def test_one_use_of_a_shape_is_not_a_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("do", shape="instance-first"))
            shapes = [o for o in observe(log).observations if o.dimension == BUILD_DIRECTION]
            self.assertTrue(all(o.grade == DECLARED for o in shapes),
                            "a single observation was graded as evidence")


class GapTests(unittest.TestCase):
    """An unsupported reading must read as unsupported, not be omitted.

    Absent and unsupported look identical to whoever reads the report next, and
    they are not the same thing.
    """

    def test_a_bare_record_cannot_answer_any_of_the_four(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("map"), _s("do", at=1))
            gaps = {gap.dimension for gap in observe(log).gaps}
            self.assertEqual(gaps, set(DIMENSIONS),
                             "a record with no predictions claimed to answer something")

    def test_every_gap_names_what_would_close_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(tmp, _s("map"))
            for gap in observe(log).gaps:
                with self.subTest(dimension=gap.dimension):
                    self.assertTrue(gap.needs.strip(), "a gap with no remedy")
                    self.assertTrue(gap.why.strip(), "a gap with no reason")

    def test_recording_the_missing_datum_closes_its_gap(self):
        """The requirement lives in the consumer, so satisfying it must be
        enough -- no second list to update in the producer."""
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(
                tmp,
                _s("check", expects="at most 3 attempts", domain="http", shape="instance-first"),
                _s("look", at=1, held=True, domain="http", shape="instance-first"),
            )
            self.assertEqual(observe(log).gaps, (),
                             "a gap survived the datum that answers it")

    def test_an_empty_record_reports_gaps_rather_than_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            reading = observe(Path(tmp) / "absent.jsonl")
            self.assertEqual(reading.observations, ())
            self.assertEqual(len(reading.gaps), len(DIMENSIONS))


class DeclarationTests(unittest.TestCase):
    """The record only fills up if the skill is told to declare.

    Everything else here is machinery that works on data nobody produces
    unless `SKILL.md` asks for it, so the asking is a contract too.
    """

    def _skill(self) -> str:
        return _flatten((PAYLOAD / "SKILL.md").read_text(encoding="utf-8"))

    def test_the_skill_is_told_which_fields_to_declare(self):
        skill = self._skill()
        for field in ("howdo_operation", "howdo_stage", "howdo_expects",
                      "howdo_held", "howdo_domain", "howdo_shape"):
            with self.subTest(field=field):
                self.assertIn(field, skill, f"nothing ever writes {field}")

    def test_declaring_is_gated_on_the_switch(self):
        """An instruction to header every artefact regardless would make the
        record arrive whether or not anyone asked for it."""
        self.assertIn("signals: on", self._skill())
        self.assertIn("off unless the person set it", self._skill())

    def test_headers_are_scoped_to_artefacts_the_discipline_authors(self):
        """Putting bookkeeping in someone's source file is vandalism, and the
        vocabulary rule already says machinery is not what a person reads."""
        skill = self._skill()
        self.assertIn("artifacts this discipline authors", skill)
        self.assertIn("vandalism", skill)

    def test_the_declaration_is_named_as_a_claim_not_a_result(self):
        """A declaration nobody checked is the model grading itself. The skill
        has to say so where it asks for one, not only in a module docstring."""
        skill = self._skill()
        self.assertIn("your declaration is a claim", skill)
        self.assertIn("the file existing is the check", skill)

    def test_declaring_a_check_held_dishonestly_is_refused(self):
        refuses = self._skill()[self._skill().index("## refuses"):]
        self.assertIn("because the work should have worked", refuses)


class AnalystTests(unittest.TestCase):
    """The agent is the judgement half; what it must not do is the contract."""

    def _frontmatter(self) -> str:
        text = AGENT.read_text(encoding="utf-8")
        return text[3:text.index("\n---", 3)]

    def test_the_agent_ships(self):
        self.assertTrue(AGENT.is_file(), "agents/analyst.md is missing")
        self.assertIn("name: analyst", self._frontmatter())

    def test_it_cannot_write(self):
        """Settling context is a deliberate act somebody performs with a finding
        in hand. An analyst that could write would settle by accident."""
        tools = self._frontmatter()
        line = next(l for l in tools.splitlines() if l.startswith("tools:"))
        for forbidden in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            self.assertNotIn(forbidden, line, f"the analyst can {forbidden}")

    def test_it_is_told_it_did_not_do_the_work(self):
        """Independence is the property that makes its findings admissible, so
        it has to be stated rather than assumed from how it happens to be run."""
        body = _flatten(AGENT.read_text(encoding="utf-8"))
        self.assertIn("you did not see the reasoning", body)
        self.assertIn("its own success", body)

    def test_it_carries_the_grade_distinction_and_the_refusals(self):
        body = _flatten(AGENT.read_text(encoding="utf-8"))
        for required in ("observed", "declared", "never write", "visual learner",
                         "the gaps are half the report"):
            with self.subTest(required=required):
                self.assertIn(required, body)

    def test_it_is_addressed_by_the_plugin(self):
        sys.path.insert(0, str(ROOT))
        import install  # noqa: PLC0415

        self.assertIn("agents", install.PLUGIN_EXTRA,
                      "the agent is in the payload but no install path ships it")


if __name__ == "__main__":
    unittest.main()
