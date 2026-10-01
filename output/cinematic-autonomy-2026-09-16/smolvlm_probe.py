import json
import os
import sys

import torch
from PIL import Image
from huggingface_hub import model_info
from transformers import AutoModelForMultimodalLM, AutoProcessor

model_id = os.environ.get("PROBE_MODEL", "HuggingFaceTB/SmolVLM-256M-Instruct")
revision = model_info(model_id).sha
processor = AutoProcessor.from_pretrained(model_id, revision=revision)
model = AutoModelForMultimodalLM.from_pretrained(
    model_id,
    revision=revision,
    torch_dtype=torch.float16,
).to("cuda")
images = [Image.open(path).convert("RGB") for path in sys.argv[1:]]
prompts = json.loads(os.environ.get("PROBE_PROMPTS", "[\"Describe only visible facts.\"]"))
answers = []
for prompt in prompts:
    content = [{"type": "image", "image": image} for image in images]
    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    with torch.inference_mode():
        outputs = model.generate(**inputs, max_new_tokens=100, do_sample=False)
    answers.append(processor.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
print(json.dumps({"revision": revision, "answers": answers}, ensure_ascii=False))
