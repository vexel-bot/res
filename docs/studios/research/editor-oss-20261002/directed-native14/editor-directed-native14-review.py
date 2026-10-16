"""Export canonical blind labels as verified NTFS links, without rating or copying media."""
import hashlib
import json
import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/visual-directed-native14-20261004"
BLIND = OUT / "blind-review"
assert not BLIND.exists(), "Preserve an existing blind export"
state = json.loads((OUT / "execution.json").read_text(encoding="utf-8"))
assert len(state["variants"]) == 9 and all(v.get("artifact") for v in state["variants"].values())
study = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
study["api"].__globals__["BASE"] = "http://127.0.0.1:8000/api/v1"
_, workspace_id = study["identity"]()
assert workspace_id == state["workspaceId"]
sessions = {}
for key in ["organization", "comparison", "interface"]:
    identifier = state["comparisons"][key]["id"]
    current = study["api"](f"/studios/v1/workspaces/{workspace_id}/visual-study-comparisons/{identifier}")
    assert current["status"] == "not_assessed" and not current["blockers"] and current["review"] is None
    assert current["labels"] == state["comparisons"][key]["labels"]
    sessions[key] = current
BLIND.mkdir()
lines = ["# Revisão cega dos três estudos — 15 segundos", "",
    "Assista às opções completas, com som e em tamanho de celular. As letras vêm das sessões cegas da API; a condição permanece oculta nesta página.", "",
    "Para cada estudo, descreva o que mudou e indique A/B/C. Dê notas de 1–5 para clareza, ritmo, continuidade e adequação à mensagem; registre acabamento separadamente. Cite tempo/cena de qualquer falha e a mudança necessária.", "",
    "As notas estão pendentes. Estes links reproduzem os MP4s canônicos, sem nova edição ou encode; abrir os arquivos não registra uma avaliação no Studio.", ""]
export = {"scope": "canonical_API_blind_labels_original_MP4_bytes", "workspaceId": workspace_id,
    "humanReview": "not_assessed", "autonomy": "not_demonstrated", "sessions": {}, "aliases": []}
names = {"organization": "Dê direção às suas ideias.", "comparison": "Mesmas peças. Outra relação.",
         "interface": "Uma mudança. Um resultado real."}
html = ['<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
    '<title>Revisão cega — estudos reais do res</title>',
    '<style>body{margin:0;background:#101416;color:#efece1;font:16px system-ui}main{max-width:1050px;margin:auto;padding:24px}section{margin:40px 0}.options{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0;width:280px;max-width:100%}video{width:280px;max-width:100%;display:block}figcaption{margin:8px 0}small{overflow-wrap:anywhere}p{max-width:75ch;line-height:1.5}a{color:#c9ed84}</style><main>',
    '<h1>Compare os três estudos</h1><p>Assista às três opções completas, em velocidade normal e com som. Cada vídeo tem 15 s e aparece com 280 px de largura. As letras vêm das sessões cegas da API.</p>',
    '<p>Depois descreva o que mudou e informe a preferência A/B/C e as notas de clareza, ritmo, continuidade, adequação à mensagem e acabamento (1–5). Cite os intervalos de falhas. Avaliação humana pendente.</p>',
    '<p>Esta página reproduz os MP4s canônicos. Abrir os vídeos não registra notas no Studio.</p>']
for key, session in sessions.items():
    folder = BLIND / key
    folder.mkdir()
    lines += ["## " + names[key], "", "Sessão: `" + session["id"] + "` · avaliação pendente.", "",
        "| Opção A | Opção B | Opção C |", "|---|---|---|"]
    cells = []
    export["sessions"][key] = session
    assert {x["label"] for x in session["labels"]} == {"A", "B", "C"}
    html += [f'<section id="{key}"><h2>{names[key]}</h2><p>Sessão: {session["id"]}</p><div class="options">']
    for label in session["labels"]:
        matches = [v for v in state["variants"].values() if v["artifact"]["assetId"] == label["assetId"]]
        assert len(matches) == 1
        value = matches[0]
        assert value["documentId"] == label["documentId"] and value["revision"] == label["documentRevision"]
        source = OUT / (value["key"] + ".mp4")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == label["checksum"] == value["artifact"]["checksumSha256"]
        alias = folder / (label["label"] + ".mp4")
        os.link(source, alias)
        assert os.path.samefile(source, alias) and alias.stat().st_nlink >= 2
        assert hashlib.sha256(alias.read_bytes()).hexdigest() == digest
        cells.append(f"[Assistir {label['label']}](<{alias.as_posix()}>)")
        html.append(f'<figure><figcaption>Opção {label["label"]}</figcaption><video controls playsinline preload="metadata" src="{key}/{label["label"]}.mp4" aria-label="{key} opção {label["label"]}"></video><small>SHA-256: {digest}</small></figure>')
        export["aliases"].append({"sessionId": session["id"], "label": label["label"],
            "assetId": label["assetId"], "checksum": digest, "path": alias.relative_to(OUT).as_posix(),
            "storage": "same_NTFS_file_hard_link_no_extra_media_data", "sizeBytes": alias.stat().st_size})
    lines += ["| " + " | ".join(cells) + " |", "",
        "Resposta: preferência ___ · clareza ___ · ritmo ___ · continuidade ___ · adequação ___ · acabamento ___", "",
        "O que mudou? ___  Falhas e intervalos: ___  Assistiu completo/com som/em tamanho móvel? ___", ""]
    html.append('</div></section>')
html.append('<p><a href="REVIEW.md">Instruções e campos de resposta</a></p></main><script>document.querySelectorAll("video").forEach(v=>v.addEventListener("play",()=>document.querySelectorAll("video").forEach(o=>{if(o!==v)o.pause()})))</script></html>')
(BLIND / "REVIEW.html").write_text("\n".join(html), encoding="utf-8")
(BLIND / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
(OUT / "blind-export.json").write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"sessions": len(sessions), "verifiedAliases": 9,
    "additionalMediaDataBytes": 0, "humanReview": "not_assessed"}))
