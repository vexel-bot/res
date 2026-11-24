"""Local synthetic audio synchronization proof, not listening or sound design approval."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import wave

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.providers.studios.craft import call_engine, require_capability
from app.services.studios.craft import require_command_success


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--envelope',action='store_true',help='Also test keyed gain at the two attacks')
    p.add_argument('--from-silence',action='store_true',help='Start the gain envelope muted; requires --envelope')
    args=p.parse_args()
    if args.from_silence and not args.envelope:p.error('--from-silence requires --envelope')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    before=hashlib.sha256(args.source.read_bytes()).hexdigest()
    source=out/'source.ecproj';shutil.copyfile(args.source,source)
    rate=48000;samples=[]
    for i in range(rate):
        t=i/rate;active=any(start<=t<start+.02 for start in (.1,.6))
        samples.append(int(12000*math.sin(2*math.pi*1000*t)) if active else 0)
    with wave.open(str(out/'signal.wav'),'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(struct.pack('<'+'h'*rate,*samples))
    code='''var c=app.project.activeItem;while(c.numLayers)c.layer(1).remove();
c.duration=1;c.frameRate=30;c.width=64;c.height=64;
var footage=app.project.importFile(new ImportOptions(new File('/job/signal.wav')));
var l=c.layers.add(footage);l.startTime=0.1;l.inPoint=0.1;l.outPoint=0.9;
JSON.stringify({startTime:l.startTime,inPoint:l.inPoint,outPoint:l.outPoint});'''
    if args.envelope:
        code+='''var gain=l.property("ADBE Audio Group").property("ADBE Audio Levels");
gain.setValueAtTime(0.2,[-6,-6]);gain.setValueAtTime(7/30,[-6,-6]);
gain.setValueAtTime(0.7,[-12,-12]);gain.setValueAtTime(22/30,[-12,-12]);'''
        if args.from_silence:
            code+='gain.setValueAtTime(0.1,[-96,-96]);'
    (out/'audio.jsx').write_text(code,encoding='utf8')
    params={'nativePath':str(source),'mediaRoot':str(out),'media':[]}
    report={'buildId':require_capability('effectcraft')['buildId'],'paidCalls':0,'status':'not_run',
            'fixtureSha256':hashlib.sha256(code.encode()).hexdigest(),
            'limits':'Synthetic signal only. No listening, balance, integration, fades or advertisement sound quality approval.'}
    try:
        native=out/'audio.ecproj'
        result=call_engine('effectcraft','engine.execute',{**params,'outputPath':str(native),
            'commands':[{'id':'script.run','params':{'code':code}}]})
        report['execution']=result;require_command_success(result)
        call_engine('effectcraft','render.export',{**params,'nativePath':str(native),'outputPath':str(out/'export.wav'),'format':'wav'})
        with wave.open(str(out/'export.wav'),'rb') as w:
            channels=w.getnchannels();width=w.getsampwidth();fps=w.getframerate();n=w.getnframes();raw=w.readframes(n)
        if width!=2:raise ValueError('PCM16 analysis requires conversion; exported width='+str(width))
        values=struct.unpack('<'+'h'*(len(raw)//2),raw)
        active=[i for i in range(n) if max(abs(values[i*channels+j]) for j in range(channels))>100]
        starts=[i/fps for index,i in enumerate(active) if index==0 or i-active[index-1]>.005*fps]
        report.update(channels=channels,sampleRate=fps,durationSeconds=n/fps,attackSeconds=starts,
            peak=max(map(abs,values),default=0)/32768,
            synchronization=('pass' if len(starts)==2 and all(abs(a-b)<.003 for a,b in zip(starts,(.2,.7))) else 'fail'),
            status='measured',exportSha256=hashlib.sha256((out/'export.wav').read_bytes()).hexdigest())
        if args.envelope:
            peaks=[max(abs(values[i*channels]) for i in range(round(t*fps),round((t+.02)*fps)))/32768 for t in (.2,.7)]
            expected=[12000/32768*10**(db/20) for db in (-6,-12)]
            report['keyedGain']={'attackPeaks':peaks,'expectedPeaks':expected,
                'status':'pass' if all(abs(a-b)<.003 for a,b in zip(peaks,expected)) else 'fail'}
    except Exception as exc:report.update(status='failed',error=str(exc))
    report['sourcePreserved']=hashlib.sha256(args.source.read_bytes()).hexdigest()==before
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='execution'}))
    return 0 if report.get('synchronization')=='pass' and report.get('keyedGain',{}).get('status','pass')=='pass' and report['sourcePreserved'] else 1


if __name__=='__main__':raise SystemExit(main())
