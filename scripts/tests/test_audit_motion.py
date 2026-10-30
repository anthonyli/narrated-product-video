import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "audit_motion.py"
SPEC = importlib.util.spec_from_file_location("audit_motion", SCRIPT)
motion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(motion)


def action(name, kind, start, end):
    return {"id": name, "kind": kind, "start": start, "end": end}


def plan(actions=None, **extra):
    return {"duration": 3, "fps": 30, "actions": actions or [], **extra}


class MotionAuditTests(unittest.TestCase):
    def test_interval_union_merges_nested_overlap_and_touching(self):
        self.assertEqual(motion.merge_intervals([(2, 4), (0, 1), (1, 3), (5, 6), (2.5, 2.7)]),
                         [(0, 4), (5, 6)])

    def test_overlap_does_not_create_false_gap(self):
        result = motion.audit(plan([action("a", "focus", 0, 2), action("b", "focus", 1, 3)]))
        self.assertNotIn("idle-gap", [warning["code"] for warning in result["warnings"]])

    def test_camera_drift_does_not_hide_idle_gap(self):
        result = motion.audit(plan([action("drift", "camera", 0, 3)]))
        self.assertEqual([(w["code"], w["start"], w["end"]) for w in result["warnings"]],
                         [("idle-gap", 0, 3)])

    def test_explained_hold_covers_reading_time(self):
        result = motion.audit(plan([action("entry", "enter", 0, .3)],
                                   holds=[{"start": .3, "end": 3, "reason": "Read comparison labels"}]))
        self.assertEqual(result["warnings"], [])
        self.assertFalse(result["qualityAssessed"])

    def test_empty_hold_reason_is_not_a_waiver(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            motion.audit(plan(holds=[{"start": 0, "end": 3, "reason": "  "}]))

    def test_thresholds_and_cli_override_precedence(self):
        source = plan([action("wipe", "transition", 0, .4), action("in", "enter", .4, .9),
                       action("layout", "reflow", .9, 1.7)],
                      holds=[{"start": 1.7, "end": 3, "reason": "Narration explains result"}])
        self.assertEqual([w["code"] for w in motion.audit(source)["warnings"]],
                         ["long-transition", "long-enter", "long-reflow"])
        source["policy"] = {"transition_max": .5}
        self.assertNotIn("long-transition", [w["code"] for w in motion.audit(source)["warnings"]])
        self.assertIn("long-transition", [w["code"] for w in motion.audit(source, {"transition_max": .3})["warnings"]])

    def test_threshold_equality_is_not_warned(self):
        result = motion.audit(plan([action("wipe", "transition", 0, .35),
                                   action("in", "enter", .35, .8),
                                   action("layout", "reflow", .8, 1.5)],
                                  holds=[{"start": 1.5, "end": 3, "reason": "Read"}]))
        self.assertEqual(result["warnings"], [])

    def test_transition_samples_clamped_deduplicated_and_sorted(self):
        result = motion.audit(plan([action("a", "transition", 0, .2),
                                   action("b", "transition", 2.8, 3)]))
        frames = [sample["frame"] for sample in result["frameSamples"]]
        self.assertEqual(frames, sorted(set(frames)))
        self.assertEqual(frames[0], 0)
        self.assertEqual(frames[-1], 89)
        self.assertTrue(all(0 <= sample["time"] < 3 for sample in result["frameSamples"]))
        self.assertEqual(len(result["frameSamples"][0]["reasons"]), 2)

    def test_internal_transition_samples_straddle_boundary(self):
        result = motion.audit(plan([action("wipe", "transition", 1, 1.2)]))
        self.assertEqual([s["frame"] for s in result["frameSamples"]], [29, 30, 33, 35, 36])

    def test_long_focus_and_exit_warn_even_when_covering_full_video(self):
        for kind, threshold in [("focus", .55), ("exit", .35)]:
            with self.subTest(kind=kind):
                result = motion.audit(plan([action("whole-video", kind, 0, 10)], duration=10))
                self.assertEqual([w["code"] for w in result["warnings"]], [f"long-{kind}"])
                self.assertEqual(result["warnings"][0]["threshold"], threshold)
                self.assertEqual([s["frame"] for s in result["frameSamples"]], [0, 150, 299])
                self.assertFalse(result["qualityAssessed"])

    def test_focus_and_exit_thresholds_are_configurable(self):
        for kind, threshold in [("focus", .55), ("exit", .35)]:
            with self.subTest(kind=kind):
                source = plan([action("action", kind, 0, threshold)], duration=threshold)
                self.assertEqual(motion.audit(source)["warnings"], [])
                source["policy"] = {f"{kind}_max": .1}
                self.assertEqual(motion.audit(source)["warnings"][0]["code"], f"long-{kind}")
                self.assertEqual(motion.audit(source, {f"{kind}_max": 1})["warnings"], [])

    def test_every_primary_action_gets_boundary_samples_even_without_warning(self):
        kinds = ["transition", "enter", "reflow", "focus", "exit", "camera"]
        source = plan([action(kind, kind, .1, .2) for kind in kinds], duration=.3)
        result = motion.audit(source)
        self.assertEqual(result["warnings"], [])
        sampled_actions = {reason["action"] for sample in result["frameSamples"]
                           for reason in sample["reasons"]}
        self.assertEqual(sampled_actions, set(kinds) - {"camera"})
        self.assertEqual([s["frame"] for s in result["frameSamples"]], [2, 3, 4, 5, 6])

    def test_invalid_numbers_are_rejected(self):
        for value in [True, False, math.nan, math.inf, -1, "3", None, 10 ** 1000]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                motion.audit(plan(duration=value))
        for value in [True, math.nan, math.inf, -1]:
            with self.subTest(start=value), self.assertRaises(ValueError):
                motion.audit(plan([action("bad", "enter", value, 1)]))
        for value in [True, 0, 29.97]:
            with self.subTest(fps=value), self.assertRaises(ValueError):
                motion.audit(plan(fps=value))

    def test_bad_intervals_ids_and_kinds_are_rejected(self):
        invalid = [
            [action("bad", "enter", 1, 1)], [action("bad", "enter", 0, 4)],
            [action(" ", "enter", 0, 1)], [action("bad", "float", 0, 1)],
            [action("same", "enter", 0, 1), action(" same ", "exit", 1, 2)],
        ]
        for actions in invalid:
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                motion.audit(plan(actions))

    def test_invalid_policies_are_rejected(self):
        for policy in [{"unknown": 1}, {"gap_max": True}, {"gap_max": 0},
                       {"gap_max": math.nan}, []]:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                motion.audit(plan(policy=policy))

    def test_cli_preserves_input_and_existing_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "motion-plan.json"
            original = json.dumps(plan())
            source.write_text(original)
            output = root / "audit.json"
            command = [sys.executable, str(SCRIPT), str(source), "--output", str(output), "--gap-max", "5"]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            data = output.read_text()
            self.assertEqual(json.loads(data)["warnings"], [])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_text(), data)
            self.assertEqual(source.read_text(), original)


if __name__ == "__main__":
    unittest.main()
