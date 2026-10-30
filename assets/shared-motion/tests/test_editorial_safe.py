"""Full-canvas safe layout regressions for the optional subtitle/CTA route."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('safe_adapter', ROOT/'editorial_ui.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def config():
    value = json.loads((ROOT/'examples/impeccable-v3.json').read_text())
    value['caption_safe'] = True
    value['content']['engagement'] = {
        'lines': ['有想法欢迎留言', '觉得有用记得点赞、关注。'],
        'actions': ['留言', '点赞', '关注'],
    }
    value['scenes'].append({'id': 'engagement', 'source': 'engagement', 'duration': 4.5})
    return value


class EditorialSafeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            adapter.resolve_font()
        except RuntimeError as error:
            raise unittest.SkipTest(str(error))

    def test_solid_scene_background_reaches_all_four_edges(self):
        scenes = adapter.create_scenes(config(), ROOT)
        for index, color in [(1, adapter.ORANGE), (3, adapter.BLUE), (6, adapter.INK), (7, adapter.INK)]:
            frame = scenes[index].frame(2.5)
            expected = Image.new('RGB', (1, 1), color).getpixel((0, 0))
            self.assertEqual(frame.size, (1920, 1080))
            for point in [(0, 0), (1919, 0), (0, 1079), (1919, 1079)]:
                self.assertEqual(frame.getpixel(point), expected, (index, point))

    def test_main_content_leaves_single_line_caption_region_clear(self):
        scenes = adapter.create_scenes(config(), ROOT)
        # Excludes the separate small right-corner conceptual disclaimer.
        for scene, time, color in zip(scenes, [4.9, 2.5, 2.5, 3, 5.8, 5, 7.5, 2],
                                     [adapter.CREAM, adapter.ORANGE, adapter.CREAM, adapter.BLUE,
                                      adapter.CREAM, adapter.CREAM, adapter.INK, adapter.INK]):
            area = scene.frame(time).crop((450, 916, 1470, 1004))
            self.assertIsNone(ImageChops.difference(area, Image.new('RGB', area.size, color)).getbbox(), scene.id)

    def test_engagement_duration_follows_authored_audio_segment(self):
        scenes = adapter.create_scenes(config(), ROOT)
        self.assertEqual(scenes[-1].duration, 4.5)
        self.assertEqual(scenes[-1].id, 'engagement')

    def test_invalid_caption_flag_and_incomplete_cta_are_rejected(self):
        value = config(); value['caption_safe'] = 'yes'
        with self.assertRaises(ValueError): adapter.create_scenes(value, ROOT)
        value = config(); value['content']['engagement']['actions'] = ['关注']
        with self.assertRaises(ValueError): adapter.create_scenes(value, ROOT)


if __name__ == '__main__':
    unittest.main()
