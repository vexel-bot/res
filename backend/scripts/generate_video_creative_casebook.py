from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.creative_autonomy import (
    AnimaticPlanV1,
    CreativeAutonomyCaseV1,
    CreativeEvidenceV1,
    CreativePilotCasebookV1,
    CreativeScriptV1,
    ExecutableStoryboardV1,
    FormatRecipeV1,
    FormatRouterV1,
    LearningRecordV1,
    MessageArchitectureV1,
    SoundDesignPlanV1,
    VisualDirectionV1,
    creative_script_digest,
    executable_storyboard_digest,
    format_recipe_digest,
    format_router_digest,
    message_architecture_digest,
    sound_design_plan_digest,
    visual_direction_digest,
)

FAMILIES = {
    "presenter_ugc": {
        "recipe_id": "recipe-f1-presenter-ugc-v1",
        "name": "F1 — Apresentador/UGC contextual",
        "min_ms": 15_000,
        "max_ms": 45_000,
        "capabilities": ["multi_asset_timeline", "captions", "natural_sound", "safe_zones"],
        "modalities": ["presenter", "product", "screen_ui", "typography", "environment"],
        "layout": [
            "Manter rosto, produto e CTA fora das áreas de interface da plataforma.",
            "Usar inserts somente quando provarem ou demonstrarem a mensagem do beat.",
        ],
        "motion": [
            "Priorizar movimento real, punch-ins motivados e captions por unidade de sentido.",
            "Não ocultar cortes de performance com transições decorativas.",
        ],
        "audio": [
            "Ligar foley a ações visíveis e preservar inteligibilidade do texto.",
            "Não introduzir voz, conversa ou música em recipes natural-foley-only.",
        ],
        "fallback": None,
    },
    "split_screen_proof": {
        "recipe_id": "recipe-f2-split-screen-proof-v1",
        "name": "F2 — Split-screen de prova/tutorial",
        "min_ms": 15_000,
        "max_ms": 60_000,
        "capabilities": ["multi_asset_timeline", "split_layout", "captions", "source_attribution"],
        "modalities": ["presenter", "screen_ui", "source_video", "typography", "data", "product"],
        "layout": [
            "Dar uma região dominante à prova e uma região secundária à explicação.",
            "Preservar legibilidade da fonte e atribuição estrutural sem reproduzir identidade visual.",
        ],
        "motion": [
            "Usar zoom, highlight e cursor apenas para orientar o olhar.",
            "Sincronizar mudança de foco com o passo explicado.",
        ],
        "audio": [
            "Usar som de interface apenas quando ligado a uma ação visível.",
            "Evitar competição entre fala, fonte e efeitos.",
        ],
        "fallback": "recipe-f1-presenter-ugc-v1",
    },
    "motion_visual_essay": {
        "recipe_id": "recipe-f3-motion-visual-essay-v1",
        "name": "F3 — Motion/ensaio visual",
        "min_ms": 15_000,
        "max_ms": 60_000,
        "capabilities": ["motion_graph", "kinetic_type", "shape_system", "sound_events"],
        "modalities": ["typography", "shape", "data", "screen_ui", "archive", "source_video", "environment"],
        "layout": [
            "Uma ideia dominante por frame e hierarquia legível sem movimento.",
            "Transformar conceitos por relações causais, não por ícones genéricos.",
        ],
        "motion": [
            "Animar por unidades de sentido com easing coerente com massa e intenção.",
            "Oferecer reduced-motion e preservar o significado no frame estático.",
        ],
        "audio": [
            "Projetar impactos, silêncio e textura desde o animatic.",
            "Não usar som para compensar uma transformação visual incompreensível.",
        ],
        "fallback": "recipe-f2-split-screen-proof-v1",
    },
    "cinematic_hybrid": {
        "recipe_id": "recipe-f4-cinematic-hybrid-v1",
        "name": "F4 — Cinematográfico/híbrido/VFX",
        "min_ms": 15_000,
        "max_ms": 60_000,
        "capabilities": ["multi_shot_state", "reality_constraints", "compositing", "cinematic_sound"],
        "modalities": ["presenter", "product", "environment", "generated_scene", "typography", "shape", "avatar"],
        "layout": [
            "Manter sujeito, objeto e direção reconhecíveis entre real e gerado.",
            "Reservar tipografia para promessa, orientação ou payoff.",
        ],
        "motion": [
            "Usar match de gesto, composição, direção ou som nas transformações.",
            "Declarar toda quebra intencional de física antes da geração.",
        ],
        "audio": [
            "Vincular eventos sonoros a contato, ambiente e transformação.",
            "Usar silêncio para contraste quando houver payoff visual.",
        ],
        "fallback": "recipe-f3-motion-visual-essay-v1",
    },
}


