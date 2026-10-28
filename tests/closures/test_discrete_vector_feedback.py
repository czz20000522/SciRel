from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from scirel.closures import simulate_discrete_vector_feedback

ROOT = Path(__file__).parents[1] / "fixtures" / "closures" / "discrete_vector_feedback"
EVIDENCE = ROOT / "evidence"


class NeutralFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = json.loads((EVIDENCE / "fixtures" / "feedback-input.json").read_text(encoding="utf-8"))
        cls.controller = json.loads((EVIDENCE / "source-defaults.json").read_text(encoding="utf-8"))
        cls.source = json.loads((EVIDENCE / "runs" / "source-001" / "result.json").read_text(encoding="utf-8"))
        cls.source_trace = json.loads((EVIDENCE / "runs" / "source-001" / "state-trace.json").read_text(encoding="utf-8"))
        cls.replay = json.loads((EVIDENCE / "runs" / "replay-001" / "result.json").read_text(encoding="utf-8"))

    def test_fixture_shapes_and_source_replay_agree(self):
        self.assertEqual(self.source, self.replay)
        result = simulate_discrete_vector_feedback(self.inputs, self.controller)
        self.assertEqual(result["schema"], "magnetic-error-current-feedback-discrete")
        self.assertEqual(len(result["time_s"]), 121)
        self.assertEqual(np.asarray(result["values"]["total_current_A"]).shape, (121, 11))
        self.assertEqual(np.asarray(result["values"]["feedback_current_A"]).shape, (121, 11))
        self.assertEqual(np.asarray(result["values"]["pid_components"]).shape, (121, 30))
        self.assertEqual(np.asarray(result["values"]["error_T"]).shape, (121, 10))

    def test_reimplementation_matches_saved_source_trace(self):
        result = simulate_discrete_vector_feedback(self.inputs, self.controller)
        for key in result["values"]:
            np.testing.assert_allclose(
                np.asarray(result["values"][key], dtype=float),
                np.asarray(self.source["values"][key], dtype=float),
                rtol=2e-12,
                atol=2e-9,
            )
        for key in self.source_trace:
            if key in {"execution_kind", "native_simulink_execution", "scientific_acceptance", "runtime_octave_version"}:
                continue
            if key == "reset_at_sample":
                self.assertEqual(result["state_trace"][key], self.source_trace[key])
            else:
                np.testing.assert_allclose(
                    np.asarray(result["state_trace"][key], dtype=float),
                    np.asarray(self.source_trace[key], dtype=float),
                    rtol=2e-12,
                    atol=2e-12,
                )

    def test_disabled_hold_and_rising_reset_are_observable(self):
        result = simulate_discrete_vector_feedback(self.inputs, self.controller)
        values = result["values"]
        trace = result["state_trace"]
        self.assertEqual(trace["reset_at_sample"], [i in (0, 55, 105) for i in range(121)])
        self.assertEqual(values["total_current_A"][40], self.inputs["signals"]["feedforward_current_A"][40])
        self.assertEqual(values["total_current_A"][54], self.inputs["signals"]["feedforward_current_A"][54])
        self.assertEqual(values["feedback_current_A"][40], values["feedback_current_A"][39])
        self.assertEqual(trace["pre_filter_state"][55], [0.0] * 10)
        self.assertEqual(trace["pre_integrator_state"][105], [0.0] * 10)

    def test_rejects_nonbinary_enable(self):
        inputs = json.loads(json.dumps(self.inputs))
        inputs["signals"]["enable"][1] = 2
        with self.assertRaisesRegex(ValueError, "binary"):
            simulate_discrete_vector_feedback(inputs, self.controller)


if __name__ == "__main__":
    unittest.main()
