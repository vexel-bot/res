"""Replay two local compactions against saved job evidence; never submits a model request."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.services.studios.craft_history import compact_messages
from app.services.studios.craft_motion_validation import cost_breakdown


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();source=args.evidence.read_bytes();raw=json.loads(source);s=raw.get('result',raw)
    context={'instruction':raw.get('request',{}).get('instruction','Recover the existing native draft'),
             'directorContext':s.get('directorContext'),'recoverableEvidenceMode':True}
    batch=s.get('draft',{}).get('batches',0);messages=[];rounds=[]
    for number in (1,2):
        messages=compact_messages(context,s.get('draft',{}),batch,s,messages=messages)
        cp=json.loads(messages[0]['content'][1]['text'])
        original=s.get('directorContext') or {};current=cp.get('directorContext') or {}
        checks={k:current.get(k)==original.get(k) for k in ('currentUserRequirements','latestPlan','issues',
            'preferredCandidateId','revisionHypotheses','approvedPreferences','humanApproval','evidenceIndex')}
        rounds.append({'round':number,'checks':checks,'serializedBytes':len(json.dumps(messages).encode()),
            'presentFields':[k for k in checks if original.get(k) is not None],
            'limits':'Equality validates persistence, not whether the director recalls, follows or judges these facts correctly.'})
    tools=s.get('tools',[]);repeats={}
    for t in tools:
        # Batch distinguishes repeated inspection from necessary reinspection after edits.
        if t.get('name') not in ('inspect_project','review_clip','describe_commands','inspect_reference'):continue
        key=json.dumps([t.get('draftBatch'),t.get('name'),t.get('input')],sort_keys=True)
        repeats.setdefault(key,[]).append(t.get('toolUseId'))
    result={'sourceSha256':hashlib.sha256(source).hexdigest(),'paidCalls':0,'rounds':rounds,
        'costs':cost_breakdown(s),'repeatedIdenticalInspectionGroups':[{'request':json.loads(k),'toolUseIds':v}
            for k,v in repeats.items() if len(v)>1],
        'limits':'Repeat requests are hypotheses of waste, not proven unnecessary calls or measured savings. Historical log is not modified.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
    assert all(all(r['checks'].values()) for r in rounds)
    assert args.evidence.read_bytes()==source
    print(json.dumps({'roundsPassed':2,'paidCalls':0,'repeatGroups':len(result['repeatedIdenticalInspectionGroups'])}))


if __name__=='__main__':main()
