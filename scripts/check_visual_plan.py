#!/usr/bin/env python3
"""Validate an authored editorial visual plan and its inspected keyframe evidence.
Checks completeness and hashes, not whether a layout is beautiful or a claim true.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

FORMS={'editorial_hero','ledger','notebook','diagram','chart','timeline','screen','custom'}
EFFECTS={'ripple','radial','flip','match','cut','dissolve','custom'}
CRITERIA=('hierarchy','composition','material_consistency','legibility','content_fit')

def nonempty(v):return isinstance(v,str) and bool(v.strip())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def check(plan,base):
 if not isinstance(plan,dict) or plan.get('schema_version')!=1:raise ValueError('visual plan schema_version must be 1')
 base=Path(base);issues=[]
 def artifact(e,label):
  if not isinstance(e,dict) or not nonempty(e.get('path')) or not nonempty(e.get('sha256')):issues.append(label+': path/hash required');return
  p=base/e['path']
  if not p.is_file() or digest(p)!=e['sha256']:issues.append(label+': missing/stale artifact');return
  if label.endswith('.keyframe'):
   try:
    from PIL import Image
    with Image.open(p) as im:im.verify()
   except (OSError,ValueError):issues.append(label+': keyframe must be a decodable image')
 if not nonempty(plan.get('design_thesis')):issues.append('design_thesis required')
 scenes=plan.get('scenes',[])
 if not isinstance(scenes,list) or not scenes:raise ValueError('scenes must be a nonempty array')
 ids=[];forms=[]
 for i,s in enumerate(scenes):
  if not isinstance(s,dict):raise ValueError('scene must be object')
  label=f'scenes[{i}]';ids.append(s.get('id'));forms.append(s.get('visual_form'))
  for k in ('id','argument','dominant_subject','composition_reason','material_treatment','state_change','implementation'):
   if not nonempty(s.get(k)):issues.append(label+': '+k+' required')
  if s.get('visual_form') not in FORMS:issues.append(label+': unsupported visual_form')
  artifact(s.get('keyframe'),label+'.keyframe')
  review=s.get('review',{})
  if not isinstance(review,dict):raise ValueError('review must be object')
  if not nonempty(review.get('reviewer')) or not nonempty(review.get('notes')):issues.append(label+': concrete review required')
  for k in CRITERIA:
   if review.get(k)!='passed':issues.append(label+': '+k+' not passed')
  if s.get('visual_form')=='chart' and (not isinstance(s.get('data'),dict) or not isinstance(s['data'].get('illustrative'),bool) or not nonempty(s['data'].get('source'))):issues.append(label+': chart provenance/illustrative flag required')
 if any(not isinstance(i,str) for i in ids):raise ValueError('scene IDs must be strings')
 if len(set(ids))!=len(ids):issues.append('scene IDs must be unique')
 if len(scenes)>2 and len(set(forms))==1 and not nonempty(plan.get('uniform_form_rationale')):issues.append('same visual form throughout requires task-specific rationale; no default all-card template')
 transitions=plan.get('transitions',[])
 if not isinstance(transitions,list):raise ValueError('transitions must be array')
 expected=list(zip(ids[:-1],ids[1:]))
 if len(transitions)!=len(expected):issues.append('transitions must cover exactly consecutive scene boundaries')
 for t in transitions:
  if not isinstance(t,dict):raise ValueError('transition must be object')
  if (t.get('from'),t.get('to')) not in expected:issues.append('transition references unknown/nonconsecutive scene')
 for before,after in expected:
  matches=[t for t in transitions if isinstance(t,dict) and t.get('from')==before and t.get('to')==after]
  if len(matches)!=1:issues.append(f'transition {before}->{after}: exactly one plan required');continue
  t=matches[0]
  if t.get('effect') not in EFFECTS:issues.append('transition: unknown effect')
  for k in ('reason','origin_subject','trigger','implementation'):
   if not nonempty(t.get(k)):issues.append('transition: '+k+' required')
  duration=t.get('duration')
  if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<0 or duration>3:issues.append('transition: duration invalid')
  elif duration==0 and t.get('effect')!='cut':issues.append('transition: non-cut requires positive duration')
  elif duration>1 and not nonempty(t.get('long_transition_reason')):issues.append('transition: long duration needs reading/meaning reason')
  if t.get('effect') in ('ripple','radial'):
   o=t.get('origin')
   if not isinstance(o,list) or len(o)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in o):issues.append('transition: normalized origin required')
 assets=plan.get('assets')
 if not isinstance(assets,list):raise ValueError('assets must be array (empty permitted for entirely code-authored shapes)')
 for i,a in enumerate(assets):
  if not isinstance(a,dict):raise ValueError('asset must be object')
  for k in ('origin','rights','purpose'):
   if not nonempty(a.get(k)):issues.append(f'asset {i}: {k} required')
  artifact(a,f'asset {i}')
 return {'schema_version':1,'visual_plan_complete':not issues,'quality_assessed':False,'issues':issues,'notice':'Completeness and artifact checks do not establish aesthetic quality or truthful reviewer claims.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:
  result=check(json.loads(a.plan.read_text()),a.plan.parent);payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
  if a.output:
   with a.output.open('x') as f:f.write(payload)
  else:print(payload,end='')
 except (ValueError,OSError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')
 return 0 if result['visual_plan_complete'] else 1
if __name__=='__main__':sys.exit(main())
