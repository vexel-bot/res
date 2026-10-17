"""Official documentation converted to knowledge, never to watched tutorials."""

from ...domain.studios.contextual_editing import EditingTechniqueV1, digest
from ...domain.studios.motion_recipes import RECIPE_CAPABILITIES

BASE = "https://support.alightmotion.com/hc/en-us/articles/"
SPECS = [
    (
        "motion_choreography",
        "Coreografia de movimento",
        "Antecipar, acelerar, acomodar e manter uma pausa legível.",
        BASE + "10536934703889-Animation-Easing-Curves",
        ["curvas por intervalo", "pivô", "pausa"],
        ["Parada sem salto", "Texto e produto nítidos na pausa"],
    ),
    (
        "layer_rig",
        "Hierarquia e grupos",
        "Coordenar movimentos compartilhados e preservar animações locais.",
        BASE + "10536997444369-Layer-Parenting-and-Null-Objects",
        ["grupo", "pai", "pivô"],
        ["Relações espaciais preservadas", "Ausência de salto ao vincular camadas"],
    ),
    (
        "motivated_occlusion",
        "Oclusão motivada",
        "Usar um gesto ou objeto para motivar a passagem entre planos.",
        "https://alightmotion.com/",
        ["máscara", "oclusor", "âncora de continuidade"],
        ["Bordas limpas", "Passagem vinculada ao gesto", "Identidade preservada"],
    ),
    (
        "integrated_type",
        "Tipografia integrada",
        "Vincular entrada e posição do texto à ação e à composição.",
        BASE + "10536791122449-Elements-The-Complete-Guide",
        ["fonte", "texto", "área de leitura"],
        ["Leitura em celular", "Sem sobreposição do detalhe essencial"],
    ),
    (
        "vector_reveal",
        "Revelação vetorial",
        "Conduzir a atenção com traços e continuidade de direção.",
        "https://guide.alightmotion.com/effects/drawing-progress",
        ["caminho vetorial", "ponto de chegada"],
        ["Direção contínua", "Traço aponta para informação relevante"],
    ),
    (
        "velocity_blur",
        "Desfoque de movimento",
        "Associar o rastro à trajetória e à velocidade, com parada nítida.",
        BASE + "10537118778129-Motion-Blur",
        ["trajetória", "curva", "camada gráfica"],
        ["Rastro coerente com o movimento", "Ausência de blur na pausa"],
    ),
    (
        "depth_camera",
        "Câmera com profundidade",
        "Separar planos por distância com paralaxe e foco coerentes.",
        BASE + "10536993608977-Camera-Objects-Guide",
        ["camadas separadas", "câmera", "distâncias"],
        ["Paralaxe consistente", "Produto sem deformação involuntária"],
    ),
    (
        "localized_refraction",
        "Refração localizada",
        "Usar uma distorção limitada para motivar uma passagem visual.",
        "https://guide.alightmotion.com/effects/displacement-map",
        ["mapa", "região delimitada"],
        ["Marca preservada", "Bordas corretas", "Sem distorção da área de leitura"],
    ),
    (
        "action_sound_cut",
        "Montagem e som",
        "Conectar ação observável, motivo do corte e evento sonoro.",
        "https://alightmotion.com/",
        ["ação filmada ou tarefa", "âncora", "áudio autorizado"],
        ["Continuidade entre planos", "Som sincronizado", "Zoom em fotografia não conta como ação"],
    ),
]

