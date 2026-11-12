"""Inspect actual exports and build timestamped evidence sheets; never calls an API."""

import argparse
import json
import math
import shutil
import subprocess
from array import array
from collections import Counter
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw


def run(tool, args):
    return subprocess.run([shutil.which(tool),"-v","error",*args],capture_output=True,check=True,
        timeout=60,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)).stdout


def inspect(video, directory):
    directory.mkdir(parents=True,exist_ok=True)
    data=json.loads(run("ffprobe",["-show_format","-show_streams","-of","json",str(video)]))
    stream=next(s for s in data["streams"] if s["codec_type"]=="video")
    a,b=map(int,stream["avg_frame_rate"].split('/'));fps=a/b
    raw=run("ffmpeg",["-nostdin","-i",str(video),"-an","-vf","scale=96:54", "-c:v","rawvideo",
        "-threads","1","-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
    size=96*54*3
    empty=[]
    for frame in range(len(raw)//size):
        rgb=raw[frame*size:(frame+1)*size]
        colors=Counter((r//12,g//12,b//12) for r,g,b in zip(rgb[::3],rgb[1::3],rgb[2::3],strict=True))
        if max(colors.values())/(size/3) >= .995:
            empty.append(frame)
    pcm=array("h",run("ffmpeg",["-nostdin","-i",str(video),"-vn","-ac","1","-ar","8000","-f","s16le","pipe:1"]))
    rms=math.sqrt(sum(x*x for x in pcm)/len(pcm))/32768 if pcm else 0
    moments=[.5,2.5,4.5,6.5,8.5,10.5,12.5,14.5,16.5,17.5]
    moments=[t for t in moments if t<float(data["format"]["duration"])]
    sheet=Image.new("RGB",(270*5,510*math.ceil(len(moments)/5)),"#252525")
    draw=ImageDraw.Draw(sheet)
    for index,second in enumerate(moments):
        target=directory/f"frame-{second:g}.jpg"
        run("ffmpeg",["-nostdin","-y","-i",str(video),"-ss",str(second),"-an","-frames:v","1",
            "-vf","scale=270:480:force_original_aspect_ratio=decrease","-q:v","2",str(target)])
        with Image.open(target) as frame:
            x,y=index%5*270,index//5*510
            sheet.paste(frame,(x,y+24));draw.text((x+8,y+6),f"{second:.1f} s",fill="white")
    sheet.save(directory/"quadros.jpg",quality=90)
    report={"file":str(video.resolve()),"checksumSha256":sha256(video.read_bytes()).hexdigest(),
        "durationSeconds":float(data["format"]["duration"]),"width":stream["width"],"height":stream["height"],
        "framesDecoded":len(raw)//size,"fps":fps,"nearUniformFrames":empty,
        "audio":{"present":bool(pcm),"rms":round(rms,6),"peak":round(max(map(abs,pcm),default=0)/32768,6)},
        "coverage":{"technicalFrames":"all_decoded_frames_at_96x54","editorialStillsSeconds":moments,
            "audioIntelligibility":"not_claimed_no_narration","spectatorComprehension":"not_tested"}}
    (directory/"verificacao.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("video");parser.add_argument("output");args=parser.parse_args()
    inspect(Path(args.video),Path(args.output))