CASES = [
    {
        "id": "pilot-f1-coffee-ritual",
        "family": "presenter_ugc",
        "title": "O ritual do café sem fala",
        "duration": 15_000,
        "golden": True,
        "objective": "Apresentar uma assinatura de café sem inventar preço, origem ou benefício.",
        "audience": "Pessoas que variam o café em casa e querem comparar opções.",
        "before": "Escolher café por assinatura parece uma decisão abstrata.",
        "after": "A pessoa entende que pode avaliar seleção e condições antes de pedir.",
        "thesis": "A rotina de preparo torna a proposta concreta sem depender de fala.",
        "promise": "Mostrar como a assinatura entra em um ritual real.",
        "mechanism": "Ação de preparo, embalagem e condições apresentadas em captions editoriais.",
        "cta": "Confira a seleção e as condições do primeiro envio.",
        "modalities": ["presenter", "product", "typography", "environment"],
        "visual": (
            "Pessoa prepara café em cozinha real; produto permanece identificável e captions não cobrem mãos "
            "ou caneca."
        ),
        "sound_mode": "natural_foley_only",
        "sound_roles": ["location_sound", "foley", "foley", "silence", "foley"],
        "reference": None,
        "metaphor": None,
    },
    {
        "id": "pilot-f1-saas-workflow",
        "family": "presenter_ugc",
        "title": "Um conteúdo atravessando o fluxo",
        "duration": 20_000,
        "golden": False,
        "objective": "Demonstrar organização de conteúdo sem prometer velocidade ou resultado comercial.",
        "audience": "Gestores de conteúdo que alternam entre muitas ferramentas.",
        "before": "O trabalho parece uma coleção de telas desconectadas.",
        "after": "A pessoa reconhece o valor de acompanhar a peça do brief à revisão.",
        "thesis": "Visibilidade do fluxo reduz a sensação de perda de contexto.",
        "promise": "Mostrar um exemplo verificável de passagem entre etapas.",
        "mechanism": "Presenter demonstra uma ação real na interface com inserts legíveis.",
        "cta": "Conheça o fluxo guiado.",
        "modalities": ["presenter", "screen_ui", "typography", "environment"],
        "visual": "Presenter em mesa de trabalho, tela real como insert e destaque localizado na etapa ativa.",
        "sound_mode": "natural_foley_only",
        "sound_roles": ["location_sound", "interface", "interface", "silence", "interface"],
        "reference": None,
        "metaphor": None,
    },
    {
        "id": "pilot-f1-chair-mechanism",
        "family": "presenter_ugc",
        "title": "Ajustes de cadeira que podem ser vistos",
        "duration": 20_000,
        "golden": False,
        "objective": "Demonstrar mecanismos documentados de uma cadeira sem alegação ergonômica inventada.",
        "audience": "Pessoas comparando cadeiras para o espaço de trabalho.",
        "before": "Os controles parecem iguais e difíceis de avaliar em uma ficha.",
        "after": "A pessoa sabe quais ajustes verificar e onde consultar medidas.",
        "thesis": "Uma demonstração fiel é mais útil que um superlativo.",
        "promise": "Mostrar os ajustes documentados e sua operação.",
        "mechanism": "Close-ups de mão, controle e consequência mecânica com labels.",
        "cta": "Confira mecanismos e medidas na ficha.",
        "modalities": ["presenter", "product", "typography", "environment"],
        "visual": "Mãos operam altura, braço e inclinação; cada ação mantém contato e estado do mecanismo.",
        "sound_mode": "natural_foley_only",
        "sound_roles": ["location_sound", "foley", "foley", "foley", "silence"],
        "reference": None,
        "metaphor": None,
    },
    {
        "id": "pilot-f2-depth-layer-explainer",
        "family": "split_screen_proof",
        "title": "Camadas de profundidade explicadas com prova",
        "duration": 20_000,
        "golden": True,
        "objective": (
            "Ensinar como uma separação de profundidade altera uma composição sem copiar o tutorial de "
            "referência."
        ),
        "audience": "Criadores iniciantes em composição e movimento de câmera.",
        "before": "Profundidade parece um efeito mágico e opaco.",
        "after": "A pessoa entende fonte, separação de planos e resultado.",
        "thesis": "Mostrar mecanismo e resultado juntos torna a técnica verificável.",
        "promise": "Decompor a profundidade em três passos visíveis.",
        "mechanism": "Fonte em região dominante, explicação em região secundária e labels sobre planos.",
        "cta": "Compare fonte, mapa e resultado.",
        "modalities": ["presenter", "source_video", "screen_ui", "typography"],
        "visual": "Layout superior/inferior com fonte legível, presenter e highlight em uma única área por vez.",
        "sound_mode": "spoken_with_foley",
        "sound_roles": ["dialogue", "dialogue", "interface", "dialogue", "interface"],
        "reference": "https://www.instagram.com/reel/DcuHK9ChRrP/",
        "metaphor": None,
    },
    {
        "id": "pilot-f2-caption-safe-zone",
        "family": "split_screen_proof",
        "title": "Legenda bonita que não cobre o produto",
        "duration": 20_000,
        "golden": False,
        "objective": "Comparar uma legenda invasiva com uma composição segura e legível.",
        "audience": "Editores de vídeo vertical e social media.",
        "before": "Legenda é tratada como camada independente do enquadramento.",
        "after": "A pessoa reconhece que texto, rosto, produto e UI disputam espaço.",
        "thesis": "Safe zone é uma decisão de composição, não um ajuste final.",
        "promise": "Mostrar a mesma cena antes e depois da correção.",
        "mechanism": "Comparação simultânea com overlays de áreas ocupadas.",
        "cta": "Revise o frame final no tamanho de publicação.",
        "modalities": ["source_video", "typography", "data"],
        "visual": "Dois frames sincronizados, mapas de ocupação e uma conclusão que isola a solução.",
        "sound_mode": "narrated_editorial",
        "sound_roles": ["narration", "narration", "interface", "narration", "silence"],
        "reference": None,
        "metaphor": None,
    },
    {
        "id": "pilot-f2-hook-anatomy",
        "family": "split_screen_proof",
        "title": "Anatomia de um hook honesto",
        "duration": 30_000,
        "golden": False,
        "objective": "Explicar a ligação entre promessa inicial, prova e payoff.",
        "audience": "Criadores e redatores de vídeos curtos.",
        "before": "Hook é entendido apenas como frase chamativa.",
        "after": "A pessoa vê o hook como expectativa que o vídeo precisa pagar.",
        "thesis": "Promessa sem payoff produz curiosidade vazia.",
        "promise": "Marcar no vídeo onde a expectativa abre e onde fecha.",
        "mechanism": "Vídeo de exemplo, timeline e labels ligados por cor.",
        "cta": "Audite a promessa e o payoff do próximo roteiro.",
        "modalities": ["source_video", "screen_ui", "typography", "data"],
        "visual": "Timeline ocupa a base, vídeo ocupa o centro e labels conectam hook, prova e payoff.",
        "sound_mode": "narrated_editorial",
        "sound_roles": ["narration", "narration", "interface", "narration", "impact"],
        "reference": None,
        "metaphor": None,
    },
    {
        "id": "pilot-f3-distribution-network",
        "family": "motion_visual_essay",
        "title": "Uma boa ideia ainda precisa chegar",
        "duration": 30_000,
        "golden": True,
        "objective": "Explicar distribuição como mecanismo entre conteúdo e público.",
        "audience": "Fundadores e criadores com produção consistente e pouco alcance.",
        "before": "Qualidade isolada parece suficiente para gerar alcance.",
        "after": "A pessoa entende distribuição como sistema de caminhos, repetição e contexto.",
        "thesis": "Uma ideia sem caminho até o público permanece invisível.",
        "promise": "Tornar visível a diferença entre núcleo e rede.",
        "mechanism": "Forma isolada se transforma em rede e recebe sinais de circulação.",
        "cta": "Planeje o caminho junto com a ideia.",
        "modalities": ["shape", "typography", "screen_ui", "environment"],
        "visual": "Sistema preto, branco e azul; um núcleo isolado ganha rotas, contexto de plataforma e consequência.",
        "sound_mode": "narrated_editorial",
        "sound_roles": ["impact", "narration", "interface", "narration", "silence"],
        "reference": "https://www.instagram.com/reel/DciIBRYBHBK/",
        "metaphor": (
            "rede de caminhos",
            "distribuição de conteúdo",
            "um núcleo só alcança outros pontos quando existem rotas",
        ),
    },
    {
        "id": "pilot-f3-content-bottleneck",
        "family": "motion_visual_essay",
        "title": "O gargalo não está onde parece",
        "duration": 25_000,
        "golden": False,
        "objective": "Mostrar como excesso de handoffs interrompe a produção de conteúdo.",
        "audience": "Times pequenos de marketing e agências.",
        "before": "A demora parece vir somente da criação.",
        "after": "A pessoa identifica filas e devoluções como parte do tempo total.",
        "thesis": "Fluxo interrompido pode custar mais tempo que a criação inicial.",
        "promise": "Visualizar onde o trabalho para e retorna.",
        "mechanism": "Objetos atravessam um sistema de filas com estados e retornos.",
        "cta": "Mapeie a próxima devolução do seu fluxo.",
        "modalities": ["shape", "typography", "data", "screen_ui"],
        "visual": "Blocos passam por estações; filas aumentam, uma devolução retorna e o fluxo final simplifica.",
        "sound_mode": "narrated_editorial",
        "sound_roles": ["impact", "interface", "narration", "interface", "silence"],
        "reference": None,
        "metaphor": ("fila com retornos", "gargalo operacional", "cada devolução aumenta o trabalho em processo"),
    },
    {
        "id": "pilot-f3-retention-events",
        "family": "motion_visual_essay",
        "title": "Retenção é uma sequência de eventos",
        "duration": 30_000,
        "golden": False,
        "objective": "Explicar por que cortes devem seguir eventos e objetivos, não um cronômetro fixo.",
        "audience": "Editores e criadores que usam cortes rápidos como regra geral.",
        "before": "Mais cortes parecem significar automaticamente mais retenção.",
        "after": "A pessoa percebe ritmo como mudança de informação, ação ou emoção.",
        "thesis": "Um corte funciona quando marca ou conecta uma mudança compreensível.",
        "promise": "Comparar corte por relógio com corte por evento.",
        "mechanism": "Duas timelines exibem a mesma ação segmentada por regras diferentes.",
        "cta": "Marque a mudança antes de escolher o corte.",
        "modalities": ["typography", "shape", "data", "source_video"],
        "visual": "Timeline dupla, eventos destacados e uma curva de compreensão como hipótese, não dado real.",
        "sound_mode": "narrated_editorial",
        "sound_roles": ["narration", "interface", "impact", "narration", "silence"],
        "reference": None,
        "metaphor": (
            "fronteiras em uma linha",
            "segmentação de eventos",
            "mudanças de objetivo dividem a ação em unidades",
        ),
    },
    {
        "id": "pilot-f4-product-portal",
        "family": "cinematic_hybrid",
        "title": "O produto abre o próprio universo",
        "duration": 30_000,
        "golden": True,
        "objective": "Criar transformação cinematográfica preservando produto, gesto e direção.",
        "audience": "Marcas que precisam apresentar atmosfera sem perder legibilidade do produto.",
        "before": "O produto aparece separado do mundo que promete evocar.",
        "after": "A pessoa entende a atmosfera como extensão do gesto e do objeto.",
        "thesis": "Uma transição motivada pode ligar uso real e universo de marca.",
        "promise": "Fazer o ambiente nascer de uma ação visível com o produto.",
        "mechanism": "Contato inicia mudança de luz, match de gesto atravessa o portal e produto persiste.",
        "cta": "Entre no universo da coleção.",
        "modalities": ["presenter", "product", "environment", "generated_scene", "typography"],
        "visual": (
            "Ambiente real se transforma por contato; produto mantém geometria e lado; mundo final herda cor e luz."
        ),
        "sound_mode": "cinematic_mix",
        "sound_roles": ["location_sound", "foley", "riser", "impact", "silence"],
        "reference": None,
        "metaphor": (
            "portal acionado pelo produto",
            "entrada no universo da marca",
            "o gesto de uso causa a transformação do ambiente",
        ),
    },
    {
        "id": "pilot-f4-gravity-of-data",
        "family": "cinematic_hybrid",
        "title": "Quando dados ganham peso",
        "duration": 30_000,
        "golden": False,
        "objective": "Materializar o custo de decisões acumuladas sem apresentar números fictícios como reais.",
        "audience": "Gestores que revisam muitas métricas sem prioridade clara.",
        "before": "Todos os dados parecem ter o mesmo peso.",
        "after": "A pessoa reconhece que contexto e decisão definem relevância.",
        "thesis": "Dado só ganha peso quando altera uma decisão.",
        "promise": "Transformar sinais abstratos em forças visíveis.",
        "mechanism": "Elementos gráficos ganham massa declaradamente metafórica e alteram o espaço.",
        "cta": "Escolha a decisão antes da métrica.",
        "modalities": ["presenter", "environment", "generated_scene", "shape", "typography"],
        "visual": (
            "Objetos de dados metafóricos deformam uma superfície; física fantástica é declarada e consistente "
            "após a transformação."
        ),
        "sound_mode": "cinematic_mix",
        "sound_roles": ["location_sound", "impact", "riser", "foley", "silence"],
        "reference": None,
        "metaphor": (
            "objetos que ganham massa",
            "relevância de dados",
            "o peso representa capacidade de alterar uma decisão",
        ),
    },
    {
        "id": "pilot-f4-hybrid-workspace",
        "family": "cinematic_hybrid",
        "title": "Do espaço real ao sistema visual",
        "duration": 30_000,
        "golden": False,
        "objective": (
            "Testar transição entre presenter real e mundo gráfico sem autorizar avatar ou identidade sintética."
        ),
        "audience": "Criadores avaliando formatos híbridos para explicar processos.",
        "before": "Talking head e motion parecem formatos separados.",
        "after": "A pessoa entende que um gesto pode manter contexto ao mudar a linguagem visual.",
        "thesis": "O híbrido funciona quando a transição preserva intenção e posição.",
        "promise": "Levar uma ação real para um sistema gráfico sem trocar a identidade.",
        "mechanism": (
            "Presenter aponta para objeto, objeto vira interface e presenter retorna como footage autorizado em "
            "picture-in-picture."
        ),
        "cta": "Escolha a linguagem que melhor explica cada beat.",
        "modalities": ["presenter", "environment", "generated_scene", "shape", "typography"],
        "visual": (
            "Footage autorizado permanece como fonte; nenhuma face ou voz é gerada; posição e direção do gesto "
            "conectam os mundos."
        ),
        "sound_mode": "cinematic_mix",
        "sound_roles": ["location_sound", "foley", "riser", "interface", "silence"],
        "reference": None,
        "metaphor": (
            "objeto que vira interface",
            "mudança de linguagem audiovisual",
            "a ação real continua como operação no mundo gráfico",
        ),
    },
]


