"""Run isolated, unpaid pixel/signal calibration and genuine engine conformance."""
import argparse
import json
import os
import subprocess
import sys
import time
import wave
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.studios.craft_quality_checks import (
    inspect_audio, inspect_flash, inspect_marker, inspect_occlusion, inspect_text_ink, score_controls, sha256,
)


def known_flash_probe(output, archive):
    """Render the existing source and a one-line corrected copy, never the baseline itself."""
    before, after = output/'flash-before', output/'flash-after'
    for directory in (before,after):
        directory.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                target=(directory/name).resolve()
                if not target.is_relative_to(directory.resolve()):
                    raise ValueError('quality_archive_path_invalid')
            z.extractall(directory)
    source=after/'src/orbita.js'
    original=source.read_text(encoding='utf-8')
    corrected = original
    for expression in ('${0.85 * wh}', '${0.9 * f * f}'):
        assert corrected.count(expression) == 1
        corrected = corrected.replace(expression, '${0}')
    source.write_text(corrected,encoding='utf-8')
    node=r'''const {chromium}=require('playwright');const {pathToFileURL}=require('node:url');
    (async()=>{const b=await chromium.launch({headless:true});const c=await b.newContext();
    await c.route(/^https?:/,r=>r.abort());const result={browser:b.version(),versions:[]};
    for(const path of process.argv.slice(1)){const p=await c.newPage();await p.goto(pathToFileURL(path).href);
    await p.evaluate(()=>window.ORBITA.ready);const frames=[];
    for(let i=232;i<=267;i++){frames.push(await p.evaluate(frame=>{ORBITA.renderFrame(frame/30);
    const d=document.createElement('canvas');d.width=144;d.height=144;
    d.getContext('2d').drawImage(document.querySelector('canvas'),0,0,144,144);
    return {frame,png:d.toDataURL().split(',')[1]}},i));}
    result.versions.push(frames);await p.close();}
    console.log(JSON.stringify(result));await b.close()})().catch(e=>{console.error(e.message);process.exitCode=1});'''
    rendered=subprocess.run(['node','-e',node,str(before/'src/orbita.html'),str(after/'src/orbita.html')],
                            cwd=ROOT,capture_output=True,text=True,timeout=120)
    if rendered.returncode:
        return {'status':'fail','error':rendered.stderr[-1000:]}
    import base64
    from io import BytesIO
    samples=json.loads(rendered.stdout)
    reports=[]
    for name,version in zip(('before','after'),samples['versions']):
        decoded=[(s['frame'],Image.open(BytesIO(base64.b64decode(s['png']))).copy()) for s in version]
        report=inspect_flash(decoded,30)
        for frame,image in decoded:
            if frame in (239,240,250):
                image.save(output/f'known-flash-{name}-{frame}.png')
        reports.append(report)
    return {'status':'pass' if reports[0]['status']=='defect' and reports[1]['status']=='pass' else 'fail',
            'browser':samples['browser'],'fps':30,'startFrame':232,'endFrame':267,'before':reports[0],'after':reports[1],
            'originalCopySha256':sha256(before/'src/orbita.js'),'correctedCopySha256':sha256(source),
            'baselineSourceUnmodified':True,'change':'Leading and trailing full-screen brightness overlays disabled in isolated copy',
            'interpretation':'Local rendering proof for the known brightness event; no aesthetic or complete-film approval'}


