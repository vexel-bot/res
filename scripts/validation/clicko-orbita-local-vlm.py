"""Run the cached visual model on the Craft evidence. No network or API calls."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_PROGRESS_BARS="1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers/media-generation-local"))


def main(output):
    import torch
    from PIL import Image
    from transformers import AutoModelForMultimodalLM, AutoProcessor
    from local_material_inspector import MODEL_ID, MODEL_REVISION, _generate

    device = "cuda" if torch.cuda.is_available() and torch.cuda.mem_get_info()[0] > 1_600_000_000 else "cpu"
    if device == "cpu":
        torch.set_num_threads(min(4, os.cpu_count() or 1))
    processor = AutoProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)
    processor.image_processor.do_image_splitting = False
    model = AutoModelForMultimodalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True,
        dtype=torch.float16 if device == "cuda" else torch.float32).to(device).eval()
    def answer(path, prompt, tokens=16):
        start = time.monotonic()
        with Image.open(path) as opened:
            image = opened.convert("RGB")
        raw = _generate(model, processor, image, prompt, tokens)
        return {"answer": raw, "seconds": round(time.monotonic() - start, 3), "image": path.name}

    question = ('Look at the top of the video. Does a straight bright horizontal edge actually cross '
                'the letters of the white top headline, touching the letters rather than sitting below them? '
                'Answer YES, NO, or UNSURE. Judge only the image.')
    results = {"model": MODEL_ID, "revision": MODEL_REVISION, "device": device, "apiSpendUsd": 0, "detection": {}}
    # These prompts and thresholds are identical for positives and negatives.
    for name in ["original-collision", "original-clean", "repaired-same-time", "repaired-title"]:
        results["detection"][name] = answer(output / (name + ".png"), question)
    if (output / "lume-seed.png").exists():
        case = json.loads((ROOT / "benchmarks/studios/orbita/transferencia-casa-lume-escolhas.json").read_text(encoding="utf-8"))
        options = "\n".join(f"{key}: {item['description']}" for key, item in case["options"].items())
        rule = ("Keep important lettering readable during movement. Separate the text from a crossing edge in space or time. "
                "Respect the order of actions in the new brief and keep its own kind of motion.")
        prompt = f"Choose one native editing operation for the pictured library.\nBriefing: {case['briefing']}\n{options}\nAnswer just A, B or C, then one short reason."
        demo = ("Worked demonstration from a different project: the ORBITA camera moved from 372% to 100%. "
                "A frame crossed the title at 2.625s. We hid the lettering while the frame crossed it, slowed the scale "
                "change and restored the full phrase above the settled screen. Intermediate rendered frames showed "
                "clear text before and after the movement. The camera zoom was specific to ORBITA.\n")
        results["transfer"] = {
            "ruleOnly": answer(output / "lume-seed.png", rule + "\n" + prompt, 32),
            "ruleAndDemonstration": answer(output / "lume-seed.png", rule + "\n" + demo + prompt, 32),
        }
    (output / "ia-local-resultados.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output.resolve())
