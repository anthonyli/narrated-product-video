#!/usr/bin/env python3
"""Audit a motion-plan QA record; this is not a renderer timeline schema.

Input: {duration, fps, actions: [{id, kind, start, end}],
        holds?: [{start, end, reason}], policy?: {...}}
Times are seconds. Actions describe meaningful visible changes; camera motion
alone does not count as a change. A hold needs a concrete reading/narration reason.
Policy keys: transition_max, enter_max, reflow_max, focus_max, exit_max,
gap_max (seconds). All non-camera actions get boundary frame samples.
CLI overrides take precedence over the optional JSON policy.

Warnings are advisory. Frame samples and timing checks cannot establish visual
smoothness, legibility, factual accuracy, or synchronization with narration.
"""

import argparse
import json
import math
import sys
from pathlib import Path


KINDS = {"transition", "enter", "reflow", "focus", "camera", "exit"}
DEFAULT_POLICY = {
    "transition_max": 0.35,
    "enter_max": 0.45,
    "reflow_max": 0.7,
    "focus_max": 0.55,
    "exit_max": 0.35,
    "gap_max": 1.2,
}


def number(value, label, *, positive=False):
    """Reject bools, NaN and infinity as well as invalid time values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (value <= 0 if positive else value < 0):
        boundary = "positive" if positive else "nonnegative"
        raise ValueError(f"{label} must be finite and {boundary}")
    return float(value)


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value.strip()


def interval(item, duration, label):
    if not isinstance(item, dict):
        raise ValueError(f"{label} must be an object")
    start = number(item.get("start"), f"{label}.start")
    end = number(item.get("end"), f"{label}.end")
    if end <= start or end > duration:
        raise ValueError(f"{label} must satisfy 0 <= start < end <= duration")
    return start, end


def merge_intervals(intervals):
    """Return the union, merging both overlapping and touching intervals."""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def audit(plan, policy_overrides=None):
    if not isinstance(plan, dict):
        raise ValueError("motion plan must be an object")
    duration = number(plan.get("duration"), "duration", positive=True)
    fps = plan.get("fps")
    number(fps, "fps", positive=True)
    if not isinstance(fps, int):
        raise ValueError("fps must be a positive integer")

    policy = dict(DEFAULT_POLICY)
    for source in (plan.get("policy", {}), {} if policy_overrides is None else policy_overrides):
        if not isinstance(source, dict):
            raise ValueError("policy must be an object")
        unknown = set(source) - set(policy)
        if unknown:
            raise ValueError(f"Unknown policy keys: {', '.join(sorted(unknown))}")
        for key, value in source.items():
            policy[key] = number(value, f"policy.{key}", positive=True)

    actions = plan.get("actions")
    holds = plan.get("holds", [])
    if not isinstance(actions, list) or not isinstance(holds, list):
        raise ValueError("actions and holds must be arrays")

    warnings = []
    coverage = []
    samples = {}
    frame_count = duration * fps
    if not math.isfinite(frame_count):
        raise ValueError("duration * fps must be finite")
    last_frame = math.ceil(frame_count) - 1
    ids = set()

    def sample(frame, action_id, phase):
        frame = max(0, min(last_frame, frame))
        samples.setdefault(frame, []).append({"action": action_id, "phase": phase})

    for index, action in enumerate(actions):
        label = f"actions[{index}]"
        start, end = interval(action, duration, label)
        action_id = text(action.get("id"), f"{label}.id")
        if action_id in ids:
            raise ValueError(f"Duplicate action id: {action_id}")
        ids.add(action_id)
        kind = action.get("kind")
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError(f"{label}.kind must be one of {', '.join(sorted(KINDS))}")
        if kind != "camera":
            coverage.append((start, end))
        threshold = policy.get(f"{kind}_max")
        if threshold is not None and end - start > threshold + 1e-9:
            warnings.append({
                "code": f"long-{kind}", "action": action_id,
                "start": start, "end": end, "duration": end - start,
                "threshold": threshold,
                "message": "Review motion duration; shorten travel or easing tails if they add no meaning.",
            })
        if kind != "camera":
            # Samples straddle each primary action. 'end' is its last included frame;
            # 'after' is the first frame at/after its exclusive end time.
            first = math.floor(start * fps)
            final = math.ceil(end * fps) - 1
            for phase, frame in (
                ("before", first - 1), ("start", first),
                ("middle", math.floor((start + end) * fps / 2)),
                ("end", final), ("after", final + 1),
            ):
                sample(frame, action_id, phase)

    for index, hold in enumerate(holds):
        label = f"holds[{index}]"
        span = interval(hold, duration, label)
        text(hold.get("reason"), f"{label}.reason")
        coverage.append(span)

    merged = merge_intervals(coverage)
    cursor = 0.0
    for start, end in [*merged, (duration, duration)]:
        if start - cursor > policy["gap_max"] + 1e-9:
            warnings.append({
                "code": "idle-gap", "start": cursor, "end": start,
                "duration": start - cursor, "threshold": policy["gap_max"],
                "message": "No recorded primary change or explained hold; camera drift does not cover this gap.",
            })
        cursor = max(cursor, end)

    return {
        "valid": True,
        "qualityAssessed": False,
        "duration": duration,
        "fps": fps,
        "policy": policy,
        "warnings": warnings,
        "frameSamples": [
            {"frame": frame, "time": frame / fps, "reasons": reasons}
            for frame, reasons in sorted(samples.items())
        ],
        "reviewRequired": "Inspect continuous motion and, when present, narration at these boundaries; timing checks alone do not establish quality.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path, help="motion-plan.json QA record (read only)")
    parser.add_argument("--output", type=Path, help="create a new report file; never overwrite")
    for key in DEFAULT_POLICY:
        parser.add_argument("--" + key.replace("_", "-"), type=float,
                            help=f"seconds; default {DEFAULT_POLICY[key]}, overrides JSON policy")
    args = parser.parse_args(argv)
    overrides = {key: getattr(args, key) for key in DEFAULT_POLICY if getattr(args, key) is not None}
    try:
        report = audit(json.loads(args.plan.read_text(encoding="utf-8")), overrides)
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(payload)
        else:
            sys.stdout.write(payload)
    except (ValueError, OSError) as error:
        parser.exit(2, f"audit_motion: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
