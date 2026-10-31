#!/usr/bin/env python3
"""Validate evidence for a shared-motion video's formal-delivery gate.
This checks recorded review completeness and artifact identity, NOT aesthetics.
Paths are relative to the acceptance JSON. No user-supplied code/plugins are loaded or run.
Exit 0: recorded gates pass; 1: incomplete/failed; 2: malformed input or IO error.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

STATUSES={'passed','failed','not_checked'}
REQUIRED=('storyboard','sample_visual','final_visual','final_semantic','technical')


def nonempty(x):return isinstance(x,str) and bool(x.strip())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def check(record,base,require_profile=None):
    if not isinstance(record,dict) or record.get('schema_version') not in (1,2):
        raise ValueError('acceptance schema_version must be 1 or 2')
    editorial = record.get('schema_version') == 2
    if editorial and record.get('profile') != 'editorial-v4':
        raise ValueError('schema 2 requires profile editorial-v4')
    if require_profile not in (None,'editorial-v4'):
        raise ValueError('unknown required profile')
    base=Path(base)
    issues=[]; disclosures=[]
    if record.get('mode') not in ('shared-motion','editorial-motion'):raise ValueError('unsupported motion mode')
    if record.get('mode')=='editorial-motion' and not editorial:issues.append('editorial-motion requires schema 2/profile editorial-v4')
    if require_profile and not editorial:issues.append('editorial-v4 requires schema 2; legacy acceptance is insufficient')
    duration=record.get('duration')
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:
        raise ValueError('duration must be finite and positive')
    def artifact(value,label):
        if not isinstance(value,dict) or not nonempty(value.get('path')) or not nonempty(value.get('sha256')):
            issues.append(f'{label}: path and sha256 required');return None
        path=base/value['path']
        if not path.is_file():issues.append(f'{label}: missing file');return None
        if sha(path)!=value['sha256']:issues.append(f'{label}: SHA256 mismatch (review stale)');return None
        return path
    video=artifact(record.get('video'),'video')
    gates=record.get('gates',{})
    if not isinstance(gates,dict):raise ValueError('gates must be an object')
    required=list(REQUIRED)
    if editorial:required += ['art_direction','transition_visual']
    if record.get('has_narration') is True:required.append('audio_transcript')
    elif record.get('has_narration') is not False:raise ValueError('has_narration must be boolean')
    if record.get('has_captions') is True:required.append('captions')
    elif record.get('has_captions') is not False:raise ValueError('has_captions must be boolean')
    for name in required:
        g=gates.get(name,{})
        if not isinstance(g,dict):raise ValueError(f'gates.{name} must be an object')
        status=g.get('status','not_checked')
        if status not in STATUSES:raise ValueError(f'gates.{name}: invalid status')
        if status!='passed':issues.append(f'{name}: {status}')
        if not nonempty(g.get('reviewer')) or not nonempty(g.get('notes')):
            issues.append(f'{name}: reviewer and concrete notes required')
        evidence=g.get('evidence',[])
        if not isinstance(evidence,list) or not evidence:issues.append(f'{name}: evidence required')
        else:
            for i,e in enumerate(evidence):artifact(e,f'{name}.evidence[{i}]')
    listening=gates.get('audio_listening',{})
    if not isinstance(listening,dict):raise ValueError('audio_listening must be an object')
    if listening.get('status','not_checked') not in STATUSES:raise ValueError('audio_listening: invalid status')
    if record['has_narration'] and listening.get('status')=='passed':
        if not nonempty(listening.get('reviewer')) or not nonempty(listening.get('notes')):
            issues.append('audio_listening: reviewer and concrete notes required for passed')
        evidence=listening.get('evidence',[])
        if not isinstance(evidence,list) or not evidence:issues.append('audio_listening: evidence required for passed')
        else:
            for i,e in enumerate(evidence):artifact(e,f'audio_listening.evidence[{i}]')
    if record['has_narration'] and listening.get('status')!='passed':
        disclosures.append('Human/listening quality not passed; disclose separately from ASR coverage.')
    sample=record.get('sample',{})
    if not isinstance(sample,dict):raise ValueError('sample must be an object')
    if sample.get('contains_state_change') is not True or sample.get('contains_join') is not True:
        issues.append('sample must show a meaningful state change AND a cross-scene join')
    artifact(sample.get('artifact'),'sample.artifact')
    chains=record.get('state_chains',[])
    if not isinstance(chains,list) or not chains:issues.append('state_chains: at least one key explanation chain required')
    else:
        for i,c in enumerate(chains):
            if not isinstance(c,dict):raise ValueError('state chain must be an object')
            if any(not nonempty(c.get(k)) for k in ('object_id','before','change','after','meaning')):
                issues.append(f'state_chains[{i}]: identity, states and meaning required')
            if c.get('status')!='passed':issues.append(f'state_chains[{i}]: not passed')
            artifact(c.get('evidence'),f'state_chains[{i}].evidence')
    scan_path=artifact(record.get('static_scan'),'static_scan')
    scan=None
    if scan_path:
        scan=json.loads(scan_path.read_text(encoding='utf-8'))
        if scan.get('video_sha256')!=record.get('video',{}).get('sha256'):
            issues.append('static_scan: belongs to a different video version')
        spans=scan.get('low_change_spans')
        if not isinstance(spans,list):issues.append('static_scan: invalid spans')
        else:
            reviews=record.get('hold_reviews',[])
            if not isinstance(reviews,list):raise ValueError('hold_reviews must be array')
            for i,span in enumerate(spans):
                matches=[r for r in reviews if isinstance(r,dict) and r.get('scan_span_index')==i]
                if len(matches)!=1:issues.append(f'hold {i}: exactly one review required');continue
                r=matches[0]
                if r.get('status')!='passed' or r.get('decision') not in ('justified_reading','meaningful_change_verified') or not nonempty(r.get('reason')):
                    issues.append(f'hold {i}: unresolved or unjustified')
                artifact(r.get('evidence'),f'hold_reviews[{i}].evidence')
    if editorial:
        plan_path=artifact(record.get('visual_plan'),'visual_plan')
        if plan_path:
            import importlib.util
            spec=importlib.util.spec_from_file_location('npv_visual_plan',Path(__file__).with_name('check_visual_plan.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            check_plan=module.check
            plan_result=check_plan(json.loads(plan_path.read_text(encoding='utf-8')),plan_path.parent)
            issues += ['visual_plan: '+issue for issue in plan_result['issues']]
        transitions=record.get('transition_reviews')
        if not isinstance(transitions,list) or not transitions:
            issues.append('transition_reviews: rendered boundary reviews required')
        else:
            for i,t in enumerate(transitions):
                if not isinstance(t,dict):raise ValueError('transition review must be object')
                if t.get('status')!='passed' or any(not nonempty(t.get(k)) for k in ('from','to','effect','reviewer','notes')):
                    issues.append(f'transition_reviews[{i}]: unresolved or incomplete')
                hashes=[t.get(k,{}).get('sha256') for k in ('before','middle','after') if isinstance(t.get(k),dict)]
                if t.get('effect')!='cut' and len(set(hashes))<2:issues.append(f'transition_reviews[{i}]: non-cut evidence cannot be all identical')
                for key in ('before','middle','after'):
                    image_path=artifact(t.get(key),f'transition_reviews[{i}].{key}')
                    if image_path:
                        try:
                            from PIL import Image
                            with Image.open(image_path) as im:im.verify()
                        except (OSError,ValueError):issues.append(f'transition_reviews[{i}].{key}: decodable frame image required')
                a,b=t.get('start'),t.get('end')
                if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (a,b)) or not 0<=a<b<=duration:
                    issues.append(f'transition_reviews[{i}]: invalid timing')
            if plan_path:
                planned=json.loads(plan_path.read_text())['transitions']
                expected=[(t['from'],t['to']) for t in planned]
                if len(transitions)!=len(expected):issues.append('transition_reviews: count differs from planned boundaries')
                for pair in expected:
                    matching=[t for t in transitions if (t.get('from'),t.get('to'))==pair]
                    if len(matching)!=1:issues.append(f'transition_reviews: missing/duplicate {pair}')
                    elif matching[0]['effect']!=next(t['effect'] for t in planned if (t['from'],t['to'])==pair):issues.append(f'transition_reviews: wrong effect {pair}')
    findings=record.get('findings')
    if not isinstance(findings,list):raise ValueError('findings must be an array')
    for i,f in enumerate(findings):
        if not isinstance(f,dict) or f.get('status') not in STATUSES or not nonempty(f.get('description')):
            raise ValueError('each finding needs description and valid status')
        if 'blocking' in f and not isinstance(f['blocking'],bool):raise ValueError('finding.blocking must be boolean')
        if f.get('blocking',True) and f['status']!='passed':issues.append(f'finding {i}: unresolved blocking issue')
        elif f['status']!='passed':disclosures.append(f['description'])
    return {'schema_version':1,'evidence_record_validated':True,'aesthetics_independently_assessed':False,
            'formal_delivery_allowed':not issues,'issues':issues,'disclosures':disclosures,
            'notice':'This validates recorded evidence and hashes, not truth of reviewer claims. Review final timed media; never fabricate passed statuses.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('record',type=Path);p.add_argument('--output',type=Path);p.add_argument('--require-profile',choices=['editorial-v4'])
    a=p.parse_args()
    try:
        result=check(json.loads(a.record.read_text(encoding='utf-8')),a.record.parent,a.require_profile)
        payload=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if a.output:
            with a.output.open('x',encoding='utf-8') as f:f.write(payload)
        else:sys.stdout.write(payload)
    except (ValueError,OSError,KeyError) as e:p.exit(2,f'check_acceptance: {e}\n')
    return 0 if result['formal_delivery_allowed'] else 1
if __name__=='__main__':sys.exit(main())
