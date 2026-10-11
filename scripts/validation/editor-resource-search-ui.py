"""Read public catalog query/state/IDs and timings in the existing lab browser."""
import argparse
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage")
    parser.add_argument("--query", required=True)
    parser.add_argument("--status", choices=["ready", "failed", "loading"], default="ready")
    args = parser.parse_args()
    observer = runpy.run_path(str(ROOT / "scripts/validation/editor-materials-panel-observe.py"))
    globals_ = observer["main"].__globals__
    script = globals_["SCRIPT"].replace("path:new URL(x.name).pathname,status:",
        "path:new URL(x.name).pathname,query:new URL(x.name).search,status:")
    expected_query = json.dumps(args.query, ensure_ascii=True)
    script = script.replace("const inspectionReady =", "const baseInspectionReady =")
    script = script.replace("    if (document.querySelectorAll", (
        "    const catalog = document.querySelector('.vs-editing-resources [aria-label=\"Resultados do acervo\"]');\n"
        "    const panel = document.querySelector('.vs-editing-resources');\n"
        f"    const inspectionReady = baseInspectionReady && panel?.open && catalog?.dataset.catalogQuery === {expected_query}"
        f" && catalog?.dataset.catalogStatus === '{args.status}';\n"
        "    if (document.querySelectorAll"))
    script = script.replace("    cards:[...document.querySelectorAll", (
        "    catalog:(()=>{const panel=document.querySelector('.vs-editing-resources');"
        "const list=panel?.querySelector('[aria-label=\"Resultados do acervo\"]');return {open:!!panel?.open,"
        "query:list?.dataset.catalogQuery,status:list?.dataset.catalogStatus,busy:list?.getAttribute('aria-busy'),"
        "rows:[...(list?.querySelectorAll('[data-resource-id]')??[])].map(x=>({id:x.dataset.resourceId,text:x.innerText})),"
        "alerts:[...(panel?.querySelectorAll('[role=\"alert\"]')??[])].map(x=>x.innerText),"
        "statuses:[...(panel?.querySelectorAll('[role=\"status\"]')??[])].map(x=>x.innerText)}})(),\n"
        "    cards:[...document.querySelectorAll"))
    globals_["SCRIPT"] = script
    globals_["OUT"] = ROOT / "docs/studios/research/editor-oss-20261002/resource-search"
    sys.argv = ["public-observer", args.stage]
    observer["main"]()


if __name__ == "__main__":
    main()
