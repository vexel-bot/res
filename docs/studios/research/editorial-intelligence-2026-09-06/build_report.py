"""Build the standalone research deliverable; does not import the res application."""
from pathlib import Path
import hashlib
import html
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
source = (HERE / "report-source.md").read_text(encoding="utf-8")

def inline(text):
    held = []
    def stash(value):
        held.append(value)
        return f"@@TOKEN{len(held)-1}@@"
    text = re.sub(r"`([^`]+)`", lambda m: stash("<code>" + html.escape(m[1]) + "</code>"), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: stash('<a href="' + html.escape(m[2], quote=True) + '">' + html.escape(m[1]) + '</a>'), text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    for i, value in enumerate(held):
        text = text.replace(f"@@TOKEN{i}@@", value)
    return text

lines = source.splitlines()
parts, toc = [], []
i = 0
while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1
        continue
    heading = re.match(r"^(#{1,3}) (.+)$", line)
    if heading:
        level, title = len(heading[1]), heading[2]
        anchor = f"section-{len(toc)+1}" if level == 2 else f"heading-{i}"
        if level == 2:
            toc.append((anchor, title))
        parts.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
        i += 1
    elif line.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                rows.append(cells)
            i += 1
        header = "".join(f"<th scope='col'>{inline(c)}</th>" for c in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows[1:])
        parts.append(f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>')
    elif re.match(r"^\d+\. ", line):
        items = []
        while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
            items.append("<li>" + inline(re.sub(r"^\d+\. ", "", lines[i])) + "</li>")
            i += 1
        parts.append("<ol>" + "".join(items) + "</ol>")
    else:
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||\d+\. )", lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        parts.append("<p>" + inline(" ".join(paragraph)) + "</p>")

css = """
:root{--ink:#192b36;--muted:#52656f;--line:#d5e1e5;--accent:#087e83;--paper:#fff;--wash:#f0f5f5}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}body{margin:0;background:var(--wash);color:var(--ink);font:16px/1.7 'Segoe UI',Arial,sans-serif}a{color:#076b77;text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#003d48}header{background:#142d38;color:#f5fbfb;padding:36px 5vw 32px}header .eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#a7d7d6}header h1{font-size:clamp(27px,3.5vw,43px);line-height:1.18;margin:12px 0;max-width:920px;letter-spacing:-.035em}header p{color:#c5d9df;margin:0;max-width:840px}.stats{display:flex;gap:30px;margin-top:24px;flex-wrap:wrap}.stats span{font-size:13px;color:#c4d6dd}.stats b{font-size:25px;color:white;margin-right:7px}.shell{display:grid;grid-template-columns:245px minmax(0,1fr);max-width:1450px;margin:auto}nav{padding:34px 22px;align-self:start;position:sticky;top:0;max-height:100vh;overflow:auto}nav b{font-size:12px;letter-spacing:.1em;color:var(--muted)}nav a{display:block;font-size:13px;line-height:1.45;padding:9px 0;text-decoration:none;border-bottom:1px solid var(--line)}main{background:var(--paper);padding:30px 48px 70px;min-width:0}main h1{font-size:27px;line-height:1.25;margin-top:8px}h2{font-size:25px;line-height:1.3;margin:56px 0 20px;padding-top:18px;border-top:3px solid var(--accent);letter-spacing:-.025em}h3{font-size:19px;line-height:1.4;margin:32px 0 14px;color:#185663}p{margin:15px 0}code{font:12px/1.5 Consolas,monospace;overflow-wrap:anywhere;background:#edf3f5;padding:2px 4px;border-radius:3px}strong{font-weight:650}li{padding:6px 0}.table-wrap{overflow-x:auto;margin:22px 0;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.5;min-width:590px}th{background:#e6f1f1;text-align:left;color:#134b56;padding:13px 12px}td{padding:13px 12px;border-top:1px solid var(--line);vertical-align:top}tr:nth-child(even) td{background:#f7fafb}td:first-child{font-weight:600}footer{padding:25px 5vw;font-size:12px;color:var(--muted)}.tag{display:inline-block;padding:4px 10px;background:#dcefee;color:#155e62;border-radius:30px;font-size:12px;font-weight:600;margin-bottom:8px}.toolbar{float:right}button{font:inherit;font-size:13px;background:#f3fcfc;color:#183842;border:0;padding:8px 13px;border-radius:5px;cursor:pointer}
@media(max-width:1050px){.shell{grid-template-columns:190px minmax(0,1fr)}main{padding:25px 27px}nav{padding:30px 15px}body{font-size:15px}}
@media(max-width:720px){.shell{display:block}nav{position:static;max-height:none;padding:20px;display:grid;grid-template-columns:1fr 1fr;gap:0 20px}nav b{grid-column:1/-1}main{padding:20px}.stats{gap:16px}h2{font-size:22px}.toolbar{float:none;margin-bottom:14px}table{min-width:580px}}
@media print{body{background:white;font-size:10pt}header{background:white;color:#142d38;padding:0 0 15px;border-bottom:2px solid #087e83}header p,header .eyebrow,.stats span,.stats b{color:#314a54}header h1{font-size:25pt}.toolbar,nav{display:none}.shell{display:block}main{padding:0}h2{break-after:avoid;font-size:17pt;margin-top:25px}h3{break-after:avoid;font-size:13pt}p{orphans:3;widows:3}.table-wrap{overflow:visible;border:0}table{min-width:0;font-size:8pt}tr{break-inside:avoid}thead{display:table-header-group}td,th{padding:7px}a{color:inherit}footer{padding:15px 0}@page{size:A4;margin:16mm}}
"""
navigation = "".join(f'<a href="#{anchor}">{html.escape(title)}</a>' for anchor,title in toc)
document = '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>res — Pesquisa de inteligência editorial</title><style>' + css + '</style></head><body><header><div class="toolbar"><button onclick="window.print()">Imprimir / salvar PDF</button></div><div class="eyebrow">res · edição de vídeo · pesquisa e revisão</div><h1>De recursos de edição a decisões com intenção</h1><p>Diagnóstico do sistema, análise das referências e repertório operacional para preparar o próximo planejamento.</p><div class="stats"><span><b>6</b>casos reobservados</span><span><b>25</b>técnicas candidatas</span><span><b>9</b>achados prioritários</span></div></header><div class="shell"><nav aria-label="Seções"><b>NESTE RELATÓRIO</b>' + navigation + '</nav><main><span class="tag">Pesquisa concluída · implementação não iniciada nesta etapa</span>' + "\n".join(parts) + '</main></div><footer>6 de setembro de 2026 · Evidência visual amostral, fontes primárias e revisão estática do código. Áudio das referências não verificado. Documento local sem dependências externas.</footer></body></html>'
(HERE / "RELATORIO.html").write_text(document, encoding="utf-8")

sources = [
 ("S01","Ordinary Folk — Process","https://www.ordinaryfolk.co/process","processo primário","não datado","Mensagem, design, animação e áudio articulados; base para artefatos intermediários.","Página do processo lida; não é prova da qualidade do res."),
 ("S02","Ben Marriott — Motion Foundation","https://www.benmarriott.com/motion-foundation","programa do próprio autor","não datado","Currículo com curvas, máscaras, match cuts, parallax e animatic.","Programa público lido; curso não assistido."),
 ("S03","Walter Murch — In the Blink of an Eye","https://www.silmanjamespress.com/shop/filmmaking-directing/in-the-blink-of-an-eye2nd-edition/","editora","2ª edição","Referência bibliográfica para decisão de corte e continuidade.","Descrição editorial consultada; livro não lido integralmente."),
 ("S04","Karen Pearlman — Cutting Rhythms","https://www.routledge.com/Cutting-Rhythms-Creative-Film-Editing/Pearlman/p/book/9781041024088","editora / resultado indexado","3ª edição","Referência bibliográfica sobre ritmo e criatividade na montagem.","Texto integral da página bloqueado por 403; apenas referência indexada."),
 ("S05","Bruce Block — The Visual Story","https://www.routledge.com/The-Visual-Story-Creating-the-Visual-Structure-of-Film-TV-and-Digital-Media/Block/p/book/9781138014152","editora","2021, 3ª edição","Componentes visuais relacionados à estrutura da história.","Descrição e sumário consultados; livro não lido integralmente."),
 ("S06","Randy Thom — Designing a Movie for Sound","https://www.filmsound.org/articles/designing_for_sound.htm","artigo assinado","1999","Som deve participar das decisões de construção do filme, incluindo pausas e ponto de vista.","Princípio de criação; não benchmark automatizado."),
 ("S07","Scrolly2Reel","https://arxiv.org/abs/2403.18111","artigo dos autores","2024","Unidades narrativas para relacionar gráficos, narração e ritmo.","Escopo de retargeting de gráficos; não generalizar para edição universal."),
 ("S08","Blackmagic — DaVinci Resolve Training","https://www.blackmagicdesign.com/products/davinciresolve/training","documentação e currículo oficial","página atual consultada","Formação em montagem, cor, Fairlight, Fusion, composição e tracking.","Página/currículo lidos; exercícios não executados."),
 ("S09","Adobe — J cuts and L cuts","https://helpx.adobe.com/uk/premiere/desktop/edit-projects/trim-clips/perform-j-cuts-and-l-cuts.html","documentação oficial","2025-10-19","Áudio e imagem podem trocar de plano em momentos diferentes.","Mecanismo documentado; aplicação editorial depende da cena."),
 ("S10","Adobe — Animating text","https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html","documentação oficial","2026-04-30","Animadores e seletores permitem controlar grupos e unidades de texto.","Capacidade do After Effects, não do res."),
 ("S11","Cavalry — Duplicator","https://cavalry.studio/docs/nodes/shapes/duplicator/","documentação oficial","não datado","Distribuição e propriedades por instância.","Referência técnica de outro produto."),
 ("S12","Cavalry — Stagger","https://cavalry.studio/docs/nodes/behaviours/stagger/","documentação oficial","não datado","Valores sequenciais e deslocamento temporal por instância.","Não determina a escolha artística do atraso."),
 ("S13","Blender — VFX","https://www.blender.org/features/vfx/","documentação oficial","não datado","Compositor, tracking de câmera/objeto e render layers.","Página de capacidades; integração no res não certificada."),
 ("S14","HyperFrames — Determinism","https://hyperframes.heygen.com/concepts/determinism","documentação oficial","não datado","Tempo por frame, carga prévia de assets e ambiente fixado para repetibilidade.","A promessa da ferramenta precisa ser validada na integração."),
 ("S15","Motion Canvas — Tweening","https://motion-canvas.io/docs/tweening/","documentação oficial","não datado","Interpolação e funções de tempo para animações.","Não substitui direção editorial."),
 ("S16","Universal Category System","https://universalcategorysystem.com/","iniciativa original","recursos 8.2.1 citados na página","Categorias e convenções para biblioteca de efeitos sonoros.","Taxonomia não resolve seleção de som por intenção."),
 ("S17","Freesound — FAQ","https://freesound.org/help/faq/","documentação da biblioteca","não datado","Busca de sons e condições variáveis por arquivo.","Nenhum download, compra ou integração ativada."),
 ("S18","YouTube — Audio Library","https://support.google.com/youtube/answer/3376882?hl=en","documentação oficial","não datado","Biblioteca de música/efeitos, busca e downloads no Studio.","Não inferir autorização geral de redistribuição em SaaS."),
 ("S19","Meta — One year of Edits","https://about.fb.com/news/2026/04/one-year-of-edits-built-for-and-with-creators/amp/","anúncio oficial","2026-04","Inspiração, organização e exploração de projetos/templates.","Anúncio não fornece automaticamente conector de coleta; recursos futuros não tratados como entregues."),
]
ledger = [{"id":s[0],"title":s[1],"url":s[2],"source_type":s[3],"published":s[4],"accessed":"2026-09-06","supports":s[5],"limitation":s[6],"confidence":"limited" if s[0]=="S04" else "primary_source_for_stated_scope"} for s in sources]

observations = [
 {"id":"Dct4pAohiup","profile":"creators + moonsol.design","url":"https://www.instagram.com/creators/reel/Dct4pAohiup/","duration_s":35.176779,"public_metrics":{"likes_display":"45,3 mil"},"published_label":"6 dias","frames":[{"at_s":20.44,"observation":"Contorno manual da roupa sobre fotografia."},{"at_s":26.269836,"observation":"Mídia de paisagem posicionada dentro da região da blusa; timeline e escala visíveis."}]},
 {"id":"DcdfCb9SW8F","profile":"moonsol.design","url":"https://www.instagram.com/moonsol.design/reel/DcdfCb9SW8F/","duration_s":49.266667,"public_metrics":{"likes_display":"1,1 mil","comments":5,"reposts":21},"published_label":"25 de agosto","frames":[{"at_s":4.52025,"observation":"Contorno verde parcial sobre fotografia no tutorial."},{"at_s":19.138541,"observation":"Instrução para adicionar um ponto como texto; guia de linha parcial."}]},
 {"id":"DcxuG6fIxZ-","profile":"moonsol.design","url":"https://www.instagram.com/moonsol.design/reel/DcxuG6fIxZ-/","duration_s":39.147391,"public_metrics":{"likes_display":"4,2 mil","comments":19,"reposts":123},"published_label":"4 dias","frames":[{"at_s":11.327094,"observation":"Estrelas de tamanhos diferentes empilhadas; instrução para duplicar."},{"at_s":23.737736,"observation":"Conjunto de estrelas sobre fotografia; instrução para rotacionar a imagem no fim da sobreposição."}]},
 {"id":"Dcl3b2LR6NC","profile":"creators","url":"https://www.instagram.com/creators/reel/Dcl3b2LR6NC/","duration_s":10.733333,"public_metrics":{"likes_display":"162,2 mil","comments_display":"4,3 mil","reposts_display":"12,2 mil"},"published_label":"28 de agosto","frames":[{"at_s":6.065214,"observation":"Personagem olha para telefone sob texto de chamada recebida; câmera estável."}]},
 {"id":"Dc3qMrJxJcp","profile":"creators + alexcisse","url":"https://www.instagram.com/creators/reel/Dc3qMrJxJcp/","duration_s":41.701586,"public_metrics":{"likes_display":"37,4 mil","comments":661,"reposts":517},"published_label":"2 dias","frames":[{"at_s":0.867474,"observation":"Pessoa no sofá vista de cima, pequena unidade de texto."},{"at_s":19.9185,"observation":"Pessoa reclinada, janela e paisagem; pequena unidade de texto."}]},
 {"id":"DRjjvOogSZg","profile":"moonsol.design","url":"https://www.instagram.com/moonsol.design/reel/DRjjvOogSZg/","duration_s":32.020317,"public_metrics":{"likes_display":"580,3 mil","comments":221,"reposts_display":"12 mil"},"published_label":"27 de novembro de 2025","frames":[{"at_s":4.521839,"observation":"Fotografia e prato em primeiro plano sobre cartão de localização."},{"at_s":9.95925,"observation":"Cartão isolado na preparação do tutorial."}]},
]
for observation in observations:
    observation.update(observed_on="2026-09-06", surface="Codex in-app browser", audio_verification="unknown; player muted", temporal_coverage="sampled frames, not frame-complete decoupage", views_current=None, causal_performance_claim=False)

files = {
 "renderer":"backend/app/providers/studios/contextual_render.py",
 "plan_contract":"backend/app/domain/studios/contextual_editing.py",
 "contextual_service":"backend/app/services/studios/contextual_editing.py",
 "planner":"backend/app/services/studios/gemini_editing.py",
 "repertoire":"backend/app/services/studios/editing_repertoire.py",
 "materials":"backend/app/services/studios/material_director.py",
 "resources":"backend/app/services/studios/editing_resources.py",
 "motion":"backend/app/domain/studios/motion.py",
 "render_service":"backend/app/services/studios/video_render.py",
 "hyperframes":"backend/app/providers/studios/hyperframes_projection.py",
 "ai_adapters":"backend/app/providers/studios/editing_ai.py",
}
code_evidence = []
for key, relative in files.items():
    path = ROOT / relative
    code_evidence.append({"id":key,"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"scope":"static inspection; no application tests run in this research step"})

gaps = [
 {"id":"G1","question":"Repertório influencia uma composição nova?","evidence":["planner","repertoire","plan_contract","motion"],"status":"partial integration","next_validation":"Intenção gera cena/grafo com vários elementos e justificativas sem montar a peça manualmente fora do res."},
 {"id":"G2","question":"Percepção cobre ações relevantes?","evidence":["planner"],"status":"limited fixed sampling","next_validation":"Trecho com evento fora de início/meio/fim exige inspeção adicional ou abstenção."},
 {"id":"G3","question":"Fontes e elementos têm equivalência de render?","evidence":["hyperframes","resources"],"status":"known compatibility gap","next_validation":"Fonte do projeto e composição de múltiplos elementos no preview e MP4."},
 {"id":"G4","question":"Biblioteca grande continua recuperável?","evidence":["repertoire","planner"],"status":"context truncation risk identified in code","next_validation":"Técnica relevante criada depois da centésima é recuperada para o contexto."},
 {"id":"G5","question":"Som das referências foi analisado?","evidence":["Instagram sampled observations","S06","S16"],"status":"not verified by listening","next_validation":"Audição integral de arquivos disponíveis e anotação de eventos, silêncio e mixagem."},
 {"id":"G6","question":"Métricas comprovam tendência ou causalidade?","evidence":["historical Instagram CSV","current public counts"],"status":"descriptive evidence only","next_validation":"Série temporal com idade/contexto; retenção e experimentos quando houver acesso."},
 {"id":"G7","question":"Transformação em movimento está qualificada?","evidence":["ai_adapters","renderer"],"status":"pending real media qualification","next_validation":"Clip real, elementos preservados, avaliação de continuidade e incorporação na montagem."},
 {"id":"G8","question":"Qual vídeo/tema usar no teste editorial?","evidence":["report section 9"],"status":"planning decision","next_validation":"Selecionar vídeo próprio/autorizado, registrar intenção e problemas do original."},
]

queries = {"method":"Bounded thematic searches and primary-source follow-ups; topic groups, not a verbatim tool transcript.","waves":["Professional studio process and editorial representation","Narrative rhythm, text animation, procedural motion","Sound design, sound-library taxonomy and acquisition","Renderer determinism, timeline and motion integration","Instagram case reinspection in the local GPT browser"],"stop_rationale":"Each knowledge group has primary references and operational proposals; remaining uncertainties require media listening, real renders or a planning decision rather than further generic web searches.","unavailable_sources":["Pearlman publisher full page returned 403; used indexed bibliographic reference only","Blender manual page fetch failed; used official Blender VFX page for capability claims","The Visual Story sample chapter fetch failed; used publisher description/table of contents only"]}
for name, value in [("claim-source-ledger.json",{"external_sources":ledger,"code_evidence":code_evidence,"audit_date":"2026-09-06","claims_of_causality":False}), ("instagram-observations.json",observations),("gap-matrix.json",gaps),("research-method.json",queries)]:
    (HERE / name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

print(json.dumps({"report":str(HERE/"RELATORIO.html"),"words":len(source.split()),"sections":len(toc),"tables":document.count("<table>"),"sources":len(ledger),"fresh_instagram_cases":len(observations),"code_files_hashed":len(code_evidence)},ensure_ascii=False))
