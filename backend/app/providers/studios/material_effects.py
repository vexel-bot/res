"""Isolated local workers, checksum-pinned weights and host-wide memory lease."""
import json
import os
import importlib.util
from pathlib import Path
import subprocess
import sys
import time

from . import timeline_ffmpeg as ff
from .heavy_media_lease import heavy_media_lease

ROOT=Path(__file__).resolve().parents[4]
WORKER=ROOT/"workers"/"material-effects"


def capability():
    if not (WORKER/"models.lock.json").is_file():
        return {"localOnly":True,"paidFallbackEnabled":False,"segmentationAvailable":False,"generativeWeightsInstalled":False,
                "qualification":"unavailable","maxClipSeconds":12,"note":"O pacote de efeitos locais ainda não foi instalado neste servidor."}
    manifest=json.loads((WORKER/"models.lock.json").read_text())
    matte=WORKER/manifest["rvm"]["file"]
    diffusion=ROOT/"workers"/"media-generation-local"/".model-cache"/"profiles"/manifest["diffusion"]["profile"]/manifest["diffusion"]["repository"].replace("/","--")
    runtime=all(importlib.util.find_spec(name) for name in ("onnxruntime","numpy","cv2"))
    diffusion_python=ROOT/"workers"/"media-generation-local"/".venv"/("Scripts/python.exe" if sys.platform=="win32" else "bin/python")
    return {"localOnly":True,"paidFallbackEnabled":False,"segmentationAvailable":runtime and matte.is_file() and matte.stat().st_size==manifest["rvm"]["sizeBytes"],
        "generativeWeightsInstalled":diffusion_python.is_file() and (diffusion/"unet"/"diffusion_pytorch_model.fp16.safetensors").is_file(),
        "qualification":"experimental","maxClipSeconds":12,"note":"A execução verifica checksums e recursos; resultados exigem revisão de bordas e coerência."}


def run_worker(python,script,request,directory,is_cancelled,timeout):
    request_file=directory/(script+"-request.json")
    request_file.write_text(json.dumps(request),encoding="utf-8")
    with (directory/(script+".log")).open("wb") as log:
        allowed={"SYSTEMROOT","WINDIR","PATH","TEMP","TMP","USERPROFILE","LOCALAPPDATA","APPDATA","PROGRAMDATA",
                 "PATHEXT","COMSPEC","NUMBER_OF_PROCESSORS","PROCESSOR_ARCHITECTURE","CUDA_PATH","CUDA_MODULE_LOADING"}
        environment={key:value for key,value in os.environ.items() if key.upper() in allowed}
        environment.update(PYTHONUNBUFFERED="1",PYTHONIOENCODING="utf-8",OMP_NUM_THREADS="2",MKL_NUM_THREADS="2")
        executable=getattr(sys,"_base_executable",sys.executable)
        # Avoid nesting Windows' virtualenv launcher inside a server worker.
        # Activate only the explicitly selected runtime's site-packages.
        site_path=Path(python).parents[1]/("Lib/site-packages" if os.name=="nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
        bootstrap="import sys,site,runpy;site.addsitedir(sys.argv.pop(1));sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
        command=([str(python),str(WORKER/(script+".py")),str(request_file)] if script=="generate" else
                 [str(executable),"-c",bootstrap,str(site_path),str(WORKER/(script+".py")),str(request_file)])
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=environment,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        started=time.monotonic()
        try:
            while process.poll() is None:
                if is_cancelled():
                    raise ValueError("material_effect_cancelled")
                if time.monotonic()-started>timeout:
                    raise ValueError("material_effect_timeout")
                time.sleep(.5)
            if process.returncode:
                # Keep bounded diagnostic codes. Never expose full environment or paths.
                tail=(directory/(script+".log")).read_text(errors="replace")[-1200:]
                raise ValueError("material_effect_worker_failed:"+tail)
        finally:
            if process.poll() is None:
                if os.name=="nt":
                    subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
                else:
                    process.kill()
                process.wait(timeout=15)


def prepare(source,directory,request,execution_id,progress,is_cancelled):
    from .ffmpeg_utility import FFmpegUtility
    from ...config import get_settings
    with heavy_media_lease("material_effect",execution_id):
        # Matching time base and geometry avoid a moving matte drifting from its source.
        args=["-v","error","-nostdin","-y","-ss",str(request.start_seconds),"-i",str(source),"-t",str(request.duration_seconds),
              "-vf","fps=24,scale=640:640:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1",
              "-c:v","libx264","-crf","16","-threads","2","-c:a","aac","-map","0:v:0","-map","0:a?",str(directory/"source.mp4")]
        FFmpegUtility(ff.tool("ffmpeg"),get_settings().ffmpeg_timeout_seconds)._run(args,directory,is_cancelled)
        progress(12)
        payload={"source":str(directory/"source.mp4"),"directory":str(directory),"frames":request.duration_seconds*24,"ffmpeg":ff.tool("ffmpeg"),
                 "operation":request.operation,"preserveInteractionArea":request.preserve_interaction_area}
        run_worker(sys.executable,"matte",payload,directory,is_cancelled,600)
        progress(45)
        report={"segmentation":json.loads((directory/"matte-report.json").read_text())}
        if request.operation!="segment_person":
            geometry={**payload, **{k:report["segmentation"][k] for k in ("width","height")}}
            run_worker(sys.executable,"warp_plate",{**geometry,"checkOnly":True},directory,is_cancelled,90)
            report["camera"]=json.loads((directory/"camera-report.json").read_text())
            if not report["camera"]["applied"]:
                progress(70)
                return report
            python=ROOT/"workers"/"media-generation-local"/".venv"/("Scripts/python.exe" if sys.platform=="win32" else "bin/python")
            if not python.is_file():
                raise ValueError("material_effect_diffusion_runtime_missing")
            run_worker(python,"generate",{**payload,"operation":request.operation,"prompt":request.prompt,"seed":request.seed,"strength":request.strength},directory,is_cancelled,900)
            report["generation"]=json.loads((directory/"generation-report.json").read_text())
            if request.operation=="localized_edit":
                from PIL import Image,ImageDraw,ImageFilter,ImageChops
                generated=Image.open(directory/"generated.png").convert("RGBA")
                alpha=Image.new("L",generated.size)
                x,y,w,h=request.region
                bounds=(round(x*generated.width),round(y*generated.height),round((x+w)*generated.width)-1,round((y+h)*generated.height)-1)
                ImageDraw.Draw(alpha).rectangle(bounds,fill=255)
                inset=max(1,min(8,(bounds[2]-bounds[0])//6,(bounds[3]-bounds[1])//6))
                soft=Image.new("L",generated.size)
                ImageDraw.Draw(soft).rectangle((bounds[0]+inset,bounds[1]+inset,bounds[2]-inset,bounds[3]-inset),fill=255)
                alpha=ImageChops.multiply(alpha,soft.filter(ImageFilter.GaussianBlur(inset)))
                generated.putalpha(alpha)
                generated.save(directory/"generated.png")
            run_worker(sys.executable,"warp_plate",geometry,directory,is_cancelled,180)
            report["camera"]=json.loads((directory/"camera-report.json").read_text())
        progress(70)
        return report
