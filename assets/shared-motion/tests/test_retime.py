import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Episode, Hold, Rest, Scene, finite, load_episode, validate_render


class RetimeTests(unittest.TestCase):
    def test_shorten_idle_interval_preserves_both_actions(self):
        scene = Scene('sequence', 8, lambda t: t, rests=(Rest(2, 6, 1, 'Shorter reading'),))
        self.assertEqual(scene.total_duration, 5)
        self.assertEqual(scene.source_time(1.5), 1.5)
        self.assertEqual(scene.source_time(2.5), 4)
        self.assertEqual(scene.source_time(3), 6)
        self.assertAlmostEqual(scene.source_time(4.5), 7.5)
        # The 2-second transition after the resting interval stays 2 seconds.
        self.assertEqual(scene.source_time(4)-scene.source_time(3), 1)

    def test_remove_rest_and_insert_later_hold(self):
        scene = Scene('sequence', 8, lambda t: t,
                      holds=(Hold(7, 2, 'Narration conclusion'),),
                      rests=(Rest(2, 6, 0, 'Remove empty wait'),))
        self.assertEqual(scene.total_duration, 6)
        self.assertEqual(scene.source_time(2), 6)
        self.assertEqual(scene.source_time(3.5), 7)
        self.assertEqual(scene.source_time(5.5), 7.5)

    def test_rest_constraints(self):
        with self.assertRaises(ValueError): Rest(1, 2, -1, 'bad')
        with self.assertRaises(ValueError): Rest(1, 2, 0, '')
        with self.assertRaises(ValueError): Scene('a', 4, lambda t:t, rests=(Rest(1, 5, 0, 'bad'),))
        with self.assertRaises(ValueError): Scene('a', 4, lambda t:t, rests=(Rest(1, 3, 1, 'a'), Rest(2, 4, 1, 'b')))
        with self.assertRaises(ValueError): Scene('a', 4, lambda t:t, holds=(Hold(2, 1, 'a'),), rests=(Rest(1, 3, 1, 'b'),))
        with self.assertRaises(ValueError): Scene('a', 4, lambda t:t, rests=(Rest(0, 4, 0, 'all'),))

    def test_render_validation_is_independent_of_encoding(self):
        episode = Episode([Scene('a', 1, lambda t:None)])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with self.assertRaises(ValueError): validate_render(episode, base/'a.txt')
            with self.assertRaises(ValueError): validate_render(episode, base/'a.mp4', start=5, end=1)
            with self.assertRaises(FileNotFoundError): validate_render(episode, base/'a.mp4', audio=base/'missing.wav')
            (base/'a.mp4').write_bytes(b'old')
            with self.assertRaises(FileExistsError): validate_render(episode, base/'a.mp4')

    def test_large_number_is_a_validation_error(self):
        with self.assertRaises(ValueError): finite(10**1000, 'value')

    def test_adapter_supports_dataclass_and_postponed_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'adapter.py').write_text('from __future__ import annotations\n'
                'from dataclasses import dataclass\nfrom core import Scene\n'
                '@dataclass\nclass Body:\n    x: float\n'
                'def create_scenes(config, config_dir):\n'
                '    body = Body(config["value"])\n'
                '    return [Scene("scene", 1, lambda t: body.x+t)]\n')
            (root/'first.json').write_text(json.dumps({'adapter':'adapter.py', 'value':10}))
            (root/'second.json').write_text(json.dumps({'adapter':'adapter.py', 'value':20}))
            first, _ = load_episode(root/'first.json')
            second, _ = load_episode(root/'second.json')
            self.assertEqual(first.frame(.5), 10.5)
            self.assertEqual(second.frame(.5), 20.5)


if __name__ == '__main__':
    unittest.main()
