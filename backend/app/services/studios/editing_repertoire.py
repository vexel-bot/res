"""Incremental, tenant-scoped editing evidence using the existing knowledge store."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select

from ...domain.studios.contextual_editing import EditingObservationV1, EditingTechniqueV1, digest
from ...models import KnowledgeChunk, KnowledgeDocument
from ..knowledge import chunk_content, hybrid_search

RESEARCH_EXECUTABLE_IDS = frozenset({
    "action_progression", "motif_continuity", "gesture_occlusion_reveal", "moving_variant_mask"
})


def research_operation_cards() -> list[EditingTechniqueV1]:
    """Package observed editing grammar as data; observation is never a license or a quality grade."""
    from pathlib import Path

    path = Path(__file__).with_name("instagram_editing_operations.v1.json")
    research = json.loads(path.read_text(encoding="utf-8"))
    cards = []
    for item in research["operations"]:
        identifier = item["id"]
        cards.append(EditingTechniqueV1(
            id=identifier,
            version=1,
            qualification="implemented" if identifier in RESEARCH_EXECUTABLE_IDS else "knowledge_only",
            source_digest=digest(item),
            group="montage" if identifier in {"action_progression", "motif_continuity"} else "composition",
            title=identifier.replace("_", " ").capitalize(),
            purpose=item["perceptual_goal"],
            suitable_when=item["narrative_functions"],
            avoid_when=item["reject_when"],
            prerequisites=item["inputs"],
            parameters={str(index): step for index, step in enumerate(item["plan_steps"], 1)},
            required_capabilities=[],
            required_material_kinds=[],
            components=[identifier] if identifier in RESEARCH_EXECUTABLE_IDS else [],
            verification=item["render_checks"],
            evidence_type="observation",
            sources=[f"https://www.instagram.com/reel/{reel}/" for reel in item["evidence_reels"]],
            research_evidence=[f"Visual sampling: {reel}" for reel in item["evidence_reels"]],
            creator_claims=[],
            inferences=[item["perceptual_goal"], *item["plan_steps"]],
            method_limitations=research["method_limits"],
        ))
    return cards


def seed_techniques() -> list[EditingTechniqueV1]:
    data = [
        (
            "continuity",
            "montage",
            "Continuidade da mensagem",
            "Preservar relações de causa, negações e ressalvas.",
            ["Fala explicativa", "Entrevista", "Demonstração"],
            ["Remover uma ressalva que muda a promessa"],
            ["Material original", "Transcrição quando disponível"],
            {"order": "Ordem dos trechos completos"},
            ["cut"],
            "principle",
            [],
        ),
        (
            "demonstration",
            "montage",
            "Mostrar a evidência durante a explicação",
            "Relacionar a afirmação ao detalhe visível.",
            ["Tutorial", "Produto com material de apoio correspondente"],
            ["Imagem que sugere prova inexistente"],
            ["Apoio visual identificado por cena"],
            {"coverage": "Duração suficiente para observar a ação"},
            ["multitrack"],
            "observation",
            [
                {
                    "sourceUrl": "https://www.instagram.com/p/Dct4pAohiup/",
                    "startSeconds": 3,
                    "endSeconds": 19,
                    "observation": "Resultado com vídeo dentro do recorte da roupa e explicação visual da composição.",
                    "audioVerified": False,
                }
            ],
        ),
        (
            "depth",
            "composition",
            "Profundidade por oclusão",
            "Separar fundo, assunto e primeiro plano.",
            ["Fotografia com recorte disponível", "Produto e cenário"],
            ["Oclusão do detalhe essencial"],
            ["Máscara estática", "Camadas separadas"],
            {"position": "Posição relativa", "mask": "Máscara em escala de cinza"},
            ["multitrack", "static_mask"],
            "observation",
            [
                {
                    "sourceUrl": "https://www.instagram.com/p/DRjjvOogSZg/",
                    "startSeconds": 0,
                    "endSeconds": 32.02,
                    "observation": "Composição de café explora escala e sobreposição com elementos em primeiro plano.",
                    "audioVerified": False,
                }
            ],
        ),
        (
            "state_reveal",
            "composition",
            "Revelação por estados",
            "Mostrar uma transformação em etapas legíveis.",
            ["Sequência de imagens relacionadas"],
            ["Intervalos curtos que impedem compreender o estado"],
            ["Imagens dos estados", "Relação explícita entre eles"],
            {"duration": "Tempo por estado, adaptado à leitura"},
            ["cut", "multitrack"],
            "observation",
            [
                {
                    "sourceUrl": "https://www.instagram.com/p/Dcys2J3MfYK/",
                    "startSeconds": 29,
                    "endSeconds": 48,
                    "observation": (
                        "Silhuetas, restauração de regiões e exportação de variantes; "
                        "tutorial mostra intervalos de 0,5 s, sem estabelecer regra universal."
                    ),
                    "audioVerified": False,
                }
            ],
        ),
        (
            "directed_motion",
            "composition",
            "Movimento para orientar atenção",
            "Guiar o olhar entre elementos relacionados.",
            ["Mudança de foco visual"],
            ["Movimento decorativo que disputa com a fala", "Preferência por movimento reduzido"],
            ["Elemento com espaço para deslocamento"],
            {"position": "Trajetória X/Y", "duration": "Tempo de deslocamento"},
            ["keyframes"],
            "principle",
            [],
        ),
        (
            "readable_text",
            "composition",
            "Texto com tempo de leitura",
            "Reforçar uma informação sem competir com a imagem.",
            ["Título curto", "Legenda de fala disponível"],
            ["Texto que acrescenta promessa não sustentada"],
            ["Texto fornecido ou transcrição"],
            {"fontSize": "Tamanho legível", "duration": "Intervalo da mensagem"},
            ["text"],
            "principle",
            [],
        ),
        (
            "speech_priority",
            "sound",
            "Prioridade da fala",
            "Reduzir a música quando existe fala e equilibrar os níveis.",
            ["Diálogo com música"],
            ["Compressão que elimina a dinâmica desejada"],
            ["Faixas separadas", "Direitos verificados da música"],
            {"ducking": "Redução guiada pelo sinal da fala", "loudness": "-16 LUFS de referência"},
            ["audio_mix", "ducking", "normalize"],
            "principle",
            [],
        ),
        (
            "intentional_pause",
            "sound",
            "Pausa intencional",
            "Dar tempo para compreender ou observar.",
            ["Demonstração detalhada", "Momento emocional"],
            ["Preencher toda pausa automaticamente com efeitos"],
            ["Intenção da cena"],
            {"duration": "Duração contextual"},
            ["cut", "audio_mix"],
            "principle",
            [],
        ),
    ]
    techniques = [
        EditingTechniqueV1(
            id=i,
            group=g,
            title=t,
            purpose=p,
            suitable_when=s,
            avoid_when=a,
            prerequisites=r,
            parameters=parameters,
            required_capabilities=c,
            evidence_type=e,
            sources=[x["sourceUrl"] for x in examples] or ["https://ffmpeg.org/ffmpeg-filters.html"],
            examples=examples,
        )
        for i, g, t, p, s, a, r, parameters, c, e, examples in data
    ]
    for identifier, title, width, height, entrance, seconds in [
        ("product_detail_zoom", "Detalhe do produto com aproximação", 0.8, 0.65, "zoom", 0.6),
        ("calm_visual_support", "Apoio visual com entrada suave", 0.7, 0.45, "fade", 0.8),
        ("explanatory_slide", "Demonstração com entrada lateral", 0.65, 0.5, "slide", 0.4),
    ]:
        techniques.append(
            EditingTechniqueV1(
                id=identifier,
                group="composition",
                title=title,
                purpose="Apresentar o material de apoio conforme o espaço, a duração e a identidade do projeto.",
                suitable_when=["Há material de apoio relevante e tempo para observá-lo"],
                avoid_when=["O movimento prejudica leitura ou cobre detalhes essenciais"],
                prerequisites=["Imagem ou vídeo de apoio"],
                parameters={
                    "width": "Proporção da tela",
                    "height": "Proporção da tela",
                    "duration": "Tempo de entrada",
                },
                required_capabilities=["multitrack", "keyframes" if entrance != "fade" else "transition"],
                evidence_type="principle",
                sources=["https://ffmpeg.org/ffmpeg-filters.html"],
                composition_profile={
                    "supportWidthRatio": width,
                    "supportHeightRatio": height,
                    "entrance": entrance,
                    "entranceSeconds": seconds,
                },
            )
        )
    import json
    from pathlib import Path

    from .editorial_principles import editorial_principles
    from .scene_compiler import COMPONENTS

    research = json.loads(Path(__file__).with_name("editorial_techniques_20260906.json").read_text(encoding="utf-8"))
    descriptions = {
        "typography": ("Tipografia seletiva", "Hierarquizar a mensagem e revelar palavras no ritmo da explicação."),
        "groups": ("Grupos e repetição", "Mostrar conjuntos relacionados com distribuição e entradas escalonadas."),
        "paths": ("Conexões vetoriais", "Explicar relações e percursos por linhas progressivas."),
        "depth": ("Máscaras e profundidade", "Separar planos e revelar mídia com recortes fornecidos."),
        "effects": (
            "Pilha de efeitos ordenada",
            "Aplicar correções visuais e modos de mistura em uma ordem reproduzível.",
        ),
        "panels": ("Cartões adaptáveis", "Organizar texto, imagens e dados em blocos comparáveis."),
        "semantic_compositions": (
            "Composições demonstráveis",
            "Executar relações visuais registradas com critérios verificáveis de compreensão.",
        ),
        "continuity": (
            "Continuidade motivada",
            "Conectar cenas por corte, dissolve, wipe ou transformação correspondente.",
        ),
        "sound_events": ("Som vinculado a eventos", "Orientar atenção com mixagem, silêncio e acentos sincronizados."),
    }
    executable = [
        EditingTechniqueV1(
            id="res-motion-v2-" + family,
            group="sound" if family == "sound_events" else "composition",
            title=descriptions[family][0],
            purpose=descriptions[family][1],
            suitable_when=["A relação visual ou sonora contribui para a compreensão"],
            avoid_when=["O movimento compete com a mensagem", "Material obrigatório não verificado"],
            prerequisites=["Parâmetros tipados e materiais compatíveis"],
            parameters={op: "Consultar os limites do plano contextual V2" for op in spec["operations"]},
            required_capabilities=[family],
            components=[family],
            required_material_kinds=["audio"] if family == "sound_events" else [],
            verification=["Conferir frames e intervalos do manifesto", "Revisão audiovisual permanece necessária"],
            evidence_type="principle",
            sources=[],
        )
        for family, spec in COMPONENTS.items()
    ]
    semantic_compositions = [
        EditingTechniqueV1(
            id="res-composition-" + identifier,
            version=1,
            qualification="implemented",
            group="composition",
            title=title,
            purpose=purpose,
            suitable_when=suitable,
            avoid_when=avoid,
            prerequisites=materials,
            parameters={
                "identity": "Tokens visuais do projeto",
                "duration": "Intervalo da ação observável",
                "hierarchy": "Relação entre hero, suporte e texto",
                "motion": "Perfil registrado no runtime",
            },
            required_capabilities=["semantic_compositions", identifier],
            components=["semantic_compositions"],
            required_material_kinds=required_kinds,
            verification=verification,
            evidence_type="principle",
            sources=[],
        )
        for identifier, title, purpose, suitable, avoid, materials, required_kinds, verification in [
            (
                "annotated_material",
                "Material com anotação vinculada",
                "Apontar uma evidência em imagem ou vídeo sem separar a anotação do alvo.",
                ["Existe uma região de interesse observável"],
                ["O material não mostra o detalhe alegado"],
                ["Imagem ou vídeo inspecionado", "Região de interesse"],
                [],
                ["Alvo e anotação aparecem juntos", "Conector termina na região indicada"],
            ),
            (
                "format_transformation",
                "Transformação reconhecível entre formatos",
                "Mostrar o mesmo material ocupando suportes diferentes e preservando sua identidade.",
                ["A mensagem explica adaptação ou distribuição entre formatos"],
                ["Rótulos desconectados substituem a transformação visual"],
                ["Um material reutilizado em ao menos dois estados"],
                [],
                ["O checksum ou asset de origem é comum aos estados", "A mudança ocorre na sequência"],
            ),
            (
                "demonstrative_interface",
                "Interface demonstrativa por eventos",
                "Demonstrar seleção, scroll ou mudança de estado em uma interface ilustrativa.",
                ["A interação ajuda a explicar uma ação"],
                ["A interface sugere métricas ou dados que não existem"],
                ["Estados e eventos explicitamente rotulados como demonstração"],
                [],
                ["Estado inicial, evento e consequência são observados"],
            ),
            (
                "continuity_comparison",
                "Comparação com continuidade",
                "Comparar dois estados mantendo um elemento visual comum.",
                ["A diferença entre antes e depois precisa ser localizada"],
                ["Os estados não possuem âncora visual comum"],
                ["Dois estados relacionados"],
                [],
                ["A âncora permanece identificável", "A mudança relevante recebe destaque"],
            ),
        ]
    ]
    cinematic_craft = [
        EditingTechniqueV1(
            id=identifier,
            version=1,
            qualification="knowledge_only",
            group=group,
            title=title,
            purpose=purpose,
            suitable_when=suitable,
            avoid_when=avoid,
            prerequisites=prerequisites,
            parameters=parameters,
            required_capabilities=capabilities,
            verification=verification,
            evidence_type="principle",
            sources=sources,
        )
        for (
            identifier, group, title, purpose, suitable, avoid, prerequisites,
            parameters, capabilities, verification, sources,
        ) in [
            (
                "cinema-visual-translation-v1",
                "montage",
                "Tradução visual antes da explicação",
                "Converter um conceito abstrato em ação, escala e consequência observáveis.",
                ["A mensagem contém processo, contraste ou transformação"],
                ["Uma associação decorativa seria confundida com evidência"],
                ["Storyboard e mensagem preservada"],
                {"shotScale": "Função informativa de cada escala", "duration": "Tempo necessário para observar a ação"},
                [],
                [
                    "A sequência continua compreensível sem o texto complementar",
                    "Cada corte altera conhecimento ou foco",
                ],
                ["https://www.dga.org/events/2024/may2024/duneparttwo_qna_0324"],
            ),
            (
                "cinema-attention-transfer-v1",
                "montage",
                "Transferência de atenção entre planos",
                "Posicionar e temporizar regiões essenciais para que o olhar encontre a próxima ação.",
                ["Há corte, revelação ou mudança de foco"],
                ["A desorientação é uma intenção editorial explícita"],
                ["Regiões de interesse observadas"],
                {"attentionStart": "Foco antes da mudança", "attentionEnd": "Foco esperado após a mudança"},
                [],
                ["A região essencial permanece legível nos dois lados do corte"],
                ["https://doi.org/10.3167/proj.2012.060102"],
            ),
            (
                "cinema-motivated-camera-v1",
                "composition",
                "Câmera motivada",
                "Usar movimento ou mudança de escala somente para revelar, acompanhar ou transferir atenção.",
                ["Existe um alvo ou informação que muda"],
                ["Zoom decorativo sem consequência"],
                ["Alvo e região de interesse"],
                {"movement": "push, pull, pan ou estático", "rationale": "Mudança produzida no público"},
                ["camera"],
                ["O movimento termina no alvo declarado", "Crop digital não é descrito como ângulo físico"],
                ["https://www.dga.org/craft/dgaq/issues/0604-winter-2006/dga-interview-steven-spielberg"],
            ),
            (
                "cinema-lighting-intent-v1",
                "composition",
                "Intenção de luz por função",
                "Selecionar ou compor luz por legibilidade, atmosfera e separação do assunto.",
                ["Filmagem, produto ou composição possui assunto principal"],
                ["O tratamento tentaria reluminar fisicamente um stock já gravado"],
                ["Modo de execução declarado"],
                {"quality": "suave, dura, disponível ou gráfica", "contrast": "relação entre assunto e ambiente"},
                [],
                ["A fonte de luz é compatível entre planos", "O assunto se separa do fundo"],
                ["https://www.arri.com/en/learn-help/lighting/lighting-handbook"],
            ),
            (
                "cinema-procedural-evidence-v1",
                "montage",
                "Procedimento como evidência",
                "Dramatizar somente detalhes de interface e trabalho que alteram a compreensão da ação.",
                ["Tutorial, processo ou demonstração de produto"],
                ["A interface inventaria métricas ou resultados"],
                ["Estados inicial, ação e consequência"],
                {"deviation": "Mudança mensurável entre estados", "insert": "Detalhe necessário para provar a ação"},
                ["demonstrative_interface"],
                ["A ação declarada ocorre nos frames observados", "Dados ilustrativos são identificados"],
                ["https://www.dga.org/craft/dgaq/issues/1301-winter-2013/house-of-cards"],
            ),
        ]
    ]
    cinematic_craft.extend(
        EditingTechniqueV1(
            id=identifier,
            version=1,
            qualification="knowledge_only",
            group=group,
            title=title,
            purpose=purpose,
            suitable_when=suitable,
            avoid_when=avoid,
            prerequisites=prerequisites,
            parameters=parameters,
            required_capabilities=capabilities,
            verification=verification,
            evidence_type="principle",
            sources=sources,
        )
        for (
            identifier,
            group,
            title,
            purpose,
            suitable,
            avoid,
            prerequisites,
            parameters,
            capabilities,
            verification,
            sources,
        ) in [
            (
                "cinema-state-action-consequence-v1",
                "montage",
                "Estado, ação e consequência verificáveis",
                "Transformar uma descrição de cena em uma afirmação visual falsificável.",
                ["Processo, comparação, adaptação, distribuição ou uso de produto"],
                ["Caixas, rótulos ou movimento genérico substituem a ação alegada"],
                ["Objeto canônico", "Intervalo", "Estado inicial e final"],
                {
                    "object": "Entidade persistente",
                    "event": "Mudança observável",
                    "evidence": "Frames, sequência ou áudio exigidos",
                    "counterexample": "Resultado que deve reprovar",
                },
                ["semantic_assertions"],
                [
                    "Diferença de pixels valida apenas execução",
                    "Toda ação essencial tem evidência ou permanece inconclusiva",
                ],
                ["https://arxiv.org/abs/2501.02955"],
            ),
            (
                "cinema-canonical-content-adaptation-v1",
                "composition",
                "Conteúdo canônico adaptado entre formatos",
                "Reorganizar partes persistentes sem trocar a identidade do conteúdo.",
                ["Post, story, reel, carrossel ou feed compartilham a mesma peça"],
                ["Cartões vazios, imagens distintas ou IDs internos simulam continuidade"],
                ["Mídia principal", "Título", "Identidade versionada"],
                {
                    "parts": "primary_media, title, identity, body e CTA",
                    "layouts": "Estados derivados medidos pelo compositor",
                },
                ["format_transformation", "semantic_assertions"],
                [
                    "Partes obrigatórias aparecem em cada estado exportado",
                    "Ao menos dois viewports têm proporções distintas",
                ],
                [
                    "https://idl.cs.washington.edu/files/2007-AnimatedTransitions-InfoVis.pdf",
                    "https://m1.material.io/motion/choreography.html",
                ],
            ),
            (
                "cinema-screen-replacement-boundary-v1",
                "composition",
                "Substituição de tela como composição rastreada",
                "Impedir que chroma ou uma sobreposição plana sejam tratados como tela finalizada.",
                ["Filmagem autorizada tem superfície planar rastreável"],
                ["Tracking, corner pin, oclusão ou integração de cor não estão disponíveis"],
                ["Cobertura de tracking", "Quatro cantos", "Política de oclusão"],
                {"processing": "tracking, corner pin, keying, occlusion e color integration"},
                ["screen_tracking", "corner_pin"],
                ["O insert permanece aderente no início, trecho mais difícil e final"],
                [
                    "https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/track-motion/tracking-stabilizing-motion-cs5.html"
                ],
            ),
            (
                "cinema-word-safe-kinetic-type-v1",
                "composition",
                "Tipografia cinética preservando palavras",
                "Aplicar ênfase sem fragmentar palavras, glifos ou oportunidades naturais de quebra.",
                ["Palavras-chave curtas e ligadas ao roteiro"],
                ["Texto longo, ressalva ou corpo factual é fragmentado por decoração"],
                ["Fonte final carregada", "Offsets por palavra", "Safe area"],
                {"contrast": "4,5:1 normal e 3:1 grande como referências internas", "preview": "300 px"},
                ["typography"],
                ["Nenhum glifo corta nos extremos de escala", "Nenhuma palavra quebra dentro de um span"],
                ["https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html"],
            ),
            (
                "cinema-causal-sound-events-v1",
                "sound",
                "Som causal e silêncio explícito",
                "Vincular efeitos, ambiente e música à função e ao frame da ação.",
                ["Publicação, inserção, passagem, transição ou pausa pede suporte auditivo"],
                ["Som inventa uma notificação ou reação ausente da imagem"],
                ["Evento", "Fonte licenciada ou sintética", "Manifesto temporal"],
                {"trigger": "Frame do evento", "perspective": "Origem e distância", "silence": "Intencional ou falha"},
                ["sound_events", "audio_mix"],
                ["O intervalo exportado contém sinal audível", "Silêncio necessário está declarado"],
                ["https://filmsound.org/murch/stretching.htm"],
            ),
            (
                "cinema-dimensional-evaluation-v1",
                "montage",
                "Avaliação dimensional com cobertura declarada",
                "Separar execução, significado e compreensão humana sem condensar bloqueadores em uma nota.",
                ["Render, animatic, material gerado ou correção automática"],
                ["Uma nota agregada compensa ação ausente ou intervalo não observado"],
                ["Checksum", "Intervalos amostrados", "Afirmações essenciais"],
                {"gates": "execution, semantic e human", "coverage": "static ou temporal"},
                ["visual_audit"],
                [
                    "Fixtures negativos não passam semanticamente",
                    "Fixtures positivos equivalentes continuam elegíveis",
                ],
                ["https://arxiv.org/abs/2311.17982", "https://arxiv.org/abs/2501.02955"],
            ),
        ]
    )
    external_workflow_principles = [
        EditingTechniqueV1(
            id="reference-role-lock-v1",
            version=1,
            qualification="knowledge_only",
            group="composition",
            title="Referências com função visual explícita",
            purpose=(
                "Fixar o que cada referência controla — aparência, enquadramento, "
                "objeto ou movimento — sem copiar pessoas, texto, logos ou elementos não solicitados."
            ),
            suitable_when=["Uma peça precisa manter coerência entre materiais adquiridos ou gerados"],
            avoid_when=["A origem, os direitos ou a função da referência são desconhecidos"],
            prerequisites=["Referência identificada", "Função declarada", "Procedência registrada"],
            parameters={
                "referenceRole": "style, framing, subject, motion ou authoritative_asset",
                "mustPreserve": "Invariantes que não podem derivar",
                "mustNotControl": "Aspectos fora do escopo da referência",
            },
            required_capabilities=[],
            verification=[
                "A direção registra a função de cada referência",
                "O resultado não incorpora conteúdo não autorizado da referência",
            ],
            evidence_type="principle",
            sources=[
                "https://github.com/higgsfield-ai/skills/blob/main/higgsfield-brandkit/references/brand-lock.md",
                "https://github.com/higgsfield-ai/skills/blob/main/higgsfield-video-explainer/references/prompts.md",
            ],
        ),
        EditingTechniqueV1(
            id="localized-visual-repair-v1",
            version=1,
            qualification="knowledge_only",
            group="composition",
            title="Correção visual localizada por causa",
            purpose=(
                "Separar defeitos de material, geração, layout e composição para refazer "
                "somente o derivado responsável e preservar decisões aprovadas."
            ),
            suitable_when=["O candidato tem uma falha visual identificada e localizada"],
            avoid_when=["A ideia visual inteira não demonstra a mensagem"],
            prerequisites=["Checksum do candidato", "Achado com cena e intervalo", "Dependências versionadas"],
            parameters={"failureClass": "material, generative, layout, composition ou direction"},
            required_capabilities=[],
            verification=[
                "Somente dependentes do elemento defeituoso foram invalidados",
                "O candidato corrigido foi inspecionado novamente",
            ],
            evidence_type="principle",
            sources=[
                "https://github.com/higgsfield-ai/skills/blob/main/higgsfield-brandkit/references/qa-and-iteration.md"
            ],
        ),
    ]
    return [
        *techniques,
        *editorial_principles(),
        *(EditingTechniqueV1.model_validate(t) for t in research),
        *(
            EditingTechniqueV1.model_validate(t)
            for t in json.loads(Path(__file__).with_name("motion_vox_knowledge.v1.json").read_text(encoding="utf-8"))
        ),
        *(
            EditingTechniqueV1.model_validate(t)
            for t in json.loads(
                Path(__file__).with_name("pinterest_motion_knowledge.v1.json").read_text(encoding="utf-8")
            )
        ),
        *executable,
        *semantic_compositions,
        *cinematic_craft,
        *external_workflow_principles,
        *research_operation_cards(),
    ]


def store_technique(db, workspace_id, technique, observation=None):
    # Metrics have their own immutable observations; they do not multiply chunks.
    content = technique.model_dump_json(by_alias=True)
    content_hash = digest({"editingTechnique": technique.model_dump(mode="json")})
    record = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.content_hash == content_hash
        )
    )
    if record is None:
        record = KnowledgeDocument(
            workspace_id=workspace_id,
            title=technique.title,
            source_type="editing-technique",
            source_url=technique.sources[0] if technique.sources else None,
            content_hash=content_hash,
            status="ready",
            embedding_status="unconfigured",
            document_metadata={"technique": technique.model_dump(mode="json", by_alias=True), "observations": []},
        )
        db.add(record)
        db.flush()
        for index, chunk in enumerate(chunk_content(content)):
            db.add(
                KnowledgeChunk(
                    document_id=record.id,
                    workspace_id=workspace_id,
                    chunk_index=index,
                    content=chunk.content,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    citation={"sourceUrl": record.source_url, "techniqueId": technique.id},
                    embedding=None,
                )
            )
    metadata = dict(record.document_metadata)
    if observation:
        observations = list(metadata.get("observations", []))
        item = observation.model_dump(mode="json", by_alias=True)
        fingerprint = digest(item)
        if not any(o["digest"] == fingerprint for o in observations):
            observations.append({"digest": fingerprint, **item})
        metadata["observations"] = observations
        metadata["lastObservedAt"] = (
            max(datetime.fromisoformat(o["observedAt"]) for o in observations).astimezone(UTC).isoformat()
        )
    metadata["lastSuccessfulIngestAt"] = datetime.now(UTC).isoformat()
    metadata["collectionMode"] = "manual"
    metadata["causalPerformanceClaim"] = False
    record.document_metadata = metadata
    db.flush()
    return record


def store_render_example(db, workspace_id, production_state, review_receipt):
    """Store a tenant-scoped human example without treating it as training or a technique."""
    plan = (production_state.get("artifacts") or {}).get("plan") or {}
    direction = plan.get("direction") or {}
    scenes = direction.get("scenes") or []
    techniques = sorted(
        {
            technique_id
            for scene in scenes
            for technique_id in scene.get("techniqueIds", scene.get("technique_ids", []))
        }
    )
    compositions = sorted(
        {
            composition.get("family")
            for scene in scenes
            for composition in scene.get("compositions", [])
            if composition.get("family")
        }
    )
    operation_bindings = [
        {"sceneId": scene.get("id"), **binding}
        for scene in scenes for binding in scene.get("operationBindings", [])
    ]
    decision = "accepted" if review_receipt.get("status") == "meets_human_criteria" else "rejected"
    example = {
        "schemaVersion": "studio.render-example.v1",
        "decision": decision,
        "evaluatorType": "human",
        "productionRunId": production_state.get("id"),
        "documentId": production_state.get("documentId"),
        "documentRevision": production_state.get("documentRevision"),
        "renderChecksum": review_receipt.get("renderChecksum"),
        "review": review_receipt,
        "techniqueIds": techniques,
        "operationBindings": operation_bindings,
        "failureCause": review_receipt.get("failureCause"),
        "compositionFamilies": compositions,
        "executionVersions": direction.get("executionVersions"),
        "automaticEvaluation": production_state.get("visualAudit"),
        "trainingApplied": False,
        "causalPerformanceClaim": False,
    }
    content = json.dumps(example, ensure_ascii=False, sort_keys=True)
    content_hash = digest({"renderExample": example})
    record = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == workspace_id,
            KnowledgeDocument.content_hash == content_hash,
        )
    )
    if record is not None:
        return record
    record = KnowledgeDocument(
        workspace_id=workspace_id,
        title=f"Exemplo de render {decision} — {str(example['renderChecksum'] or '')[:12]}",
        source_type="editing-example",
        language="pt-BR",
        content_hash=content_hash,
        status="ready",
        embedding_status="unconfigured",
        document_metadata=example,
    )
    db.add(record)
    db.flush()
    for index, chunk in enumerate(chunk_content(content)):
        db.add(
            KnowledgeChunk(
                document_id=record.id,
                workspace_id=workspace_id,
                chunk_index=index,
                content=chunk.content,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                citation={
                    "documentId": record.id,
                    "sourceType": "editing-example",
                    "renderChecksum": example["renderChecksum"],
                    "decision": decision,
                },
                embedding=None,
            )
        )
    db.flush()
    return record


def ensure_repertoire(db, workspace_id):
    return [store_technique(db, workspace_id, t) for t in seed_techniques()]


def ingest_observation(db, workspace_id, request: EditingObservationV1):
    if request.observed_at > datetime.now(UTC):
        raise ValueError("editing_observation_in_future")
    record = store_technique(db, workspace_id, request.technique, request)
    db.commit()
    return {"documentId": record.id, **record.document_metadata}


def search_repertoire(db, workspace_id, query):
    # No embeddings request: this production path cannot call GPT/OpenAI.
    return hybrid_search(db, workspace_id, query, None, 12)


def available_repertoire(db, workspace_id):
    techniques = {t.id: t for t in seed_techniques()}
    records = db.scalars(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.workspace_id == workspace_id,
            KnowledgeDocument.source_type == "editing-technique",
            KnowledgeDocument.status == "ready",
        )
        .order_by(KnowledgeDocument.created_at, KnowledgeDocument.id)
    ).all()
    for record in records:
        raw = (record.document_metadata or {}).get("technique")
        if raw:
            technique = EditingTechniqueV1.model_validate(raw)
            techniques[technique.id] = technique
    return list(techniques.values())


def rank_repertoire(
    techniques,
    query,
    capabilities,
    *,
    requested_ids=(),
    retrieved_ids=(),
    material_kinds=None,
    limit=24,
    allow_missing_materials=False,
):
    """Rank before truncating; knowledge without an executable recipe remains knowledge."""
    import re
    import unicodedata

    def tokens(value):
        plain = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode()
        return set(re.findall(r"[a-z0-9]{3,}", plain))

    terms, requested = tokens(query), set(requested_ids)
    ranked = []
    for technique in techniques:
        if not set(technique.required_capabilities) <= set(capabilities):
            continue
        if (
            not allow_missing_materials
            and material_kinds is not None
            and not set(technique.required_material_kinds) <= set(material_kinds)
        ):
            continue
        title_terms = tokens(technique.title + " " + technique.id)
        body_terms = tokens(" ".join([technique.purpose, *technique.suitable_when, *technique.prerequisites]))
        score = 5 * len(terms & title_terms) + len(terms & body_terms)
        if technique.id in requested:
            score += 10000
        elif technique.id in retrieved_ids:
            score += 100
        ranked.append((score, technique.id, technique))
    ordered = sorted(ranked, key=lambda row: (-row[0], row[1]))
    # Preserve relevance while avoiding a context made entirely from one craft
    # group when other positively relevant groups are available.
    selected = []
    selected_ids = set()
    for _, identifier, technique in ordered:
        if len(selected) >= limit:
            break
        if identifier in requested:
            selected.append(technique)
            selected_ids.add(identifier)
    if ordered and len(selected) < limit and ordered[0][1] not in selected_ids:
        selected.append(ordered[0][2])
        selected_ids.add(ordered[0][1])
    for group in ("montage", "composition", "sound"):
        candidate = next(
            (
                row
                for row in ordered
                if row[2].group == group
                and (row[0] > 0 or row[2].id in requested or row[2].id in retrieved_ids)
            ),
            None,
        )
        if candidate and candidate[1] not in selected_ids and len(selected) < limit:
            selected.append(candidate[2])
            selected_ids.add(candidate[1])
    for _, identifier, technique in ordered:
        if len(selected) >= limit:
            break
        if identifier not in selected_ids:
            selected.append(technique)
            selected_ids.add(identifier)
    return selected


def planning_repertoire(db, workspace_id, query, capabilities, requested_ids=(), *, material_kinds=None):
    techniques = available_repertoire(db, workspace_id)
    hits = search_repertoire(db, workspace_id, query) if query.strip() else []
    # Hybrid retrieval supplements lexical relevance while keeping a deterministic tie break.
    hit_documents = {hit["documentId"] for hit in hits}
    retrieved_ids = []
    if hit_documents:
        for record in db.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.id.in_(hit_documents)
            )
        ):
            raw = (record.document_metadata or {}).get("technique", {})
            if raw.get("id"):
                retrieved_ids.append(raw["id"])
    return rank_repertoire(
        techniques,
        query,
        capabilities,
        requested_ids=requested_ids,
        retrieved_ids=retrieved_ids,
        material_kinds=material_kinds,
        allow_missing_materials=True,
    )


def contextual_references(db, workspace_id, query, requested_ids, capabilities):
    """Retrieve evidence; only explicit typed profiles can change execution parameters."""
    hits = search_repertoire(db, workspace_id, query)
    hit_ids = {h["documentId"] for h in hits}
    records = db.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == workspace_id,
            KnowledgeDocument.source_type == "editing-technique",
            KnowledgeDocument.status == "ready",
        )
    ).all()
    latest = {}
    for record in records:
        raw = (record.document_metadata or {}).get("technique")
        if not raw:
            continue
        technique = EditingTechniqueV1.model_validate(raw)
        if technique.id not in latest or (record.created_at, record.id) > (
            latest[technique.id][0].created_at,
            latest[technique.id][0].id,
        ):
            latest[technique.id] = (record, technique)
    evidence, profiles, unavailable = [], [], []
    for technique_id in requested_ids:
        pair = latest.get(technique_id)
        if not pair or not set(pair[1].required_capabilities) <= set(capabilities):
            unavailable.append(technique_id)
            continue
        record, technique = pair
        if technique.composition_profile:
            profiles.append((record.id, technique))
    for record, technique in latest.values():
        if record.id not in hit_ids and technique.id not in requested_ids:
            continue
        metadata = record.document_metadata or {}
        observed = metadata.get("lastObservedAt")
        age = (datetime.now(UTC) - datetime.fromisoformat(observed)).days if observed else None
        evidence.append(
            {
                "type": "reference",
                "documentId": record.id,
                "techniqueId": technique.id,
                "evidenceType": technique.evidence_type,
                "sources": technique.sources,
                "requiredCapabilities": technique.required_capabilities,
                "observedAt": observed,
                "observationAgeDays": age,
                "freshness": "undated" if age is None else "recent" if age <= 30 else "historical",
                "selection": "requested" if technique.id in requested_ids else "retrieved",
                "causalPerformanceClaim": False,
                "techniqueDigest": digest(technique),
            }
        )
    return evidence, profiles, unavailable