def recipe_for(family: str) -> FormatRecipeV1:
    data = FAMILIES[family]
    accents = {
        "presenter_ugc": "#6C5CE7",
        "split_screen_proof": "#00A8FF",
        "motion_visual_essay": "#4C7DFF",
        "cinematic_hybrid": "#FF7A45",
    }
    return FormatRecipeV1(
        recipe_id=data["recipe_id"],
        family=family,
        name=data["name"],
        canvas_width=1080,
        canvas_height=1920,
        minimum_duration_milliseconds=data["min_ms"],
        maximum_duration_milliseconds=data["max_ms"],
        required_capabilities=data["capabilities"],
        allowed_modalities=data["modalities"],
        layout_rules=data["layout"],
        motion_rules=data["motion"],
        audio_rules=data["audio"],
        design_tokens={
            "backgroundColor": "#0B0D10",
            "foregroundColor": "#F5F7FA",
            "accentColor": accents[family],
            "mutedColor": "#667085",
            "displayFontFamily": "Inter",
            "bodyFontFamily": "Inter",
            "displayFontSize": 88,
            "captionFontSize": 56,
            "safeZoneTop": 180,
            "safeZoneRight": 72,
            "safeZoneBottom": 260,
            "safeZoneLeft": 72,
            "baseSpacing": 8,
            "transitionMilliseconds": 240,
        },
        fallbacks=[
            {
                "fallbackId": f"{data['recipe_id']}-reduced-motion",
                "trigger": "reduced_motion",
                "strategy": (
                    "Substituir deslocamentos amplos por cortes, dissolves curtos e estados "
                    "estáticos equivalentes."
                ),
                "preservesVisualFunctions": ["evidence", "context", "call_to_action"],
            },
            {
                "fallbackId": f"{data['recipe_id']}-rights",
                "trigger": "rights_unverified",
                "strategy": (
                    "Trocar o asset por blocking tipográfico autoral sem alterar tese, timing ou "
                    "evidência declarada."
                ),
                "preservesVisualFunctions": ["evidence", "metaphor", "identity"],
            },
            {
                "fallbackId": f"{data['recipe_id']}-provider",
                "trigger": "provider_unavailable",
                "strategy": (
                    "Projetar o shot para shapes, fonte verificada ou footage existente no "
                    "renderer determinístico."
                ),
                "preservesVisualFunctions": ["demonstration", "continuity", "rhythm"],
            },
        ],
        reduced_motion_rules=[
            "Preservar a mesma ordem, texto, função visual e duração de leitura.",
            "Nenhuma informação pode depender somente de parallax, escala rápida ou trajetória.",
        ],
        fallback_recipe_id=data["fallback"],
    )


