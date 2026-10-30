"""Behavior checks for deterministic time mapping and safe local delivery.

These tests use scalar frame callbacks, so the core contract is independent of
Pillow, fonts, FFmpeg, scene artwork, and GPU access.
"""
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Episode, Hold, Scene, reserve_publish, validate_audio


def source_frame(time):
    return time


class SceneTimingTests(unittest.TestCase):
    def test_no_hold_preserves_source_time_and_duration(self):
        scene = Scene("base", 4.0, source_frame)
        self.assertEqual(scene.total_duration, 4.0)
        for time in (0, 0.01, 1.7, 3.999):
            self.assertEqual(scene.source_time(time), time)

    def test_hold_freezes_only_its_interval_and_keeps_action_speed(self):
        scene = Scene("layout", 4.0, source_frame,
                      holds=(Hold(1.5, 2.0, "Read the changed layout"),))
        self.assertEqual(scene.total_duration, 6.0)
        self.assertAlmostEqual(scene.source_time(1.4), 1.4)
        for time in (1.5, 2, 3.49):
            self.assertAlmostEqual(scene.source_time(time), 1.5)
        self.assertAlmostEqual(scene.source_time(3.5), 1.5)
        self.assertAlmostEqual(scene.source_time(3.6), 1.6)
        # Both before and after the hold, a 0.2 s step remains 0.2 source s.
        self.assertAlmostEqual(scene.source_time(.8) - scene.source_time(.6), .2)
        self.assertAlmostEqual(scene.source_time(4.2) - scene.source_time(4), .2)

    def test_multiple_holds_use_source_coordinates(self):
        scene = Scene("sequence", 6.0, source_frame,
                      holds=(Hold(1.0, 2.0, "First explanation"),
                             Hold(4.0, 1.0, "Second explanation")))
        self.assertEqual(scene.total_duration, 9.0)
        for output_time, source_time in ((.5, .5), (2, 1), (3.5, 1.5),
                                          (5.5, 3.5), (6.5, 4), (7.5, 4.5),
                                          (8.9, 5.9)):
            self.assertAlmostEqual(scene.source_time(output_time), source_time)

    def test_opening_hold_and_exclusive_timeline_end(self):
        scene = Scene("opening", 2.0, source_frame,
                      holds=(Hold(0.0, .4, "Recognize the initial state"),))
        self.assertEqual(scene.source_time(0), 0)
        self.assertEqual(scene.source_time(.3), 0)
        self.assertAlmostEqual(scene.source_time(.5), .1)
        for invalid in (-.1, scene.total_duration, math.inf, math.nan, True):
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, TypeError)):
                scene.source_time(invalid)

    def test_invalid_source_durations_are_rejected(self):
        for duration in (0, -1, math.nan, math.inf, True):
            with self.subTest(duration=duration), self.assertRaises((ValueError, TypeError)):
                Scene("invalid", duration, source_frame)

    def test_invalid_holds_are_rejected(self):
        for at, duration, reason in ((-1, 1, "reason"),
                                     (math.nan, 1, "reason"),
                                     (True, 1, "reason"),
                                     (1, 0, "reason"),
                                     (1, -1, "reason"),
                                     (1, math.inf, "reason"),
                                     (1, True, "reason"),
                                     (1, 1, ""), (1, 1, "   ")):
            with self.subTest(at=at, duration=duration, reason=reason):
                with self.assertRaises((ValueError, TypeError)):
                    Scene("invalid", 4, source_frame,
                          holds=(Hold(at, duration, reason),))

    def test_holds_must_be_in_source_range_and_order(self):
        for holds in ((Hold(4, 1, "outside"),),
                      (Hold(3, 1, "later"), Hold(1, 1, "earlier"))):
            with self.subTest(holds=holds), self.assertRaises((ValueError, TypeError)):
                Scene("invalid", 4, source_frame, holds=holds)


class EpisodeTimingTests(unittest.TestCase):
    def test_exact_boundary_selects_next_scene_after_inserted_hold(self):
        first = Scene("first", 2, lambda t: ("first", t),
                      holds=(Hold(1, .5, "Read"),))
        second = Scene("second", 3, lambda t: ("second", t))
        episode = Episode([first, second])
        self.assertEqual(episode.duration, 5.5)
        self.assertEqual(episode.frame(0), ("first", 0))
        self.assertEqual(episode.frame(1.25), ("first", 1))
        self.assertEqual(episode.frame(2.5), ("second", 0))
        name, source_time = episode.frame(5.4)
        self.assertEqual(name, "second")
        self.assertAlmostEqual(source_time, 2.9)
        for invalid in (-1, 5.5, math.inf, math.nan, False):
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, TypeError)):
                episode.frame(invalid)

    def test_empty_episode_and_duplicate_ids_are_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            Episode([])
        with self.assertRaises((ValueError, TypeError)):
            Episode([Scene("same", 1, source_frame), Scene("same", 1, source_frame)])


class PublicationTests(unittest.TestCase):
    def test_publish_new_file_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temporary, output = root / "temp.mp4", root / "final.mp4"
            temporary.write_bytes(b"validated-media")
            reserve_publish(temporary, output)
            self.assertEqual(output.read_bytes(), b"validated-media")

    def test_existing_output_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temporary, output = root / "temp.mp4", root / "final.mp4"
            temporary.write_bytes(b"new")
            output.write_bytes(b"old")
            with self.assertRaises((FileExistsError, ValueError)):
                reserve_publish(temporary, output)
            self.assertEqual(output.read_bytes(), b"old")
            self.assertEqual(temporary.read_bytes(), b"new")

    def test_dangling_output_symlink_is_not_followed_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temporary, output = root / "temp.mp4", root / "final.mp4"
            temporary.write_bytes(b"new")
            target = root / "missing.mp4"
            output.symlink_to(target)
            with self.assertRaises((FileExistsError, ValueError)):
                reserve_publish(temporary, output)
            self.assertTrue(output.is_symlink())
            self.assertFalse(target.exists())


class AudioValidationTests(unittest.TestCase):
    @staticmethod
    def make_wav(path, frames=16000):
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(struct.pack("<h", 100) * frames)

    def test_matching_audio_and_one_frame_tolerance(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "narration.wav"
            self.make_wav(audio)
            validate_audio(audio, 1.0, 60)
            validate_audio(audio, 1.0 + .5 / 60, 60)
            validate_audio(audio, 1.0 - .5 / 60, 60)

    def test_duration_mismatch_is_rejected_without_adjusting_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "narration.wav"
            self.make_wav(audio)
            before = audio.read_bytes()
            for duration in (.5, 1.5):
                with self.subTest(duration=duration), self.assertRaises((ValueError, RuntimeError)):
                    validate_audio(audio, duration, 60)
            self.assertEqual(audio.read_bytes(), before)

    def test_empty_and_truncated_audio_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "narration.wav"
            self.make_wav(audio, frames=0)
            with self.assertRaises((ValueError, RuntimeError, wave.Error)):
                validate_audio(audio, 1.0, 60)
            self.make_wav(audio)
            audio.write_bytes(audio.read_bytes()[:-100])
            with self.assertRaises((ValueError, RuntimeError, wave.Error)):
                validate_audio(audio, 1.0, 60)


if __name__ == "__main__":
    unittest.main()
