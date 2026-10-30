import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('render_captions', Path(__file__).resolve().parents[1]/'render_captions.py')
captions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(captions)


class CaptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root/'original.mp4'
        self.video.write_bytes(b'video fixture')
        self.output = self.root/'new.mp4'
        self.srt = self.root/'new.srt'
        self.cues = [{'start': 0.5, 'end': 2.25, 'text': '这是字幕。'}]

    def test_timestamp_rounding_and_hour_carry(self):
        self.assertEqual(captions.timestamp(3599.9995), '01:00:00,000')
        self.assertEqual(captions.timestamp(61.234), '00:01:01,234')
        self.assertEqual(captions.timestamp(61.235, ass=True), '0:01:01.24')

    def test_invalid_times_and_overlap(self):
        for value in [True, float('nan'), float('inf'), -1, '1']:
            with self.assertRaises(ValueError):
                captions.validate_captions({'captions': [{'start': value, 'end': 2, 'text': '词'}]})
        for document in [
            {'captions': [{'start': 1, 'end': 1, 'text': '词'}]},
            {'captions': self.cues + [{'start': 2.2, 'end': 3, 'text': '词'}]},
            {'captions': self.cues, 'duration': 1},
            {'captions': [{'start': 0, 'end': .001, 'text': '词'}]},
        ]:
            with self.assertRaises(ValueError): captions.validate_captions(document)

    def test_text_limits_and_wrapping_preserve_characters(self):
        for value in ['', 'a\nb\nc', 'a\n', '中'*45, 'a\rb']:
            with self.assertRaises(ValueError):
                captions.validate_captions({'captions': [{'start': 0, 'end': 2, 'text': value}]})
        value='中'*43
        result=captions.validate_captions({'captions':[{'start':0,'end':2,'text':value}]})
        self.assertEqual(result[0]['text'].replace('\n',''), value)
        self.assertEqual(len(result[0]['text'].splitlines()),2)

    def test_ass_override_is_not_executed(self):
        text=r'{\pos(1,1)}literal\N'+'\n下一行'
        escaped=captions.ass_escape(text)
        self.assertNotIn('{',escaped)
        self.assertNotIn(r'\pos',escaped)
        self.assertEqual(escaped.count(r'\N'),1)
        with self.assertRaises(ValueError): captions.ass_text(self.cues,'fake\nStyle: injected')
        self.assertIn('&lt;i&gt;',captions.srt_text([{'start':0,'end':1,'text':'<i>x</i>'}]))

    def test_burn_command_keeps_audio_and_does_not_put_paths_in_filter(self):
        command=captions.build_command('/ffmpeg',self.video,self.output)
        self.assertEqual(command[command.index('-c:a')+1],'copy')
        filters=command[command.index('-vf')+1]
        self.assertEqual(filters,'ass=filename=captions.ass:fontsdir=fonts')
        for operation in ['scale=', 'pad=', 'crop=', 'setsar=']:
            self.assertNotIn(operation,filters)
        self.assertNotIn(str(self.root),filters)

    def test_original_skill_style_has_rounded_box_without_motion(self):
        result=captions.ass_text(self.cues)
        self.assertIn('Style: Default,PingFang SC,40,&H00F3FAFD',result)
        events=[line for line in result.splitlines() if line.startswith('Dialogue:')]
        self.assertEqual(len(events),2)
        self.assertTrue(events[0].startswith('Dialogue: 0,0:00:00.50,0:00:02.25'))
        self.assertIn(r'\p1\bord0\shad0\1c&H0A1217&\1a&H11&',events[0])
        self.assertIn('m 12 0 l ',events[0])
        self.assertIn(' b ',events[0])
        self.assertIn(r'\pos(960,960)\b600\bord0\shad0',events[1])
        for animation in [r'\move',r'\fad',r'\t(']:
            self.assertNotIn(animation,result)

    def test_two_line_box_keeps_sixty_pixel_line_spacing_and_bottom_margin(self):
        cues=[{'start':0,'end':1,'text':'这是第一行\n这是第二行'}]
        result=captions.ass_text(cues)
        events=[line for line in result.splitlines() if line.startswith('Dialogue:')]
        self.assertEqual(len(events),3)
        self.assertIn(',856)',events[0])
        self.assertIn(r'\pos(960,900)',events[1])
        self.assertIn(r'\pos(960,960)',events[2])
        self.assertIn('148',events[0])  # 2*60 + 2*14; bottom is 1004 = 1080-76

    def test_caption_box_width_uses_measured_text_and_rejects_unsafe_width(self):
        with patch.object(captions,'text_width',return_value=321):
            result=captions.ass_text(self.cues)
        self.assertIn(r'\pos(771.5,916)',result)  # (1920 - (321 + 56))/2
        with patch.object(captions,'text_width',return_value=1200):
            with self.assertRaisesRegex(ValueError,'safe width'):
                captions.ass_text(self.cues)

    def test_font_measurement_is_optional_and_missing_font_is_explicit(self):
        self.assertEqual(captions.text_width('中文',40),80)
        self.assertLess(captions.text_width('iii',40),captions.text_width('WWW',40))
        with self.assertRaisesRegex(ValueError,'existing local file'):
            captions.ass_text(self.cues,font_file=self.root/'missing.ttf')

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'keep')
        with patch.object(captions.subprocess,'run',side_effect=AssertionError('must not render')):
            with self.assertRaises(FileExistsError): captions.render(self.video,self.cues,self.output,self.srt)
        self.assertEqual(self.output.read_bytes(),b'keep')

    def test_sidecar_copies_without_reencoding(self):
        with patch.object(captions.subprocess,'run',side_effect=AssertionError('no encoding')):
            result=captions.render(self.video,self.cues,self.output,self.srt,mode='sidecar')
        self.assertFalse(result['burned_narration_subtitles'])
        self.assertEqual(self.video.read_bytes(),self.output.read_bytes())
        self.assertIn('00:00:00,500 --> 00:00:02,250',self.srt.read_text())

    def test_encoding_failure_does_not_publish_outputs(self):
        with patch.object(captions.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='failed')):
            with self.assertRaises(RuntimeError): captions.render(self.video,self.cues,self.output,self.srt)
        self.assertFalse(self.output.exists());self.assertFalse(self.srt.exists())

    def test_burn_publishes_completed_video_and_srt(self):
        def run(command,**kwargs):
            self.assertTrue((Path(kwargs['cwd'])/'captions.ass').is_file())
            Path(command[-1]).write_bytes(b'encoded')
            return SimpleNamespace(returncode=0,stderr='')
        with patch.object(captions.subprocess,'run',side_effect=run):
            result=captions.render(self.video,self.cues,self.output,self.srt)
        self.assertTrue(result['burned_narration_subtitles'])
        self.assertEqual(self.output.read_bytes(),b'encoded')
        self.assertTrue(self.srt.is_file())

    def test_validate_only_creates_nothing(self):
        source=self.root/'captions.json';source.write_text(json.dumps({'captions':self.cues}))
        with patch.object(captions.subprocess,'run',side_effect=AssertionError('no encoder')):
            self.assertEqual(captions.main(['--video',str(self.video),'--captions',str(source),
                '--output',str(self.output),'--srt',str(self.srt),'--validate-only']),0)
        self.assertFalse(self.output.exists());self.assertFalse(self.srt.exists())


if __name__ == '__main__': unittest.main()