def build_case(definition: dict[str, object]) -> CreativeAutonomyCaseV1:
    case_id = str(definition["id"])
    reference = definition["reference"]
    evidence = [
        CreativeEvidenceV1(
            evidence_id=f"{case_id}-brief",
            kind="user_provided",
            summary=str(definition["objective"]),
            allowed_claims=[str(definition["thesis"]), str(definition["promise"])],
            prohibited_claims=[
                "Garantia de resultado comercial",
                "Preço, atributo ou performance não fornecidos",
            ],
            human_review_required=True,
        )
    ]
    structural_urls: list[str] = []
    if reference:
        structural_urls.append(str(reference))
        evidence.append(
            CreativeEvidenceV1(
                evidence_id=f"{case_id}-structure-reference",
                kind="creative_reference",
                summary="Referência usada somente para estudar estrutura e função visual.",
                source_url=str(reference),
                prohibited_claims=["Copiar identidade, assets, copy ou composição frame a frame"],
                human_review_required=True,
            )
        )

    message_id = f"message-{case_id}"
    payoff_id = f"{case_id}-beat-4"
    message = MessageArchitectureV1.model_validate(
        {
            "messageId": message_id,
            "objective": definition["objective"],
            "audience": definition["audience"],
            "awarenessStage": "problem_aware",
            "beliefBefore": definition["before"],
            "beliefAfter": definition["after"],
            "thesis": definition["thesis"],
            "promise": definition["promise"],
            "mechanism": definition["mechanism"],
            "claims": [
                {
                    "claimId": f"{case_id}-claim-1",
                    "text": definition["thesis"],
                    "evidenceIds": [f"{case_id}-brief"],
                    "status": "human_review_required",
                }
            ],
            "hooks": [
                {
                    "hookId": f"{case_id}-hook-a",
                    "text": definition["promise"],
                    "mechanism": "demonstration",
                    "evidenceIds": [f"{case_id}-brief"],
                    "promiseDeliveredByBeatId": payoff_id,
                },
                {
                    "hookId": f"{case_id}-hook-b",
                    "text": definition["before"],
                    "mechanism": "tension",
                    "evidenceIds": [f"{case_id}-brief"],
                    "promiseDeliveredByBeatId": payoff_id,
                },
            ],
            "selectedHookId": f"{case_id}-hook-a",
            "cta": definition["cta"],
            "lockedFacts": [str(definition["objective"]), "Nenhuma publicação está autorizada."],
        }
    )

    total = int(definition["duration"])
    durations = [round(total * 0.14), round(total * 0.2), round(total * 0.24), round(total * 0.24)]
    durations.append(total - sum(durations))
    roles = ["hook", "problem", "demo", "proof", "cta"]
    functions = ["context", "contrast", "demonstration", "evidence", "call_to_action"]
    relations = ["origin", "contrast", "cause", "escalation", "conclusion"]
    messages = [
        str(definition["promise"]),
        str(definition["before"]),
        str(definition["mechanism"]),
        str(definition["thesis"]),
        str(definition["cta"]),
    ]
    modalities = list(definition["modalities"])
    beats = []
    cursor = 0
    for index, duration in enumerate(durations):
        beat_modalities = [modalities[index % len(modalities)]]
        if "typography" in modalities and beat_modalities[0] != "typography":
            beat_modalities.append("typography")
        beats.append(
            {
                "beatId": f"{case_id}-beat-{index}",
                "order": index,
                "narrativeRole": roles[index],
                "purpose": [
                    "Abrir uma expectativa verificável.",
                    "Tornar o problema específico.",
                    "Mostrar o mecanismo em ação.",
                    "Entregar prova ou consequência visual.",
                    "Fechar a promessa e indicar o próximo passo.",
                ][index],
                "message": messages[index],
                "opensExpectation": str(definition["promise"]) if index == 0 else "",
                "closesExpectation": str(definition["promise"]) if index == 4 else "",
                "visualFunction": functions[index],
                "modalities": beat_modalities,
                "relationToPrevious": relations[index],
                "startMilliseconds": cursor,
                "durationMilliseconds": duration,
                "spokenText": "" if definition["sound_mode"] == "natural_foley_only" else messages[index],
                "onScreenText": messages[index] if index in {0, 4} else "",
                "soundIntent": f"{definition['sound_roles'][index]} ligado ao evento do beat.",
                "evidenceIds": [f"{case_id}-brief"],
                "prohibitedClaims": ["Resultado garantido", "Atributo não fornecido"],
                "realityConstraints": [
                    "Preservar personagem, objeto, direção de tela e estado entre entrada e saída.",
                    "Toda quebra de física deve estar declarada como transformação intencional.",
                ],
                "successCriterion": "O beat pode ser descrito em uma frase e sua função visual é reconhecível.",
            }
        )
        cursor += duration

    script = CreativeScriptV1.model_validate(
        {
            "scriptId": f"script-{case_id}",
            "messageId": message.message_id,
            "messageDigestSha256": message_architecture_digest(message),
            "targetDurationMilliseconds": total,
            "beats": beats,
        }
    )
    recipe = recipe_for(str(definition["family"]))
    route_scores = {
        "presenter_ugc": 0.52,
        "split_screen_proof": 0.50,
        "motion_visual_essay": 0.48,
        "cinematic_hybrid": 0.44,
    }
    route_scores[str(definition["family"])] = 0.95
    format_route = FormatRouterV1.model_validate(
        {
            "routeId": f"route-{case_id}",
            "scriptId": script.script_id,
            "scriptDigestSha256": creative_script_digest(script),
            "candidates": [
                {
                    "family": family,
                    "score": score,
                    "rationale": (
                        "Família selecionada por aderência ao mecanismo, modalidades e risco do brief."
                        if family == definition["family"]
                        else "Alternativa válida, porém menos direta para a função visual dominante."
                    ),
                    "blockers": [],
                }
                for family, score in route_scores.items()
            ],
            "selectedFamily": definition["family"],
            "selectedRecipeId": recipe.recipe_id,
            "selectedRecipeDigestSha256": format_recipe_digest(recipe),
            "selectionRationale": (
                f"{definition['family']} maximiza clareza do mecanismo sem exigir identidade ou voz sintética."
            ),
            "humanReviewRequired": True,
        }
    )

    metaphor = definition["metaphor"]
    metaphors = []
    if metaphor:
        metaphors.append(
            {
                "metaphorId": f"{case_id}-metaphor-1",
                "sourceConcept": metaphor[0],
                "targetConcept": metaphor[1],
                "causalRelation": metaphor[2],
                "interpretationRisk": "A metáfora não pode ser apresentada como dado ou mecanismo físico literal.",
                "literalness": "balanced",
                "fallbackDescription": "Usar comparação editorial direta com texto e evidência.",
            }
        )

    shots = []
    for index, beat in enumerate(script.beats):
        shots.append(
            {
                "shotId": f"{case_id}-shot-{index}",
                "order": index,
                "beatId": beat.beat_id,
                "modality": beat.modalities[0],
                "composition": f"{definition['visual']} Foco deste shot: {beat.message}",
                "camera": "Vertical 9:16; eixo e escala motivados pela função do beat.",
                "lighting": "Luz consistente com o ambiente e a transformação declarada.",
                "entryState": (
                    "Receber sujeito, objeto e direção do beat anterior; no hook, estabelecer o estado inicial."
                ),
                "exitState": "Entregar estado legível para o próximo beat e preservar elementos bloqueados.",
                "transition": "Hard cut, cut on action ou transformação semântica; selecionar no animatic.",
                "assetRequirements": ["Asset com direitos verificados antes do render final."],
                "realityConstraints": beat.reality_constraints,
            }
        )

    visual = VisualDirectionV1.model_validate(
        {
            "directionId": f"visual-{case_id}",
            "scriptId": script.script_id,
            "scriptDigestSha256": creative_script_digest(script),
            "family": definition["family"],
            "recipeId": recipe.recipe_id,
            "recipeDigestSha256": format_recipe_digest(recipe),
            "selectionRationale": (
                f"A família {definition['family']} materializa a mensagem usando {definition['mechanism']}"
            ),
            "designPrinciples": [
                "Uma ideia dominante por frame.",
                "Toda camada visual possui função semântica.",
                "Safe zone, legibilidade e continuidade precedem acabamento.",
            ],
            "palette": ["#0B0D10", "#F5F7FA", "#4C7DFF"],
            "typographyDirection": (
                "Sans de alta legibilidade, hierarquia por escala e no máximo duas linhas por caption."
            ),
            "metaphors": metaphors,
            "shots": shots,
        }
    )

    cues = []
    for index, beat in enumerate(script.beats):
        role = definition["sound_roles"][index]
        cues.append(
            {
                "cueId": f"{case_id}-cue-{index}",
                "beatId": beat.beat_id,
                "role": role,
                "startMilliseconds": beat.start_milliseconds,
                "endMilliseconds": beat.start_milliseconds + beat.duration_milliseconds,
                "description": f"{role} planejado para {beat.purpose}",
                "rightsStatus": "not_applicable" if role == "silence" else "required_before_render",
                "eventBinding": beat.sound_intent,
            }
        )
    sound = SoundDesignPlanV1.model_validate(
        {
            "soundPlanId": f"sound-{case_id}",
            "scriptId": script.script_id,
            "scriptDigestSha256": creative_script_digest(script),
            "mode": definition["sound_mode"],
            "voiceInferenceAuthorized": False,
            "musicAuthorized": False,
            "targetLoudnessLufs": -14,
            "cues": cues,
            "mixNotes": [
                "Validar relação causal entre som e evento.",
                "Revisar loudness e inteligibilidade no render final.",
            ],
        }
    )
    placeholder_by_modality = {
        "presenter": "source_thumbnail",
        "product": "source_thumbnail",
        "screen_ui": "wireframe_ui",
        "source_video": "source_thumbnail",
        "archive": "source_thumbnail",
        "typography": "typography_card",
        "shape": "shape_blocking",
        "data": "shape_blocking",
        "environment": "solid_card",
        "generated_scene": "generated_scene_blocking",
        "avatar": "solid_card",
    }
    cues_by_beat = {cue.beat_id: [cue.cue_id] for cue in sound.cues}
    storyboard = ExecutableStoryboardV1.model_validate(
        {
            "storyboardId": f"storyboard-{case_id}",
            "scriptId": script.script_id,
            "scriptDigestSha256": creative_script_digest(script),
            "directionId": visual.direction_id,
            "directionDigestSha256": visual_direction_digest(visual),
            "soundPlanId": sound.sound_plan_id,
            "soundPlanDigestSha256": sound_design_plan_digest(sound),
            "routeId": format_route.route_id,
            "routeDigestSha256": format_router_digest(format_route),
            "targetDurationMilliseconds": total,
            "status": "ready_for_review",
            "shots": [
                {
                    "shotId": shot.shot_id,
                    "order": shot.order,
                    "beatId": shot.beat_id,
                    "visualFunction": script.beats[index].visual_function,
                    "startMilliseconds": script.beats[index].start_milliseconds,
                    "durationMilliseconds": script.beats[index].duration_milliseconds,
                    "placeholderKind": placeholder_by_modality[shot.modality],
                    "frameDescription": shot.composition,
                    "onScreenText": script.beats[index].on_screen_text,
                    "primaryColor": recipe.design_tokens.background_color,
                    "accentColor": recipe.design_tokens.accent_color,
                    "soundCueIds": cues_by_beat[shot.beat_id],
                    "realityConstraints": shot.reality_constraints,
                    "plannedClipIds": [],
                    "assetState": "placeholder",
                    "expensiveGenerationRequired": shot.modality == "generated_scene",
                }
                for index, shot in enumerate(visual.shots)
            ],
            "humanReviewRequired": True,
        }
    )
    animatic = AnimaticPlanV1.model_validate(
        {
            "animaticId": f"animatic-{case_id}",
            "storyboardId": storyboard.storyboard_id,
            "storyboardDigestSha256": executable_storyboard_digest(storyboard),
            "width": 540,
            "height": 960,
            "frameRate": 30,
            "reducedMotion": False,
            "renderTier": "placeholder_only",
            "expensiveProviderCallsAllowed": False,
            "provisionalAudioOnly": True,
            "status": "planned",
            "shots": [
                {
                    "storyboardShotId": shot.shot_id,
                    "startMilliseconds": shot.start_milliseconds,
                    "durationMilliseconds": shot.duration_milliseconds,
                    "visualPlaceholder": True,
                    "soundCueIds": shot.sound_cue_ids,
                    "transitionPreview": "Corte seco ou dissolve curto conforme a relação entre beats.",
                }
                for shot in storyboard.shots
            ],
            "humanReviewRequired": True,
        }
    )

    return CreativeAutonomyCaseV1(
        case_id=case_id,
        title=str(definition["title"]),
        family=definition["family"],
        golden=bool(definition["golden"]),
        structural_reference_urls=structural_urls,
        evidence=evidence,
        message=message,
        script=script,
        recipe=recipe,
        format_route=format_route,
        visual_direction=visual,
        sound_design=sound,
        storyboard=storyboard,
        animatic=animatic,
        learning=LearningRecordV1(
            learning_id=f"learning-{case_id}",
            case_id=case_id,
            status="planned",
            hypotheses=[
                "A estrutura escolhida torna a tese compreensível no animatic.",
                "O payoff fecha a expectativa aberta pelo hook.",
            ],
        ),
        hard_gates=[
            "rights_and_provenance",
            "claims_and_evidence",
            "technical_integrity",
            "reality_and_continuity",
            "safe_zone_and_legibility",
            "human_review",
        ],
        identity_inference_authorized=False,
        publication_authorized=False,
    )


def build_casebook() -> CreativePilotCasebookV1:
    return CreativePilotCasebookV1(
        suite_id="clicko.video-creative-pilot.pt-br.v1",
        cases=[build_case(item) for item in CASES],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the fixed Clicko creative pilot casebook.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/studios/creative/video-creative-pilot-casebook.v1.json"),
    )
    args = parser.parse_args()
    casebook = build_casebook()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(casebook.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "generatedAt": datetime.now(UTC).isoformat(),
                "output": str(args.output),
                "suiteId": casebook.suite_id,
                "cases": len(casebook.cases),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
