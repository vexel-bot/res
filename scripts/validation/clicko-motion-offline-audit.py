"""Audit existing session logs without model calls or changing historical receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.services.studios.craft_motion_validation import receipt, cost_breakdown

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--evidence',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
source=args.evidence.read_bytes(); raw=json.loads(source); state=raw.get('result',raw)
scripts=[]
for t in state.get('tools',[]):
    if t['name']=='run_motion_script':
        commands=[{'id':'script.run','params':{'code':t['input']['code']}}]
    elif t['name']=='edit_project':
        commands=t.get('input',{}).get('commands',[])
    else:
        continue
    if not t.get('ok'):
        continue
    scripts.append({'toolUseId':t.get('toolUseId'),'draftBatch':t.get('draftBatch'),
                    'audit':receipt(commands,{}),
                    'limits':'Historical log audit only. No historical configuration/visual approval is inferred.'})
out={'schemaVersion':'craft.motion-offline-audit.v1','sourceSha256':hashlib.sha256(source).hexdigest(),
     'costs':cost_breakdown(state),'scripts':scripts,
     'externalReferenceInspections':len(state.get('referenceInspections',[])),
     'compactions':state.get('contextCompactions',0),'paidCalls':0,'historicalReceiptsModified':False}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'auditedOperations':len(scripts),'silentExceptionRiskOperations':sum(any('Empty exception' in r for r in s['audit']['risks']) for s in scripts),'paidCalls':0}))
