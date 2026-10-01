"""Bounded local visual inspection for immutable material samples.

This process deliberately owns PyTorch/Transformers so the API environment does
not acquire those dependencies.  It emits one JSON document on stdout; model
warnings and progress stay on stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import unicodedata
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import torch
from PIL import Image, ImageDraw
from transformers import AutoModelForMultimodalLM, AutoProcessor, logging

logging.set_verbosity_error()

MODEL_ID = "HuggingFaceTB/SmolVLM-500M-Instruct"
MODEL_REVISION = "a7da5b986cb59b408707209984f360a5f4ad7e47"
MODEL_LICENSE = "Apache-2.0"


def _normalized(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def _decision(value: str) -> str:
    answer = _normalized(value).strip(" .,:;!\n\t")
    if answer.startswith(("sim", "yes", "supported")):
        return "yes"
    if answer.startswith(("nao", "no", "contradicted")):
        return "no"
    return "unknown"


def _contact_sheet(paths: list[Path]) -> Image.Image:
    frames = [Image.open(path).convert("RGB") for path in paths]
    width = 384
    resized = []
    for frame in frames:
        height = max(1, round(frame.height * width / frame.width))
        resized.append(frame.resize((width, height)))
    cell_height = max(image.height for image in resized) + 28
    columns = min(3, len(resized))
    rows = (len(resized) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * width, rows * cell_height), "#101820")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(resized):
        x = (index % columns) * width
        y = (index // columns) * cell_height
        sheet.paste(image, (x, y + 28))
        draw.text((x + 8, y + 7), f"FRAME {index}", fill="white")
    return sheet


def _generate(model, processor, image: Image.Image, prompt: str, max_tokens: int) -> str:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
    return processor.decode(
        output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True
    ).strip()


def inspect(payload: dict) -> dict:
    paths = [Path(value) for value in payload["samplePaths"]]
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("local_vlm_samples_unavailable")
    criteria = [str(value).strip() for value in payload["criteria"]]
    evidence_kind = str(payload.get("evidenceKind") or "static_frames")
    if evidence_kind not in {"static_frames", "temporal_sequence"}:
        raise ValueError("local_vlm_evidence_kind_invalid")
    if not criteria or any(not value for value in criteria):
        raise ValueError("local_vlm_criteria_invalid")
    processor = AutoProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        dtype=torch.float16,
    ).to("cuda" if torch.cuda.is_available() else "cpu")
    representative_indices = sorted({0, len(paths) // 2, len(paths) - 1})
    sheet = _contact_sheet(paths)
    description = _generate(
        model,
        processor,
        sheet,
        (
            "These are chronological sampled frames from one asset. Describe only visible facts "
            "that recur or visibly change: people, faces, hands, held objects, screens, setting, "
            "and observable actions. Do not infer intent or unseen events. Use at most 90 words."
        ),
        130,
    )
    findings = []
    for index, criterion in enumerate(criteria):
        raw_answers = []
        decisions = []
        sample_indices = list(range(len(paths))) if evidence_kind == "temporal_sequence" else representative_indices
        inspection_images = [sheet] if evidence_kind == "temporal_sequence" else [
            Image.open(paths[sample_index]).convert("RGB") for sample_index in representative_indices
        ]
        for image in inspection_images:
            raw = _generate(
                model,
                processor,
                image,
                (
                    f'Does this {"chronological sequence" if evidence_kind == "temporal_sequence" else "frame"} '
                    f'visibly prove this criterion: "{criterion}"? '
                    "For a sequence, require the stated change in chronological order. "
                    "Answer only YES, NO, or INCONCLUSIVE. Do not use metadata and do not infer intent."
                ),
                12,
            )
            raw_answers.append(raw)
            decisions.append(_decision(raw))
        yes = decisions.count("yes")
        no = decisions.count("no")
        required_yes = 1 if evidence_kind == "temporal_sequence" else 2
        result = "supported" if yes >= required_yes and no == 0 else "unknown"
        findings.append(
            {
                "index": index,
                "result": result,
                "evidence": (
                    f"Representative-frame description: {description} "
                    f"{evidence_kind} checks {sample_indices}: {raw_answers!r}."
                )[:1000],
                "sampleIndices": sample_indices,
            }
        )
    chroma_answer = _generate(
        model,
        processor,
        sheet,
        "Is a bright green or blue chroma-key screen a material part of the visible background? "
        "Answer only YES, NO, or INCONCLUSIVE.",
        12,
    )
    processing_requirements = ["chroma_key"] if _decision(chroma_answer) == "yes" else []
    return {
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "description": description or "Local sampled visual inspection completed.",
        "criteria": findings,
        "confidence": None,
        "confidenceKind": "uncalibrated_rule",
        "evidenceKind": evidence_kind,
        "processingRequirements": processing_requirements,
        "uncertainty": (
            "A compact local VLM performed bounded triage on sampled frames. Its output is not a "
            "calibrated probability or proof of unobserved intervals; every unsupported claim remains unknown."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload")
    args = parser.parse_args()
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    print(json.dumps(inspect(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