# Editorial decisions are explicitly inferences. The linked documentation
# establishes app features, not these recipes' quality or automated execution.
DIRECTION = {
    "motion_choreography": (
        "Objeto precisa chegar a um lugar e acomodar-se antes da leitura",
        "tracks por propriedade; curva cubic-bezier por intervalo; pivot relativo ao objeto",
        "Separar antecipação, aceleração, acomodação e pausa; não animar todos os eixos em todo plano",
        "Salto na parada: igualar valores; oscilação excessiva: reduzir overshoot; texto ilegível: ampliar pausa",
    ),
    "layer_rig": (
        "Produto e assinatura devem conservar relação espacial ao mover o conjunto",
        "parentTargetId de um group; targetIds dos filhos; tracks locais separados dos controles do grupo",
        "Mover o conjunto uma vez, reservar movimento local para função perceptiva diferente",
        "Deriva entre marca e produto: conferir pivôs e pai; transformação duplicada: remover controle redundante",
    ),
    "motivated_occlusion": (
        "Um gesto ou objeto atravessa a região da mudança e justifica a revelação",
        "occluderTargetId; máscara vinculada por checksum; intervalo cobre passagem e estado oculto",
        "Manter direção, escala e registro do objeto; mudar estado somente sob cobertura",
        "Borda exposta: corrigir máscara/registro; estado aparece cedo: deslocar corte para dentro da cobertura",
    ),
    "integrated_type": (
        "Uma palavra deve reforçar o evento relevante sem tapar o sujeito",
        "textUnit word/character; staggerFrames 0..60; readingHoldFrames dentro do intervalo; fontAssetId autorizado",
        "Planejar área livre e hierarquia; entrada breve, pausa legível, saída motivada",
        "Leitura insuficiente: aumentar hold/reduzir palavras; conflito com produto: mover área e ajustar escala",
    ),
    "vector_reveal": (
        "Um traço deve conduzir atenção e chegar a um elemento significativo",
        "tracks stroke_progress 0..1; trajetória vetorial existente; endpoint e direção explícitos",
        "Conectar origem, percurso e destino; conservar continuidade na passagem para o próximo plano",
        "Chegada desconectada: corrigir endpoint; ruído decorativo: eliminar traços sem função",
    ),
    "velocity_blur": (
        "Uma camada gráfica se desloca rápido o bastante para exigir integração temporal",
        "shutterDegrees 0..360; temporalSamples 2..32; tracks da trajetória; parada deve permanecer nítida",
        "Aplicar rastro ligado à velocidade da camada, preservando marca e pausa de leitura",
        "Rastro permanente: revisar velocidade/shutter; smear na marca: reduzir exposição e antecipar parada",
    ),
    "depth_camera": (
        "A composição tem primeiro plano, sujeito e fundo com distâncias coerentes",
        "z por camada; câmera comum; focusDistance e depthOfField positivos e limitados",
        "Adiar até importação e render básico; planejar foco e paralaxe sem deformar produto",
        "Paralaxe contraditória: corrigir distâncias; produto deformado: diminuir perspectiva/movimento",
    ),
    "localized_refraction": (
        "Uma passagem localizada pede distorção sem alterar a identidade do produto",
        "maskAssetId do mapa; displacementRatio 0..0.05; região e intervalo delimitados",
        "Adiar até render básico; isolar área de efeito e preservar bordas, logotipo e texto",
        "Marca distorcida: excluir sua região; borda rompida: corrigir mapa e reduzir deslocamento",
    ),
    "action_sound_cut": (
        "Filmagem ou interface mostra uma tarefa observável e o corte acompanha sua consequência",
        "shotPlan com escala, ação, continuidade e motivo; soundEvents ligados a áudio e alvo existentes",
        "Selecionar entrada/saída pela ação; marcar ataque sonoro visível; FFmpeg aplica áudio uma vez",
        "Colagem de acervo: substituir tomada/coerência; som tardio: corrigir ataque; zoom em foto não é ação filmada",
    ),
}


def alight_technique_cards():
    cards = []
    for identifier, title, purpose, source, prerequisites, checks in SPECS:
        situation, parameters, implementation, corrections = DIRECTION[identifier]
        cards.append(
            EditingTechniqueV1(
                id="alight." + identifier,
                version=1,
                qualification="knowledge_only",
                group="montage" if identifier == "action_sound_cut" else "composition",
                title=title,
                purpose=purpose,
                suitable_when=[situation],
                avoid_when=[
                    "Aplicação decorativa sem motivo",
                    "Ocultar informação essencial",
                    "Material necessário ausente",
                ],
                prerequisites=prerequisites,
                parameters={
                    "recipe": "studio.motion-recipe.v1",
                    "priority": "later" if identifier in {"depth_camera", "localized_refraction"} else "initial",
                    "bounds": "Intervalos, curvas, pivôs e parâmetros são tipados; não aceitar código ou XML livre.",
                    "executableFields": parameters,
                    "direction": implementation,
                    "failureCorrections": corrections,
                },
                required_capabilities=[RECIPE_CAPABILITIES[identifier]],
                required_material_kinds=["font"] if identifier == "integrated_type" else [],
                verification=checks,
                evidence_type="principle",
                sources=[source],
                source_evidence=[{"url": source, "kind": "documentation", "audioVerified": False}],
                engine_qualifications=[
                    {
                        "provider": "alight-motion.contextual-v1",
                        "providerVersion": "unqualified",
                        "status": "knowledge_only",
                    },
                    {
                        "provider": "remotion.contextual-v2",
                        "providerVersion": "4.0.527-native.5",
                        "status": "implemented"
                        if identifier
                        in {
                            "motion_choreography",
                            "layer_rig",
                            "integrated_type",
                            "motivated_occlusion",
                            "vector_reveal",
                            "velocity_blur",
                            "action_sound_cut",
                        }
                        else "knowledge_only",
                    },
                ],
                research_evidence=["Pesquisa documental em fonte oficial; nenhum tutorial acompanhado nesta etapa."],
                inferences=[purpose, implementation, corrections],
                method_limitations=[
                    "Implementação nativa dirigida em avaliação; aprovação visual e autonomia pendentes.",
                    "Receita editorial proposta; suporte específico depende de execução no aplicativo.",
                    "Documentação não comprova qualidade visual, autonomia ou licença dos materiais.",
                ],
                source_digest=digest(
                    {
                        "technique": identifier,
                        "source": source,
                        "checks": checks,
                        "editorialInference": DIRECTION[identifier],
                    }
                ),
            )
        )
    return cards
