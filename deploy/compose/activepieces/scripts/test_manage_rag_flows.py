from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("manage-rag-flows.py")
SPEC = importlib.util.spec_from_file_location("manage_rag_flows", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)
BUNDLE = json.loads((SCRIPT.parents[1] / "flows" / "rag-orchestration-v1.json").read_text(encoding="utf-8"))


class FlowBundleTests(unittest.TestCase):
    def test_bundle_contains_five_policy_neutral_flows(self) -> None:
        self.assertEqual(5, len(BUNDLE["flows"]))
        self.assertFalse(BUNDLE["security"]["automaticApproval"])
        self.assertFalse(BUNDLE["security"]["rawSourceInFlowRun"])
        self.assertFalse(BUNDLE["security"]["credentialsInBundle"])

    def test_every_action_has_fail_closed_http_settings_and_correlation(self) -> None:
        for flow in BUNDLE["flows"]:
            trigger = module.build_trigger(flow, BUNDLE["gatewayBaseUrl"])
            action = trigger["nextAction"]
            count = 0
            while action:
                count += 1
                settings = action["settings"]["input"]
                self.assertEqual("continue_none", settings["failureMode"])
                self.assertIn("X-Correlation-Id", settings["headers"])
                self.assertIn("Idempotency-Key", settings["headers"])
                self.assertNotIn("Authorization", settings["headers"])
                action = action.get("nextAction")
            self.assertEqual(len(flow["operations"]), count)

    def test_review_flow_requires_human_reviewer_input(self) -> None:
        flow = next(item for item in BUNDLE["flows"] if item["route"] == "review")
        text = json.dumps(flow)
        self.assertIn("reviewer", text)
        self.assertIn("expectedCommit", text)
        self.assertNotIn("autoApprove", text)


if __name__ == "__main__":
    unittest.main()
