"""Measure every frame of an existing video locally; never infer cause from frame activity."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.providers.studios.media_runtime import resolve_tool


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();before=hashlib.sha256(args.video.read_bytes()).hexdigest()
    probe=subprocess.run([resolve_tool('ffprobe'),'-v','error','-select_streams','v:0','-show_frames',
        '-show_streams','-of','json',str(args.video)],capture_output=True,check=True,text=True)
    data=json.loads(probe.stdout);stream=data['streams'][0];frames=data['frames'];w=96
    h=round(stream['height']*w/stream['width']);stride=w*h*3
    # Low-resolution signal analysis only, not finish/detail inspection.
    raw=subprocess.run([resolve_tool('ffmpeg'),'-v','error','-i',str(args.video),'-map','0:v:0',
        '-vf',f'scale={w}:{h}','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
        capture_output=True,check=True).stdout
    if len(raw)!=len(frames)*stride:raise ValueError('decoded_frame_count_mismatch')
    changes=[];previous=None
    for i in range(len(frames)):
        im=Image.frombytes('RGB',(w,h),raw[i*stride:(i+1)*stride])
        if previous is not None:changes.append(sum(ImageStat.Stat(ImageChops.difference(im,previous)).mean)/3)
        previous=im
    timestamps=[float(f['best_effort_timestamp_time']) for f in frames]
    periods=[b-a for a,b in zip(timestamps,timestamps[1:])]
    quiet=[];start=None
    for i,value in enumerate(changes+[float('inf')],1):
        if value<.2 and start is None:start=i-1
        elif value>=.2 and start is not None:
            if i-1-start>=3:quiet.append({'startFrame':start,'endFrame':i-1,
                'startSeconds':timestamps[start],'endSeconds':timestamps[i-1]})
            start=None
    result={'videoSha256':before,'fps':stream['avg_frame_rate'],'decodedFrames':len(frames),
        'timestampPeriodMin':min(periods),'timestampPeriodMax':max(periods),
        'identicalAdjacentLowResolutionFrames':sum(v==0 for v in changes),
        'lowChangeIntervals':quiet,'meanAbsoluteRgbChangePerFrame':changes,'analysisResolution':[w,h],
        'paidCalls':0,'sourcePreserved':hashlib.sha256(args.video.read_bytes()).hexdigest()==before,
        'limits':'Low-resolution activity is not native parameter evidence or playback FPS. Holds may be intentional; compression affects pixels. No aesthetic or causal verdict.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('meanAbsoluteRgbChangePerFrame','lowChangeIntervals')}))


if __name__=='__main__':main()
