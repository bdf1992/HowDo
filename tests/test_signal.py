"""Signals are logged operations, so what is tested is what gets logged.

Two properties carry the design, and neither is a claim a document can hold.

The first is that recording is **off until a person turns it on**. An
observation surface that arrived by surprise would be the ambience `SKILL.md`
refuses; one somebody switched on is not. So the default is silence, and the
switch is the only thing that breaks it.

The second is that a signal needs **both halves**: the model declares what an
operation was in the artifact's header, and the hook confirms from outside the
model's context that the artifact landed. `SKILL.md` refuses to treat model
output as independent evidence of its own success, so a declaration nobody
checked would not be admissible evidence of anything.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))

from howdo.context import ensure_context  # noqa: E402
from howdo.signal import (  # noqa: E402
    SIGNAL_BASENAME,
    STAGES,
    Signal,
    SignalError,
    append,
    by_stage,
    read,
    read_header,
    signal_from_header,
    signal_log_path,
)

HOOK = PAYLOAD / "bin" / "howdo-signal"

HEADER = """---
howdo_operation: {operation}
howdo_stage: {stage}
---

body
"""


class HeaderTests(unittest.TestCase):
    """The header is the model's half of the pair."""

    def test_it_reads_the_two_fields_it_contracts_for(self):
        signal = signal_from_header(
            HEADER.format(operation="map the call site", stage="map"), path="a.md"
        )
        self.assertEqual(signal.operation, "map the call site")
        self.assertEqual(signal.stage, "map")

    def test_a_file_with_no_header_is_not_an_error(self):
        """Most files a session writes have nothing to do with How Do.

        A hook that raised on each of them would be unusable, so the absence of
        a header is the ordinary case and returns nothing at all.
        """
        for text in ("", "just some code\n", "# a heading\n\nprose\n"):
            with self.subTest(text=text[:20]):
                self.assertIsNone(signal_from_header(text, path="a.md"))

    def test_a_header_without_an_operation_declares_nothing(self):
        self.assertIsNone(signal_from_header("---\nhowdo_stage: map\n---\n", path="a.md"))

    def test_a_stage_outside_the_loop_is_refused(self):
        """The loop is the fixed shell, so an unknown stage is a typo.

        Accepting it would put a value in the log that no projection can ever
        interpret, which is worse than not recording the operation at all.
        """
        with self.assertRaises(SignalError):
            signal_from_header(
                HEADER.format(operation="x", stage="ponder"), path="a.md"
            )

    def test_every_loop_stage_is_accepted(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                signal = signal_from_header(
                    HEADER.format(operation="x", stage=stage.upper()), path="a.md"
                )
                self.assertEqual(signal.stage, stage)

    def test_quotes_around_a_value_are_not_part_of_it(self):
        header = '---\nhowdo_operation: "map it"\nhowdo_stage: \'map\'\n---\n'
        signal = signal_from_header(header, path="a.md")
        self.assertEqual(signal.operation, "map it")
        self.assertEqual(signal.stage, "map")

    def test_a_header_is_only_a_header_at_the_top(self):
        """A fenced block further down a document is content, not metadata."""
        text = "prose first\n\n---\nhowdo_operation: x\nhowdo_stage: map\n---\n"
        self.assertEqual(read_header(text), {})


class LogTests(unittest.TestCase):
    """Append-only, because ordering that cannot be forged is the useful part."""

    def test_appending_never_rewrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / SIGNAL_BASENAME
            for i in range(3):
                append(Signal(operation=f"op{i}", stage="do", path="a.md"), log)
            recorded = list(read(log))
            self.assertEqual([r["operation"] for r in recorded], ["op0", "op1", "op2"])

    def test_a_truncated_line_does_not_destroy_the_history(self):
        """Hooks append on machines we do not control. One interrupted write
        must not make every earlier signal unreadable."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / SIGNAL_BASENAME
            append(Signal(operation="first", stage="map", path="a.md"), log)
            with log.open("a", encoding="utf-8") as handle:
                handle.write('{"operation":"half-writ\n')
            append(Signal(operation="third", stage="do", path="a.md"), log)
            self.assertEqual([r["operation"] for r in read(log)], ["first", "third"])

    def test_reading_an_absent_log_yields_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list(read(Path(tmp) / "absent.jsonl")), [])

    def test_the_log_sits_beside_the_store_not_inside_the_payload(self):
        """The payload is replaced on update and would discard these with no
        error raised -- the same trap the durable context is kept out of."""
        log = signal_log_path("/home/someone/.howdo/CONTEXT.md")
        self.assertEqual(log, Path("/home/someone/.howdo") / SIGNAL_BASENAME)

    def test_a_projection_is_computed_rather_than_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / SIGNAL_BASENAME
            for stage in ("map", "map", "check"):
                append(Signal(operation="x", stage=stage, path="a.md"), log)
            counts = by_stage(log)
            self.assertEqual(counts["map"], 2)
            self.assertEqual(counts["check"], 1)
            self.assertEqual(counts["do"], 0)
            self.assertNotIn("count", log.read_text(encoding="utf-8"))


class HookTests(unittest.TestCase):
    """The hook is the half that does not take the model's word for it."""

    def _store(self, tmp, *, switched_on: bool) -> Path:
        store = Path(tmp) / "CONTEXT.md"
        ensure_context(store, template=PAYLOAD / "CONTEXT.template.md")
        if switched_on:
            text = store.read_text(encoding="utf-8")
            store.write_text(
                text.replace("howdo_context:", "automated_onboarding: on\nhowdo_context:", 1),
                encoding="utf-8",
            )
        return store

    def _fire(self, store: Path, *, tool: str, written: Path) -> None:
        payload = json.dumps({
            "tool_name": tool,
            "session_id": "session-under-test",
            "tool_input": {"file_path": str(written)},
        })
        subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True,
            env={**os.environ, "HOWDO_CONTEXT": str(store)},
        )

    def _artifact(self, tmp, *, stage: str = "map") -> Path:
        written = Path(tmp) / "artifact.md"
        written.write_text(HEADER.format(operation="an operation", stage=stage),
                           encoding="utf-8")
        return written

    def test_nothing_is_recorded_until_a_person_switches_it_on(self):
        """The property that makes an observation surface admissible at all."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=False)
            self._fire(store, tool="Write", written=self._artifact(tmp))
            self.assertFalse(signal_log_path(store).exists(),
                             "the hook recorded without being switched on")

    def test_switching_it_on_records_the_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Write", written=self._artifact(tmp))
            recorded = list(read(signal_log_path(store)))
            self.assertEqual(len(recorded), 1)
            self.assertEqual(recorded[0]["operation"], "an operation")
            self.assertEqual(recorded[0]["stage"], "map")
            self.assertEqual(recorded[0]["tool"], "Write")
            self.assertEqual(recorded[0]["session"], "session-under-test")

    def test_a_file_the_model_did_not_declare_is_not_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            plain = Path(tmp) / "plain.py"
            plain.write_text("x = 1\n", encoding="utf-8")
            self._fire(store, tool="Write", written=plain)
            self.assertFalse(signal_log_path(store).exists())

    def test_a_tool_that_writes_nothing_is_not_recorded(self):
        """A signal is about an artifact existing. A read has no artifact."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Read", written=self._artifact(tmp))
            self.assertFalse(signal_log_path(store).exists())

    def test_a_declaration_with_no_artifact_records_nothing(self):
        """The hook's whole job is confirming the file landed. If the path the
        tool reported is not there, the absence is the observation."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Write", written=Path(tmp) / "never-written.md")
            self.assertFalse(signal_log_path(store).exists())

    def test_a_bad_header_costs_the_session_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Write", written=self._artifact(tmp, stage="ponder"))
            self.assertFalse(signal_log_path(store).exists())

    def test_garbage_on_stdin_costs_the_session_nothing(self):
        """This runs as a side errand on someone else's tool call. Every
        failure has to be free to them."""
        for payload in ("", "not json", "[]", "null"):
            with self.subTest(payload=payload):
                result = subprocess.run(
                    [sys.executable, str(HOOK)], input=payload,
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_hook_is_wired_to_the_tools_that_write(self):
        config = json.loads((PAYLOAD / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entries = config["hooks"]["PostToolUse"]
        commands = [h["command"] for entry in entries for h in entry["hooks"]]
        self.assertTrue(any("howdo-signal" in c for c in commands))
        self.assertTrue(any("${CLAUDE_PLUGIN_ROOT}" in c for c in commands),
                        "the hook hard-codes a path that moves on every update")
        matchers = " ".join(entry.get("matcher", "") for entry in entries)
        for tool in ("Write", "Edit"):
            self.assertIn(tool, matchers)

    def test_the_executable_ships_runnable(self):
        self.assertTrue(HOOK.is_file())
        self.assertTrue(os.access(HOOK, os.X_OK), "bin/howdo-signal is not executable")


if __name__ == "__main__":
    unittest.main()
