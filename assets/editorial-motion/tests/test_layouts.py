import importlib.util,json,unittest,copy,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('editorial',ROOT/'editorial_samples.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Layouts(unittest.TestCase):
 def test_all_six_actual_renderers(self):
  for layout in m.LAYOUTS:
   im=m.render_layout(layout,{},2.8);self.assertEqual(im.size,(1920,1080));self.assertEqual(im.mode,'RGBA')
 def test_float_boundary(self):
  config=json.loads((ROOT/'api-example.json').read_text())
  self.assertEqual(m.config_frame(config,3.4).size,(1920,1080))
 def test_examples_valid(self):
  for name in ('api-example.json','memory-example.json'):self.assertEqual(m.validate_config(json.loads((ROOT/name).read_text())),12)
 def test_determinism_and_no_palette_leak(self):
  a=m.render_layout('timeline',{},2).tobytes();m.render_layout('timeline',{'palette':{'INK':'#111111'}},2)
  self.assertEqual(a,m.render_layout('timeline',{},2).tobytes())
 def test_bad_inputs_rejected(self):
  for conf in ({'scenes':[]},{'scenes':[False]},{'width':500,'scenes':[{}]},{'scenes':[{'layout':'unknown'}]},{'scenes':[{'layout':'ledger','content':{'rows':'abc'}}]}):
   with self.assertRaises(ValueError):m.validate_config(conf)
  for t in (float('nan'),float('inf'),True):
   with self.assertRaises(ValueError):m.render_layout('timeline',{},t)
 def test_existing_output_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'old.mp4';p.write_bytes(b'old')
   with self.assertRaises(FileExistsError):m.render_config({'scenes':[{'layout':'timeline'}]},p)
   self.assertEqual(p.read_bytes(),b'old')
if __name__=='__main__':unittest.main()
