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

from howdo.context import complete_onboarding, ensure_context, set_signals  # noqa: E402
from howdo.signal import (  # noqa: E402
    SIGNAL_BASENAME,
    TOOL_PATH_KEYS,
    SIGNAL_VERSION,
    STAGES,
    Signal,
    SignalError,
    append,
    read,
    read_header,
    resolve_signal_log,
    signal_from_header,
    written_path,
)

HOOK = PAYLOAD / "bin" / "howdo-signal"


def _clean_env() -> dict:
    """Strip the variables an enclosing session sets, which would otherwise
    point the hook at a different store or a different runtime."""
    environment = dict(os.environ)
    for name in ("HOWDO_CONTEXT", "HOWDO_SIGNALS", "CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_ROOT"):
        environment.pop(name, None)
    return environment


def _form(text: str):
    """Form a signal with the fields the hook always supplies."""
    return signal_from_header(text, path="a.md", tool="Write", recorded_at=0.0)


def _signal(**overrides) -> Signal:
    fields = {"operation": "op", "stage": "do", "path": "a.md",
              "tool": "Write", "recorded_at": 0.0}
    fields.update(overrides)
    return Signal(**fields)

HEADER = """---
howdo_operation: {operation}
howdo_stage: {stage}
---

body
"""


class HeaderTests(unittest.TestCase):
    """The header is the model's half of the pair."""

    def test_it_reads_the_two_fields_it_contracts_for(self):
        signal = _form(HEADER.format(operation="map the call site", stage="map"))
        self.assertEqual(signal.operation, "map the call site")
        self.assertEqual(signal.stage, "map")

    def test_a_file_with_no_header_is_not_an_error(self):
        """Most files a session writes have nothing to do with How Do.

        A hook that raised on each of them would be unusable, so the absence of
        a header is the ordinary case and returns nothing at all.
        """
        for text in ("", "just some code\n", "# a heading\n\nprose\n"):
            with self.subTest(text=text[:20]):
                self.assertIsNone(_form(text))

    def test_a_header_without_an_operation_declares_nothing(self):
        self.assertIsNone(_form("---\nhowdo_stage: map\n---\n"))

    def test_a_stage_outside_the_loop_is_refused(self):
        """The loop is the fixed shell, so an unknown stage is a typo.

        Accepting it would put a value in the log that no projection can ever
        interpret, which is worse than not recording the operation at all.
        """
        with self.assertRaises(SignalError):
            _form(HEADER.format(operation="x", stage="ponder"))

    def test_every_loop_stage_is_accepted(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                signal = _form(HEADER.format(operation="x", stage=stage.upper()))
                self.assertEqual(signal.stage, stage)

    def test_quotes_around_a_value_are_not_part_of_it(self):
        header = '---\nhowdo_operation: "map it"\nhowdo_stage: \'map\'\n---\n'
        signal = _form(header)
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
                append(_signal(operation=f"op{i}"), log)
            recorded = list(read(log))
            self.assertEqual([r["operation"] for r in recorded], ["op0", "op1", "op2"])

    def test_a_truncated_line_does_not_destroy_the_history(self):
        """Hooks append on machines we do not control. One interrupted write
        must not make every earlier signal unreadable."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / SIGNAL_BASENAME
            append(_signal(operation="first", stage="map"), log)
            with log.open("a", encoding="utf-8") as handle:
                handle.write('{"operation":"half-writ\n')
            append(_signal(operation="third"), log)
            self.assertEqual([r["operation"] for r in read(log)], ["first", "third"])

    def test_a_line_from_another_dialect_is_skipped(self):
        """Without a version in the line, the first format change makes every
        earlier line ambiguous -- and malformed-tolerant reading hides it."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / SIGNAL_BASENAME
            append(_signal(operation="known"), log)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"v": SIGNAL_VERSION + 1, "operation": "future"}) + "\n")
            self.assertEqual([r["operation"] for r in read(log)], ["known"])

    def test_reading_an_absent_log_yields_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list(read(Path(tmp) / "absent.jsonl")), [])

    def test_the_log_sits_beside_the_store(self):
        log = resolve_signal_log(context_path="/home/someone/.howdo/CONTEXT.md", env={})
        self.assertEqual(log, Path("/home/someone/.howdo") / SIGNAL_BASENAME)

    def test_a_log_inside_the_payload_is_refused(self):
        """`install.py --shared` legitimately puts the store in the payload.

        A log that followed it there would be deleted by the next update with
        no error raised -- the exact trap this module claims to avoid, which
        makes silence here the worst possible behaviour.
        """
        with self.assertRaises(SignalError):
            resolve_signal_log(context_path=PAYLOAD / "CONTEXT.md", env={})

    def test_an_override_is_honoured(self):
        log = resolve_signal_log(env={"HOWDO_SIGNALS": "/elsewhere/mine.jsonl"})
        self.assertEqual(log, Path("/elsewhere/mine.jsonl"))

    def test_a_projection_is_computed_rather_than_stored(self):
        """Counting is done by a reader. Nothing maintains a count on disk."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / SIGNAL_BASENAME
            for stage in ("map", "map", "check"):
                append(_signal(stage=stage), log)
            stages = [record["stage"] for record in read(log)]
            self.assertEqual(stages.count("map"), 2)
            self.assertEqual(stages.count("check"), 1)
            self.assertNotIn("count", log.read_text(encoding="utf-8"))


class HookTests(unittest.TestCase):
    """The hook is the half that does not take the model's word for it."""

    def _store(self, tmp, *, switched_on: bool) -> Path:
        store = Path(tmp) / "CONTEXT.md"
        ensure_context(store, template=PAYLOAD / "CONTEXT.template.md")
        complete_onboarding(
            store, calibration_domain="a domain", representation_observation="an observation",
            landed_example="landed", rejected_example="rejected",
        )
        if switched_on:
            set_signals(store, on=True)
        return store

    def _fire(self, store: Path, *, tool: str, written: Path) -> None:
        payload = json.dumps({
            "tool_name": tool,
            "session_id": "session-under-test",
            "tool_input": {"file_path": str(written)},
        })
        subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True,
            env={**_clean_env(), "HOWDO_CONTEXT": str(store)},
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
            self.assertFalse(resolve_signal_log(context_path=store, env={}).exists(),
                             "the hook recorded without being switched on")

    def test_switching_it_on_records_the_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Write", written=self._artifact(tmp))
            recorded = list(read(resolve_signal_log(context_path=store, env={})))
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
            self.assertFalse(resolve_signal_log(context_path=store, env={}).exists())

    def test_a_tool_that_writes_nothing_is_not_recorded(self):
        """A signal is about an artifact existing. A read has no artifact."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Read", written=self._artifact(tmp))
            self.assertFalse(resolve_signal_log(context_path=store, env={}).exists())

    def test_a_declaration_with_no_artifact_records_nothing(self):
        """The hook's whole job is confirming the file landed. If the path the
        tool reported is not there, the absence is the observation."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Write", written=Path(tmp) / "never-written.md")
            self.assertFalse(resolve_signal_log(context_path=store, env={}).exists())

    def test_a_bad_header_costs_the_session_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, switched_on=True)
            self._fire(store, tool="Write", written=self._artifact(tmp, stage="ponder"))
            self.assertFalse(resolve_signal_log(context_path=store, env={}).exists())

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

    def test_every_wired_tool_can_actually_fire(self):
        """The defect this catches: a tool wired up and permanently silent.

        The writing tools disagree about which payload key holds the path.
        NotebookEdit reports ``notebook_path`` where the others report
        ``file_path``, so a hook that assumed one shape would sit in the
        matcher recording nothing, forever, with no error anywhere.
        """
        for tool, key in TOOL_PATH_KEYS.items():
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as tmp:
                store = self._store(tmp, switched_on=True)
                written = Path(tmp) / "artifact.md"
                written.write_text(HEADER.format(operation="op", stage="do"),
                                   encoding="utf-8")
                payload = json.dumps({
                    "tool_name": tool, "session_id": "s",
                    "tool_input": {key: str(written)},
                })
                subprocess.run([sys.executable, str(HOOK)], input=payload,
                               capture_output=True, text=True,
                               env={**_clean_env(), "HOWDO_CONTEXT": str(store)})
                recorded = list(read(resolve_signal_log(context_path=store, env={})))
                self.assertEqual(len(recorded), 1, f"{tool} recorded nothing")
                self.assertEqual(recorded[0]["tool"], tool)

    def test_the_matcher_and_the_table_cannot_drift_apart(self):
        """Wired in one place and not the other is silent in both directions."""
        config = json.loads((PAYLOAD / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        matched = set()
        for entry in config["hooks"]["PostToolUse"]:
            matched.update(entry.get("matcher", "").split("|"))
        self.assertEqual(matched - {""}, set(TOOL_PATH_KEYS))

    def test_a_store_that_may_not_be_recorded_against_is_not(self):
        """`SKILL.md` names treating a declined context as learned context.

        Accumulating against one is that, and a template is not a lineage at
        all -- so the switch alone is not enough to authorise recording.
        """
        from howdo.context import decline_onboarding  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "CONTEXT.md"
            ensure_context(store, template=PAYLOAD / "CONTEXT.template.md")
            set_signals(store, on=True)
            decline_onboarding(store)
            self._fire(store, tool="Write", written=self._artifact(tmp))
            self.assertFalse(resolve_signal_log(context_path=store, env={}).exists(),
                             "recorded against a declined context")

    def test_the_shipped_template_is_never_recorded_against(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._fire(PAYLOAD / "CONTEXT.template.md", tool="Write",
                       written=self._artifact(tmp))
            self.assertFalse((PAYLOAD / SIGNAL_BASENAME).exists(),
                             "a log appeared inside the payload")

    def test_a_windows_shim_ships_beside_the_hook(self):
        """The hook is invoked by path from hooks.json. Without this it simply
        does not run on Windows -- the sibling executable has had one since it
        shipped, and this one was written without."""
        shim = PAYLOAD / "bin" / "howdo-signal.cmd"
        self.assertTrue(shim.is_file(), "no Windows shim beside bin/howdo-signal")
        self.assertIn("howdo-signal", shim.read_text(encoding="utf-8"))

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
