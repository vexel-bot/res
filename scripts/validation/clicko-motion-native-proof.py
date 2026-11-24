"""Disposable local native proof. No DB writes, model calls, or production edits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.providers.studios.craft import call_engine, require_capability
from app.services.studios.craft import require_command_success
from app.services.studios.craft_motion_cadence import cadence

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--all-frames',action='store_true',help='Measure every native frame, not only five samples')
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=False)
source_sha=hashlib.sha256(args.source.read_bytes()).hexdigest()
native=args.output/'source-copy.ecproj';shutil.copyfile(args.source,native)
target=args.output/'proof.ecproj'
code=(ROOT/'benchmarks/studios/motion/native-proof.jsx').read_text(encoding='utf8')
params={'nativePath':str(native),'media':[], 'mediaRoot':str(args.output.resolve())}
cap=require_capability('effectcraft')
r=call_engine('effectcraft','engine.execute',{**params,'outputPath':str(target),
    'commands':[{'id':'script.run','params':{'code':code}}]})
require_command_success(r)
inspection=call_engine('effectcraft','project.open',{**params,'nativePath':str(target)})
(args.output/'inspection.json').write_text(json.dumps(inspection,indent=2),encoding='utf8')
frames=list(range(30)) if args.all_frames else [0,8,15,22,29]
for frame in frames:
    call_engine('effectcraft','render.frame',{**params,'nativePath':str(target),
        'outputPath':str(args.output/f'frame-{frame}.png'),'frame':frame,'format':'png','maxSide':640})
centers=[]
for frame in frames:
    image=Image.open(args.output/f'frame-{frame}.png').convert('RGB')
    positions=[]
    for kind in ['linear','bezier']:
        xs=[x for y in range(image.height) for x in range(image.width)
            if ((lambda rgb: rgb[0]>230 and 70<rgb[1]<140 and rgb[2]<120)(image.getpixel((x,y))) if kind=='linear'
                else (lambda rgb: 110<rgb[0]<190 and 80<rgb[1]<180 and rgb[2]>220)(image.getpixel((x,y))))]
        if not xs:
            raise ValueError('proof_object_not_visible_'+kind)
        positions.append(sum(xs)/len(xs))
    centers.append(positions)
checks={'easeSlowerAtStart':centers[frames.index(8)][1]<centers[frames.index(8)][0],
        'easeFasterNearEnd':centers[frames.index(22)][1]>centers[frames.index(22)][0],
        'positionsMonotonic':all(centers[i+1][j]>=centers[i][j] for i in range(len(frames)-1) for j in range(2))}
temporal=cadence([{'frame':f,'x':centers[i][0],
    'sha256':hashlib.sha256((args.output/f'frame-{f}.png').read_bytes()).hexdigest()}
    for i,f in enumerate(frames)],30,expected_velocity=440) if args.all_frames else None
if temporal:
    checks['linearTrajectory']=temporal['linearTrajectory']=='pass'
report={'buildId':cap['buildId'],'fixtureSha256':hashlib.sha256(code.encode()).hexdigest(),
        'nativeSha256':hashlib.sha256(target.read_bytes()).hexdigest(),'sourcePreserved':hashlib.sha256(args.source.read_bytes()).hexdigest()==source_sha,
        'execution':r,'sampledFrames':frames,'fps':30,'cadence':temporal,
        'status':'rendered_unobserved' if all(checks.values()) else 'technical_failed',
        'rasterChecks':checks,'centroidXLinearBezier':centers,
        'limitations':[('Full one-second fixture only; not historical film coverage' if args.all_frames else 'Discrete frames, not full temporal coverage'),'No aesthetic approval','No lighting, material, shadow, mask, audio or 3D qualification'],
        'paidCalls':0}
(args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:report[k] for k in ['buildId','sourcePreserved','status','paidCalls']}))
raise SystemExit(0 if all(checks.values()) and report['sourcePreserved'] else 1)
