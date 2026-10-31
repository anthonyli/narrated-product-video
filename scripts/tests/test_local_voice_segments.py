import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import local_voice_segments as s
class ParagraphTests(unittest.TestCase):
    def test_semantic_blank_lines(self):
        self.assertEqual(s.split_paragraphs('一整段。\n\n第二段。'), ['一整段。','第二段。'])
    def test_empty_and_oversize_rejected(self):
        for text in ['', '中'*121]:
            with self.assertRaises(ValueError):s.split_paragraphs(text)
if __name__=='__main__': unittest.main()
