from __future__ import annotations

import unittest
from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))
from local_worker.telemetry import qwen_harness_telemetry


class TelemetryTests(unittest.TestCase):
    def test_nested_tool_use_and_reported_statistics_are_compacted(self):
        records = [{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "read_file"},
            {"nested": [{"type": "tool_use", "name": "grep_search"}]},
        ]}}, {"type": "result", "subtype": "success", "result": "done",
              "stats": {"tools": {"totalCalls": 3}, "models": {"local": {"tokens": {"total": 10}}}}}]
        result = qwen_harness_telemetry(records)
        self.assertEqual(result["tool_calls"], 3)
        self.assertEqual(result["tool_names"], ["grep_search", "read_file"])
        self.assertEqual(result["stats"]["models"]["local"]["tokens"]["total"], 10)

    def test_budget_and_preemption_terminal_reasons_are_normalized(self):
        self.assertTrue(qwen_harness_telemetry([{"type": "result", "subtype": "max tool budget"}])["budget_exhausted"])
        self.assertTrue(qwen_harness_telemetry([{"type": "result", "subtype": "preempted"}])["preempted"])

if __name__ == "__main__": unittest.main()
