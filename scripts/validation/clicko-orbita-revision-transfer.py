"""Probe transfer with cached visual inference and an actual Clicko capture."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_PROGRESS_BARS="1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers/media-generation-local"))


def main(output, positive, interface):
    import torch
    from PIL import Image, ImageOps
    from transformers import AutoModelForMultimodalLM, AutoProcessor
    from local_material_inspector import MODEL_ID, MODEL_REVISION, _generate

    device = "cuda" if torch.cuda.is_available() and torch.cuda.mem_get_info()[0] > 1_600_000_000 else "cpu"
    torch.set_num_threads(min(3, os.cpu_count() or 1))
    processor = AutoProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)
    processor.image_processor.do_image_splitting = False
    model = AutoModelForMultimodalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True,
        dtype=torch.float16 if device == "cuda" else torch.float32).to(device).eval()

    example = Image.new("RGB", (360, 320), "#101520")
    for i, n in enumerate((350, 438)):
        sample = ImageOps.contain(Image.open(output / f"preview-{n}.png").convert("RGB"), (180, 320))
        example.paste(sample, (i*180, 0))
    example.save(output / "transferencia-exemplo.jpg", quality=90)
    cases = [
        ("biblioteca", positive, "A", "A library ad: the sliding doors open to reveal the library sign. A: Reveal the sign after the doors clear it. B: Place the title over the moving door edge before opening."),
        ("interface", interface, "B", "A screen tutorial: show the cursor splitting a clip and the visible result. A: Add a decorative wipe over the cursor during the split. B: Keep the cursor and the split continuously visible."),
    ]
    answers = {}
    for name, path, expected, brief in cases:
        material = ImageOps.contain(Image.open(path).convert("RGB"), (384, 360))
        image = Image.new("RGB", (384, 680), "#101520")
        image.paste(material, (0, 0))
        image.paste(example, (0, 360))
        prompt = ("The upper image is the new project; the lower two images are an example where a film strip "
                  "moves into place and then the title appears clear of the strip. Protect the actual action and the readability. "
                  f"Choose the edit that fits the new brief: {brief} Answer A or B first, with a short reason.")
        answer = _generate(model, processor, image, prompt, 30)
        match = re.match(r"^\s*(?:Answer\s+)?([AB])\b", answer, re.IGNORECASE)
        selected = match.group(1).upper() if match else None
        answers[name] = {"answer": answer, "source": str(path), "selected": selected, "expected": expected,
                         "passed": selected == expected}
    (output / "transferencia-local.json").write_text(json.dumps({"model": MODEL_ID, "device": device, "apiSpendUsd": 0,
        "cases": answers, "scope": "Choice of operations on supplied visual evidence; no autonomous execution or approval"},
        indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "positive", "interface"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    main(args.output, args.positive, args.interface)
