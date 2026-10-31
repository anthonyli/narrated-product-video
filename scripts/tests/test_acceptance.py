import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
checker=load('check_acceptance');scanner=load('scan_visual_holds')

class Holds(unittest.TestCase):
 def test_constant_flags(self):self.assertEqual(scanner.low_change_spans([0]*10,2),[{'start':0.,'end':5.,'duration':5.,'status':'not_checked'}])
 def test_short_hold_allowed(self):self.assertEqual(scanner.low_change_spans([0]*5,2),[])
 def test_motion_breaks_spans(self):
  self.assertEqual(scanner.low_change_spans([0]*6+[.2]+[0]*8,2),[{'start':0.,'end':3.,'duration':3.,'status':'not_checked'},{'start':3.5,'end':7.5,'duration':4.,'status':'not_checked'}])
 def test_no_dynamic_quality_claim(self):self.assertEqual(scanner.low_change_spans([.1]*20,2),[])
 def test_invalid_scores(self):
  for v in [float('nan'),float('inf'),-1,2]:
   with self.assertRaises(ValueError):scanner.low_change_spans([v],2)
 def test_bad_fps(self):
  for v in [0,-1,float('nan'),True]:
   with self.assertRaises(ValueError):scanner.low_change_spans([0],v)

class Acceptance(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.video=self.write('final.mp4',b'synthetic-final-version')
  self.proof=self.write('proof.txt',b'test evidence only')
  self.scan=self.write('scan.json',json.dumps({'video_sha256':self.video['sha256'],'low_change_spans':[{'start':1,'end':5}]}).encode())
  gate={'status':'passed','reviewer':'test:fixture','notes':'synthetic unit-test record','evidence':[self.proof]}
  self.record={'schema_version':1,'mode':'shared-motion','duration':10,'video':self.video,'has_narration':True,'has_captions':True,
   'gates':{k:copy.deepcopy(gate) for k in list(checker.REQUIRED)+['audio_transcript','captions']},
   'sample':{'artifact':self.proof,'contains_state_change':True,'contains_join':True},
   'state_chains':[{'object_id':'a','before':'list','change':'compress','after':'summary','meaning':'retain relevant context','status':'passed','evidence':self.proof}],
   'static_scan':self.scan,'hold_reviews':[{'scan_span_index':0,'status':'passed','decision':'justified_reading','reason':'read the specific three conditions','evidence':self.proof}], 'findings':[]}
 def tearDown(self):self.tmp.cleanup()
 def write(self,name,data):
  (self.root/name).write_bytes(data);return {'path':name,'sha256':hashlib.sha256(data).hexdigest()}
 def check(self):return checker.check(self.record,self.root)
 def test_complete_record_not_aesthetic_certification(self):
  r=self.check();self.assertTrue(r['formal_delivery_allowed']);self.assertFalse(r['aesthetics_independently_assessed']);self.assertTrue(r['disclosures'])
 def test_missing_final_visual_blocks(self):
  self.record['gates']['final_visual']['status']='not_checked';self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_failed_visual_blocks_despite_technical_pass(self):
  self.record['gates']['final_visual']['status']='failed';self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_rerender_invalidates_hash(self):
  (self.root/'final.mp4').write_bytes(b'new');self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_missing_evidence_blocks(self):
  (self.root/'proof.txt').unlink();self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_changed_evidence_blocks(self):
  (self.root/'proof.txt').write_bytes(b'changed');self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_unreviewed_static_blocks(self):
  self.record['hold_reviews']=[];self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_failed_static_cannot_be_waived(self):
  self.record['hold_reviews'][0]['status']='failed';self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_decorative_sample_blocks(self):
  self.record['sample']['contains_state_change']=False;self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_no_object_chain_blocks(self):
  self.record['state_chains']=[];self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_blocking_issue_blocks(self):
  self.record['findings']=[{'description':'words missing','status':'failed','blocking':True}];self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_optional_failure_disclosed(self):
  self.record['findings']=[{'description':'style subjective','status':'not_checked','blocking':False}];r=self.check();self.assertTrue(r['formal_delivery_allowed']);self.assertIn('style subjective',r['disclosures'])
 def test_bad_status_rejected(self):
  self.record['gates']['technical']['status']='sort_of';self.assertRaises(ValueError,self.check)
 def test_old_scan_blocks(self):
  self.record['static_scan']=self.write('old.json',json.dumps({'video_sha256':'0'*64,'low_change_spans':[]}).encode());self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_fake_listening_pass_without_evidence_blocks(self):
  self.record['gates']['audio_listening']={'status':'passed'};self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_malformed_listening_rejected(self):
  self.record['gates']['audio_listening']=[];self.assertRaises(ValueError,self.check)
 def test_nonboolean_blocking_rejected(self):
  self.record['findings']=[{'description':'missing words','status':'failed','blocking':None}];self.assertRaises(ValueError,self.check)
 def test_nan_duration_rejected(self):self.record['duration']=float('nan');self.assertRaises(ValueError,self.check)

if __name__=='__main__':unittest.main()
