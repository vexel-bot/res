"""Exact-source adaptation of the MIT-licensed upstream demo.

Upstream: meituan-longcat/LongCat-Video, revision below. No PyTorch import here.
The original checkout is never modified; the patched entry point is job-local.
"""

from __future__ import annotations

import ast
import hashlib

SOURCE_REVISION = "6b3f4b8582a8bc3f20f795735f5383716c4ba794"
SOURCE_SHA256 = "3d1125a8f9d21d2412cae0d9cc434bd8b4a497fd757d644b1ecca1fea1ae8207"


def patched_demo(source: bytes) -> str:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("longcat_demo_source_mismatch")
    text = source.decode("utf-8")
    tree = ast.parse(text)
    # Remove the separator import, helper and setup. Preserve every other
    # upstream pipeline call, including continuation and context parallelism.
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "extract_vocal_from_speech"
    )
    lines = text.splitlines(keepends=True)
    del lines[helper.lineno - 1 : helper.end_lineno]
    text = "".join(lines).replace(
        "from audio_separator.separator import Separator\n", ""
    )
    start = text.index("    vocal_separator_path =")
    end = text.index("    # initialize pipeline", start)
    text = text[:start] + text[end:]
    start = text.index("        # extract vocal")
    end = text.index("        # audio padding to target length", start)
    text = text[:start] + "        temp_vocal_path = raw_speech_path\n\n" + text[end:]
    text = text.replace(
        "    global_seed = 42", "    global_seed = int(input_data['seed'])"
    )
    # Never delete the immutable final speech after extracting its embedding.
    text = text.replace(
        "        if os.path.exists(temp_vocal_path):\n            os.remove(temp_vocal_path)\n",
        "",
    )
    ast.parse(text)
    if "Separator(" in text or "extract_vocal_from_speech(" in text:
        raise ValueError("longcat_clean_audio_patch_incomplete")
    return text
