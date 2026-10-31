import copy, importlib.util, json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_acceptance import Acceptance
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('plan',ROOT/'check_visual_plan.py');plan=importlib.util.module_from_spec(s);s.loader.exec_module(plan)
class Editorial(Acceptance):
 def setUp(self):
  super().setUp()
  import io
  from PIL import Image
  def picture(color):
   b=io.BytesIO();Image.new('RGB',(32,18),color).save(b,format='PNG');return b.getvalue()
  self.proof=self.write('frame.png',picture('blue'))
  review={'reviewer':'fixture','notes':'unit fixture, not real aesthetic evidence',**{k:'passed' for k in plan.CRITERIA}}
  self.plan={'schema_version':1,'design_thesis':'receipt explains cost, notebook explains retained context','assets':[], 'scenes':[],'transitions':[]}
  for i,form in enumerate(('editorial_hero','ledger')):
   self.plan['scenes'].append({'id':str(i),'visual_form':form,**{k:'fixture' for k in ('argument','dominant_subject','composition_reason','material_treatment','state_change','implementation')},'keyframe':self.proof,'review':copy.deepcopy(review)})
  self.plan['transitions']=[{'from':'0','to':'1','effect':'radial','origin':[.2,.5],'duration':.4,**{k:'fixture' for k in ('reason','origin_subject','trigger','implementation')}}]
  self.record.update(schema_version=2,profile='editorial-v4',visual_plan=self.write('plan.json',json.dumps(self.plan).encode()),transition_reviews=[{'from':'0','to':'1','effect':'radial','status':'passed','reviewer':'fixture','notes':'unit-test only','start':3,'end':3.4,**{k:self.proof for k in ('before','middle','after')}}])
  self.record['transition_reviews'][0]['middle']=self.write('middle.png',picture('orange'))
  self.record['gates']['art_direction']=copy.deepcopy(self.record['gates']['technical']);self.record['gates']['transition_visual']=copy.deepcopy(self.record['gates']['technical'])
 def test_identical_evidence_blocks(self):
  self.record['transition_reviews'][0]['middle']=self.proof;self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_zero_effect_blocks(self):
  self.plan['transitions'][0]['duration']=0;self.assertFalse(plan.check(self.plan,self.root)['visual_plan_complete'])
 def test_editorial_mode_requires_v4(self):
  self.record.update(schema_version=1,mode='editorial-motion');self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_missing_art_blocks(self):
  del self.record['gates']['art_direction'];self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_wrong_transition_blocks(self):
  self.record['transition_reviews'][0]['effect']='flip';self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_missing_boundary_blocks(self):
  del self.record['transition_reviews'][0]['middle'];self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_stale_keyframe_blocks(self):
  self.plan['scenes'][0]['keyframe']={'path':'absent','sha256':'0'*64};self.record['visual_plan']=self.write('plan.json',json.dumps(self.plan).encode());self.assertFalse(self.check()['formal_delivery_allowed'])
 def test_missing_origin_blocks(self):
  del self.plan['transitions'][0]['origin'];self.assertFalse(plan.check(self.plan,self.root)['visual_plan_complete'])
 def test_same_form_requires_reason(self):
  self.plan['scenes'] += [copy.deepcopy(self.plan['scenes'][1])];self.plan['scenes'][2]['id']='2'
  for scene in self.plan['scenes']:scene['visual_form']='ledger'
  self.assertTrue(any('same visual form' in x for x in plan.check(self.plan,self.root)['issues']))
 def test_uninspected_visual_cannot_pass(self):
  self.plan['scenes'][0]['review']['hierarchy']='not_checked';self.assertFalse(plan.check(self.plan,self.root)['visual_plan_complete'])
 def test_legacy_cannot_satisfy_v4(self):
  self.record['schema_version']=1
  self.assertFalse(__import__('test_acceptance').checker.check(self.record,self.root,'editorial-v4')['formal_delivery_allowed'])
if __name__=='__main__':unittest.main()
