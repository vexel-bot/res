"""Local native operation probes. No database, model/provider calls or production edits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.providers.studios.craft import call_engine, require_capability
from app.providers.studios.media_runtime import resolve_tool
from app.services.studios.craft import require_command_success

BASE='''var c=app.project.activeItem;while(c.numLayers)c.layer(1).remove();
c.duration=1;c.frameRate=30;c.width=320;c.height=320;
var bg=c.layers.addSolid([0.1,0.12,0.16],"background",320,320,1,1);
var l=c.layers.addSolid([1,0.4,0.25],"subject",120,120,1,1);
l.property("ADBE Transform Group").property("ADBE Position").setValue([160,160,0]);
'''
CASES={
 'baseline':'',
 'mask':'''var m=l.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
var s=new Shape();s.vertices=[[0,0],[60,0],[60,120],[0,120]];s.closed=true;
s.inTangents=[[0,0],[0,0],[0,0],[0,0]];s.outTangents=s.inTangents;
m.property("ADBE Mask Shape").setValue(s);''',
 'opacity':'l.property("ADBE Transform Group").property("ADBE Opacity").setValue(50);',
 'blend':'l.blendingMode=BlendingMode.MULTIPLY;',
 'shadow':'l.property("ADBE Effect Parade").addProperty("Drop Shadow");',
 'gradient':'l.property("ADBE Effect Parade").addProperty("ADBE Ramp");',
 'typography':'''l.remove();var t=c.layers.addText("MOTION");
var p=t.property("ADBE Text Properties").property("ADBE Text Document");var d=p.value;
d.fontSize=44;d.fillColor=[1,1,1];p.setValue(d);
t.property("ADBE Transform Group").property("ADBE Position").setValue([40,170,0]);''',
 'typography_centered':'''l.remove();var t=c.layers.addText("MOTION");
var p=t.property("ADBE Text Properties").property("ADBE Text Document");var d=p.value;
d.fontSize=44;d.fillColor=[1,1,1];p.setValue(d);
var rect=t.sourceRectAtTime(0,false);
t.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([rect.left+rect.width/2,rect.top+rect.height/2,0]);
t.property("ADBE Transform Group").property("ADBE Position").setValue([160,160,0]);''',
 'mask_animated':'''var m=l.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
function rect(w){var s=new Shape();s.vertices=[[0,0],[w,0],[w,120],[0,120]];s.closed=true;
s.inTangents=[[0,0],[0,0],[0,0],[0,0]];s.outTangents=s.inTangents;return s;}
m.property("ADBE Mask Shape").setValueAtTime(0,rect(1));m.property("ADBE Mask Shape").setValueAtTime(1,rect(120));''',
 'depth_rotation':'''l.threeDLayer=true;
l.property("ADBE Transform Group").property("ADBE Rotate Y").setValue(55);''',
 'camera':'''l.threeDLayer=true;var cam=c.layers.addCamera("camera",[160,160]);
cam.property("ADBE Transform Group").property("ADBE Position").setValueAtTime(0,[160,160,-800]);
cam.property("ADBE Transform Group").property("ADBE Position").setValueAtTime(1,[300,160,-800]);''',
 'light':'''l.threeDLayer=true;var light=c.layers.addLight("light",[160,160]);
light.property("ADBE Light Options Group").property("ADBE Light Intensity").setValue(0);''',
}

CASES["mask_reverse"] = CASES["mask_animated"].replace(
    "setValueAtTime(0,rect(1))", "setValueAtTime(0,rect(120))"
).replace("setValueAtTime(1,rect(120))", "setValueAtTime(1,rect(1))")
CASES["type_long"] = CASES["typography_centered"].replace('addText("MOTION")', 'addText("NOVA\\nCOLECAO")').replace(
    "d.fontSize=44", "d.fontSize=32"
)
CASES["type_long_motion"] = CASES["type_long"] + """
var position=t.property("ADBE Transform Group").property("ADBE Position");
position.setValueAtTime(0,[160,210,0]);
position.setValueAtTime(0.5,[160,160,0]);
position.setValueAtTime(29/30,[160,160,0]);
"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',nargs='+',choices=list(CASES),help='Named probes; baseline always included')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    original=sha(args.source);source=out/'source.ecproj';shutil.copyfile(args.source,source)
    params={'nativePath':str(source),'media':[],'mediaRoot':str(out)}
    report={'buildId':require_capability('effectcraft')['buildId'],'sourceSha256':original,
            'paidCalls':0,'cases':{},'limits':'Isolated default-effect probes, not full qualification or aesthetic approval. No listening or physical CGI demonstrated.'}
    selected={k:v for k,v in CASES.items() if not args.cases or k=='baseline' or k in args.cases}
    for name,operation in selected.items():
        item={'status':'not_run'};report['cases'][name]=item;start=time.monotonic()
        code=BASE+operation+'\nJSON.stringify({probe:"'+name+'",layers:c.numLayers});'
        (out/f'{name}.jsx').write_text(code,encoding='utf8')
        native=out/f'{name}.ecproj'
        try:
            result=call_engine('effectcraft','engine.execute',{**params,'outputPath':str(native),
                'commands':[{'id':'script.run','params':{'code':code}}]})
            item['execution']=result;require_command_success(result)
            inspection=call_engine('effectcraft','project.open',{**params,'nativePath':str(native)})
            (out/f'{name}-inspection.json').write_text(json.dumps(inspection,indent=2),encoding='utf8')
            item.update(nativeSha256=sha(native),frames=[])
            for f in (0,15,29):
                target=out/f'{name}-{f}.png'
                call_engine('effectcraft','render.frame',{**params,'nativePath':str(native),
                    'outputPath':str(target),'frame':f,'format':'png','maxSide':320})
                item['frames'].append({'frame':f,'sha256':sha(target)})
            item['status']='rendered_unobserved'
        except Exception as exc:
            item.update(status='execution_failed',error=str(exc))
        item['seconds']=round(time.monotonic()-start,3)
        report['sourcePreserved']=sha(args.source)==original
        (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        print(json.dumps({'case':name,'status':item['status']}),flush=True)
    gallery=Image.new('RGB',(320*3,350*len(selected)), '#15171c');draw=ImageDraw.Draw(gallery)
    for row,(name,item) in enumerate(report['cases'].items()):
        draw.text((8,row*350+8),name+' / '+item['status'],fill='white')
        if item['status']!='rendered_unobserved':continue
        diffs=[]
        for col,f in enumerate((0,15,29)):
            im=Image.open(out/f'{name}-{f}.png').convert('RGB');gallery.paste(im,(col*320,row*350+30))
            baseline=Image.open(out/f'baseline-{f}.png').convert('RGB')
            diffs.append(ImageStat.Stat(ImageChops.difference(im,baseline)).mean)
        item['meanRgbDifferenceFromBaseline']=diffs
        item['temporalPixelChange']=item['frames'][0]['sha256']!=item['frames'][-1]['sha256']
        if name.startswith("mask_"):
            revealed = []
            for frame in (0, 15, 29):
                with Image.open(out / f"{name}-{frame}.png") as image:
                    revealed.append(sum(r > 200 and 60 < g < 130 and b < 100
                                        for r, g, b in image.convert("RGB").getdata()))
            item["revealedPixels"] = revealed
            if name == "mask_reverse":
                item["visualCheck"] = "pass" if revealed[0] > revealed[1] > revealed[-1] else "fail"
            else:
                item["visualCheck"] = "pass" if revealed[0] < revealed[1] < revealed[-1] else "fail"
        if name == "type_long_motion":
            line_counts = []
            for frame in (0, 15, 29):
                with Image.open(out / f"{name}-{frame}.png") as image:
                    bright = image.convert("L").point(lambda value: 255 if value > 190 else 0)
                    rows = [y for y in range(bright.height) if bright.crop((0, y, bright.width, y + 1)).getbbox()]
                line_counts.append(sum(index == 0 or row - rows[index - 1] > 1 for index, row in enumerate(rows)))
            item["renderedLineCounts"] = line_counts
            item["visualCheck"] = "pass" if (
                line_counts == [2, 2, 2] and item["temporalPixelChange"]
                and item["frames"][1]["sha256"] == item["frames"][-1]["sha256"]
            ) else "fail"
    gallery.save(out/'gallery.png')
    # Export parity on the moving-camera fixture, falling back only explicitly to the baseline fixture.
    chosen='camera' if report['cases'].get('camera',{}).get('status')=='rendered_unobserved' else 'baseline'
    parity={'fixture':chosen,'status':'not_run'};report['exportParity']=parity
    try:
        video=out/'technical-export.mp4'
        call_engine('effectcraft','render.export',{**params,'nativePath':str(out/f'{chosen}.ecproj'),
            'outputPath':str(video),'format':'mp4'})
        probe=subprocess.run([resolve_tool('ffprobe'),'-v','error','-select_streams','v:0','-show_frames',
            '-show_streams','-of','json',str(video)],capture_output=True,check=True,text=True)
        data=json.loads(probe.stdout);(out/'export-probe.json').write_text(probe.stdout,encoding='utf8')
        frames=data['frames'];parity.update(videoSha256=sha(video),decodedFrames=len(frames),
            fps=data['streams'][0]['avg_frame_rate'],timestamps=[f.get('best_effort_timestamp_time') for f in frames],comparisons=[])
        for f in (0,15,29):
            target=out/f'decoded-{f}.png'
            subprocess.run([resolve_tool('ffmpeg'),'-v','error','-i',str(video),'-vf',f'select=eq(n\\,{f})',
                '-frames:v','1',str(target)],check=True,capture_output=True)
            diff=ImageChops.difference(Image.open(target).convert('RGB'),Image.open(out/f'{chosen}-{f}.png').convert('RGB'))
            parity['comparisons'].append({'frame':f,'meanAbsoluteRgbDifference':ImageStat.Stat(diff).mean})
        parity['status']='measured_requires_interpretation'
    except Exception as exc:parity.update(status='failed',error=str(exc))
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    assert report['sourcePreserved']


if __name__=='__main__':main()
