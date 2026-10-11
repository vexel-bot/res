"""Read public DOM/timings through the existing agent-browser lab session."""
import argparse
import base64
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/materials-and-panel-loading"

SCRIPT = r"""(async () => {
  const deadline = performance.now() + 20000;
  const inspectionRequired = __INSPECTION__;
  let ready = false;
  while (performance.now() < deadline) {
    const video = document.querySelector('.vs-stage video');
    const inspector = document.querySelector('.editor-inspection');
    const inspectionReady = !inspectionRequired || (inspector?.offsetParent && inspector.querySelector('[aria-label="Frame da composição"]'));
    if (document.querySelectorAll('.vs-media-card[data-asset-id]').length && video?.readyState >= 2 && !video.seeking && inspectionReady) { ready = true; break; }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const video = document.querySelector('.vs-stage video');
  const direction = document.querySelector('[aria-label="Edição contextual"]');
  const inspector = document.querySelector('.editor-inspection');
  const directionDraft = [...(direction?.querySelectorAll('label') ?? [])]
    .find(label => label.textContent.trim().startsWith('Roteiro e informações de origem'))?.querySelector('textarea');
  const localProbeButton = [...(direction?.querySelectorAll('button') ?? [])]
    .find(button => /Verifica.*gerador local/.test(button.textContent));
  const localCheckbox = [...(direction?.querySelectorAll('label') ?? [])]
    .find(label => label.textContent.includes('Incluir um trecho experimental'))?.querySelector('input');
  return {observedAt:new Date().toISOString(),url:location.href,ready,scope:'Public DOM and performance timings; no document edits',
    cards:[...document.querySelectorAll('.vs-media-card[data-asset-id]')].map(card=>({assetId:card.dataset.assetId,
      mediaType:card.dataset.mediaType,title:card.querySelector('b')?.innerText,
      rights:card.querySelector('small')?.innerText,thumbnailText:card.querySelector('.vs-media-thumb')?.innerText,
      videoElements:card.querySelectorAll('video').length,imageElements:card.querySelectorAll('img').length})),
    directionMounted:!!direction,directionVisible:!!direction?.offsetParent,
    directionDraft:directionDraft?.value ?? null,
    localProbe:localProbeButton?{text:localProbeButton.innerText,disabled:localProbeButton.disabled,
      selected:localCheckbox?.checked,optionDisabled:localCheckbox?.disabled,
      alerts:[...direction.querySelectorAll('[role="alert"]')].map(x=>x.innerText),
      capability:[...direction.querySelectorAll('p')].find(x=>x.textContent.trim().startsWith('Difusor local:'))?.innerText??null}:null,
    reviewGateMounted:!!document.querySelector('[aria-label="Controle editorial UGC/avatar"]'),
    inspectorFrame:inspector?.querySelector('[aria-label="Frame da composição"]')?.value ?? null,
    inspectorText:inspector?.offsetParent?inspector.innerText:null,
    video:video?{readyState:video.readyState,seeking:video.seeking,currentTime:video.currentTime,width:video.videoWidth,
      height:video.videoHeight,duration:video.duration,paused:video.paused}:null,
    overlays:document.querySelectorAll('vite-error-overlay').length,
    resources:performance.getEntriesByType('resource').filter(x=>new URL(x.name).pathname.startsWith('/api/'))
      .map(x=>({path:new URL(x.name).pathname,status:x.responseStatus,startMs:x.startTime,fetchStartMs:x.fetchStart,
        requestStartMs:x.requestStart,responseStartMs:x.responseStart,endMs:x.responseEnd,durationMs:x.duration}))};
})()
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage")
    parser.add_argument("--inspection", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]+", args.stage):
        raise ValueError("stage_slug_required")
    target = OUT / f"{args.stage}.json"
    if target.exists():
        raise ValueError("preserve_existing_observation")
    executable = shutil.which("agent-browser")
    if not executable:
        raise ValueError("existing_agent_browser_required")
    script = SCRIPT.replace("__INSPECTION__", "true" if args.inspection else "false")
    encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
    result = subprocess.run([executable, "--session", "res-output-download-20261005", "--json", "eval", "-b", encoded],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    if result.returncode:
        raise ValueError("browser_observation_failed")
    # Decode native CLI bytes explicitly; do not pass through PowerShell text conversion.
    raw = result.stdout.decode("utf-8")
    value = json.loads(raw)
    if not value["success"]:
        raise ValueError("browser_eval_failed")
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    v = value["data"]["result"]
    if not isinstance(v, dict) or "cards" not in v:
        raise ValueError("public_dom_observation_required")
    print(json.dumps({"stage":args.stage,"cards":len(v["cards"]),"mediaTypes":[c["mediaType"] for c in v["cards"]],
                      "directionMounted":v["directionMounted"],"videoReady":v["video"]["readyState"] if v["video"] else None}))
    if not v["ready"]:
        raise ValueError("expected_ui_not_ready_observation_retained")


if __name__ == "__main__":
    main()