def run(output, *, native=True):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    cases = []

    def add(identifier, family, defect, observed, evidence=None):
        cases.append({'id': identifier, 'family': family, 'expectedDefect': defect, 'observed': observed,
                      'evidence': evidence})

    for wrong in (False, True):
        image = Image.new('RGBA',(300,300))
        ImageDraw.Draw(image).rectangle((80 + 5*wrong, 84, 111 + 5*wrong, 115), fill=(255,0,0,255))
        path = output / ('motion-defect.png' if wrong else 'motion-correct.png')
        image.save(path)
        add('motion-' + ('defect' if wrong else 'correct'), 'marker_geometry', wrong,
            inspect_marker(image,(255,0,0),[80,84,112,116]), {'file':path.name,'sha256':sha256(path)})

    font_path = output / 'SpaceGrotesk.ttf'
    archive = ROOT / 'docs/studios/research/2026-11-13-motion-quality-investigation/probes/orbita-runtime-source.zip'
    with zipfile.ZipFile(archive) as z:
        font_path.write_bytes(z.read('src/fonts/SpaceGrotesk.ttf'))
    font = ImageFont.truetype(str(font_path), 19)
    text = 'ÓRBITA\nMostra de curtas\nConfira a programação'
    assert bytes(font.getmask('Ó')) != bytes(font.getmask('O'))
    for wrong in (False, True):
        image = Image.new('RGBA',(300,180))
        ImageDraw.Draw(image).multiline_text((-30 if wrong else 16,16),text,font=font,fill='white',spacing=12)
        path = output / ('text-defect.png' if wrong else 'text-correct.png')
        image.save(path)
        add('text-' + ('defect' if wrong else 'correct'), 'text_ink_clipping', wrong,
            inspect_text_ink(image), {'file':path.name,'sha256':sha256(path),'fontSha256':sha256(font_path),
                                     'sourceText':text,'sourceFont':'Space Grotesk','accentGlyphDistinct':True})

    for wrong in (False, True):
        image = Image.new('RGBA',(100,100))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20,20,70,70),fill=(255,0,0,255))
        draw.rectangle((50,40,80,80),fill=(0,255,0,255))
        if wrong:
            draw.rectangle((20,20,70,70),fill=(255,0,0,255))
        path = output / ('occlusion-defect.png' if wrong else 'occlusion-correct.png')
        image.save(path)
        add('occlusion-' + ('defect' if wrong else 'correct'),'known_occlusion_alpha',wrong,
            inspect_occlusion(image,front_point=(60,60),front_color=(0,255,0),transparent_point=(0,0)),
            {'file':path.name,'sha256':sha256(path)})

    flat = [(i,Image.new('RGB',(144,144),'#161616')) for i in range(24)]
    flash = [(i,Image.new('RGB',(144,144),'white' if 5 <= i <= 6 else '#161616')) for i in range(24)]
    add('flash-correct','wide_area_brightening',False,inspect_flash(flat,30))
    add('flash-defect','wide_area_brightening',True,inspect_flash(flash,30))
    add('flash-intentional','wide_area_brightening',False,inspect_flash(flash,30,intentional=True))

    def sound(path,onset):
        rate = 24000
        t = np.arange(rate) / rate
        s = .3*np.sin(2*np.pi*440*t)*((t>=onset)&(t<onset+.1))
        with wave.open(str(path),'wb') as wav:
            wav.setparams((1,2,rate,0,'NONE','not compressed'))
            wav.writeframes((s*32767).astype('<i2').tobytes())
    correct, shifted = output/'audio-correct.wav', output/'audio-shifted.wav'
    sound(correct,.5)
    sound(shifted,.66)
    add('audio-present','required_audio',False,inspect_audio(correct),{'file':correct.name,'sha256':sha256(correct)})
    add('audio-missing','required_audio',True,inspect_audio(None))
    add('audio-aligned','audio_onset',False,inspect_audio(correct,expected_onset=.5))
    add('audio-shifted','audio_onset',True,inspect_audio(shifted,expected_onset=.5),{'file':shifted.name,'sha256':sha256(shifted)})
    calibration = score_controls(cases)
    receipt = {'schemaVersion':'clicko.local-quality-qualification.v1','apiSpendUsd':0,'newAdvertisementGenerated':False,
               'calibration':calibration,'cases':cases,'thresholds':{'geometryPixels':2,'visualFrames':1,'audioMilliseconds':50},
               'interpretation':'Known fixture classifier calibration, not AI judgment, aesthetic approval or viewer comprehension',
               'unqualified':['photographic person segmentation','physical contact-shadow realism','human reading comfort',
                              'perceptual audio listening','full advertisement quality'],
               'nativeConformance':{'status':'not_run'},'knownFlash':{'status':'not_run'},'elapsedSeconds':None}
    if native:
        environment = {**os.environ,'PYTHONPATH':str(ROOT/'backend'),'CLICKO_TEST_REAL_CRAFT':'1','CLICKO_QUALITY_OUTPUT':str(output)}
        result = subprocess.run([sys.executable,'-m','pytest','backend/tests/test_craft_quality_checks.py','-q'],
                                cwd=ROOT,env=environment,capture_output=True,text=True,timeout=300)
        (output/'qualification-pytest.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        receipt['pytestExitCode']=result.returncode
        native_path=output/'native-conformance.json'
        receipt['nativeConformance']=json.loads(native_path.read_text(encoding='utf-8')) if result.returncode==0 and native_path.is_file() else {'status':'fail','reason':'native_conformance_not_completed'}
        receipt['knownFlash']=known_flash_probe(output,archive)
    receipt['elapsedSeconds']=round(time.monotonic()-started,3)
    receipt['status']='pass' if calibration['status']=='pass' and receipt['nativeConformance']['status']=='pass' and receipt['knownFlash']['status']=='pass' else 'incomplete'
    (output/'qualification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':receipt['status'],'calibration':calibration,'nativeConformance':receipt['nativeConformance']['status'],
                      'knownFlash':receipt['knownFlash']['status'],'elapsedSeconds':receipt['elapsedSeconds'],'apiSpendUsd':0},ensure_ascii=False))
    return 0 if receipt['status']=='pass' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.codex-runtime/clicko-dev/quality-cycle-local')
    parser.add_argument('--skip-native',action='store_true',help='Calibration only; never produces a passing full qualification')
    args=parser.parse_args()
    raise SystemExit(run(args.output.resolve(),native=not args.skip_native))
