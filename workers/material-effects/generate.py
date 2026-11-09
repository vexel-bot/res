"""Real local diffusion of a background/region. Subject pixels are preserved during composition."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time


def main(request):
    print("generation: loading local runtime",flush=True)
    import faulthandler
    faulthandler.dump_traceback_later(60,repeat=True)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    def offline(*args, **kwargs):
        raise RuntimeError("material_effect_network_disabled")
    socket.socket.connect = offline
    socket.create_connection = offline
    import torch
    print("generation: torch loaded",flush=True)
    from diffusers import StableDiffusionImg2ImgPipeline, DDIMScheduler
    print("generation: diffusion runtime loaded",flush=True)
    from PIL import Image, ImageOps
    root = Path(__file__).resolve().parents[1] / "media-generation-local"
    profile = json.loads((root/"profiles"/"animatediff-lightning-sd15-a.json").read_text())
    repo = next(item for item in profile["repositories"] if item["id"].startswith("stable-diffusion-v1-5/"))
    model = root/".model-cache"/"profiles"/profile["profileId"]/repo["id"].replace("/","--")
    for artifact in repo["artifacts"]:
        digest = hashlib.sha256()
        with (model/artifact["path"]).open("rb") as source:
            for chunk in iter(lambda: source.read(1024*1024),b""):
                digest.update(chunk)
        if digest.hexdigest() != artifact["sha256"]:
            raise ValueError("material_effect_diffusion_checksum_mismatch")
    if not torch.cuda.is_available():
        raise ValueError("material_effect_cuda_unavailable")
    free,total=torch.cuda.mem_get_info()
    if free < 2800*1024*1024:
        raise ValueError("material_effect_vram_insufficient")
    started=time.monotonic()
    print("generation: weights verified; loading pipeline",flush=True)
    torch.set_num_threads(2)
    pipe = StableDiffusionImg2ImgPipeline.from_pretrained(str(model),torch_dtype=torch.float16,variant="fp16",
        local_files_only=True,use_safetensors=True,low_cpu_mem_usage=True)
    if pipe.safety_checker is None:
        raise ValueError("material_effect_safety_checker_required")
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.enable_attention_slicing()
    pipe.vae.enable_slicing()
    pipe = pipe.to("cuda")
    directory=Path(request["directory"])
    source=Image.open(directory/("clean-plate.png" if request["operation"]=="replace_background" else "reference.png")).convert("RGB")
    size=tuple(max(64,round(d/ max(source.size)*512/8)*8) for d in source.size)
    generator=torch.Generator(device="cuda").manual_seed(request["seed"])
    with torch.inference_mode():
        result=pipe(prompt=request["prompt"],image=ImageOps.fit(source,size),strength=request["strength"],num_inference_steps=30,
            guidance_scale=7.5,negative_prompt="people, human, person, face, body, text, watermark, logo, distorted architecture, blurry",
            generator=generator)
    if result.nsfw_content_detected and any(result.nsfw_content_detected):
        raise ValueError("material_effect_candidate_rejected")
    generated=result.images[0].resize(source.size,Image.Resampling.LANCZOS)
    generated.save(directory/"generated.png")
    report={"model":"stable-diffusion-v1-5","revision":repo["revision"],"operation":"image_to_image",
        "seed":request["seed"],"strength":request["strength"],"steps":30,"generationSize":list(size),
        "seconds":round(time.monotonic()-started,3),"peakCudaAllocatedBytes":torch.cuda.max_memory_allocated(),
        "networkDisabled":True,"externalCostUsd":0,"safetyCheckerEnabled":pipe.safety_checker is not None,"reviewRequired":True}
    (directory/"generation-report.json").write_text(json.dumps(report,indent=2))
    return report


if __name__ == "__main__":
    print(json.dumps(main(json.loads(Path(sys.argv[1]).read_text()))))
