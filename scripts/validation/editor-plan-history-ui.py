"""Public DOM/timing observation after content-based history validation."""
import argparse
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage")
    parser.add_argument("--expected-frame", type=int)
    args = parser.parse_args()
    observer = runpy.run_path(str(ROOT / "scripts/validation/editor-materials-panel-observe.py"))
    globals_ = observer["main"].__globals__
    script = globals_["SCRIPT"].replace("path:new URL(x.name).pathname,status:",
        "path:new URL(x.name).pathname,query:new URL(x.name).search,status:")
    script = script.replace("inspectorFrame:inspector?.querySelector", "selectedLayerId:inspector?.querySelector('[aria-label=\"Camada\"]')?.value??null,\n    inspectorFrame:inspector?.querySelector")
    if args.expected_frame is not None:
        assert 0 <= args.expected_frame < 450
        script = script.replace("const inspectionReady =", "const baseInspectionReady =")
        script = script.replace("    if (document.querySelectorAll", (
            "    const inspectionReady = baseInspectionReady && inspector?.innerText.includes("
            f"'Propriedades calculadas no frame {args.expected_frame}.') && "
            f"Math.abs((video?.currentTime??-10)-{args.expected_frame}/30)<1/60 && !video?.seeking;\n"
            "    if (document.querySelectorAll"))
    globals_["SCRIPT"] = script
    globals_["OUT"] = ROOT / "docs/studios/research/editor-oss-20261002/plan-history-validation"
    sys.argv = ["public-observer", args.stage] + (["--inspection"] if args.expected_frame is not None else [])
    observer["main"]()


if __name__ == "__main__":
    main()
