"""Inspect the real Opus export and compare its locked intervals with the local cut."""
import argparse
import json
import runpy
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
helpers = runpy.run_path(str(ROOT / "scripts/validation/clicko-miolo-verificar.py"))
measurement = runpy.run_path(str(ROOT / "scripts/validation/clicko-quality-result.py"))["measure"]


def temporal_sheet(path, output):
    frames = helpers["decode"](path, 180, 320)
    times = np.arange(5, 11, 0.2)
    sheet = Image.new("RGB", (6 * 180, 5 * 344), "#151821")
    draw = ImageDraw.Draw(sheet)
    for index, second in enumerate(times):
        x, y = index % 6 * 180, index // 6 * 344
        frame = round(second * 30)
        if frame >= len(frames):
            break
        sheet.paste(Image.fromarray(frames[frame]), (x, y + 24))
        draw.text((x + 5, y + 5), f"{second:.2f} s", fill="white")
    sheet.save(output, quality=94)
    return frames


def main(output):
    previous = output.parent / "clicko-miolo-transferencia-2026-11-13/orbita/orbita.mp4"
    current = output / "orbita-opus-real.mp4"
    receipt = json.loads((output / "recibo.json").read_text(encoding="utf-8"))
    result = {"apiSpendUsd": receipt["apiSpendUsd"], "uncertainUsd": receipt["uncertainUsd"],
              "baseline": measurement(previous, output, "anterior"),
              "new": measurement(current, output, "opus"), "perceptualAudioListening": "pending"}
    before = temporal_sheet(previous, output / "anterior-miolo.jpg")
    after = temporal_sheet(current, output / "opus-miolo.jpg")
    result["lockedIntervals"] = {"sameDecodedFrameCount": len(before) == len(after)}
    if len(before) == len(after) == 540:
        result["lockedIntervals"]["opening"] = helpers["metric"](before[:150], after[:150])
        result["lockedIntervals"]["signature"] = helpers["metric"](before[330:], after[330:])
        a, b = helpers["audio"](previous), helpers["audio"](current)
        for key, start, end in (("openingAudio", 0, 4.94), ("signatureAudio", 11.06, 18)):
            left, right = round(start * 48000), round(end * 48000)
            error = a[left:right] - b[left:right]
            result["lockedIntervals"][key] = {"rmsDelta": float(np.sqrt(np.mean(error**2)))}
        result["lockedIntervals"]["visualTolerancePassed"] = all(
            result["lockedIntervals"][key]["worstFrameMeanDelta"] < 2 for key in ("opening", "signature"))
    (output / "comparacao.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"lockedIntervals": result["lockedIntervals"], "flash": result["new"]["wideAreaBrightness"],
                      "apiSpendUsd": receipt["apiSpendUsd"]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.output.resolve())
