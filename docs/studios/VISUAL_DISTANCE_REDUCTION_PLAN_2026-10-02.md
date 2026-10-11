# Redução da distância visual — 02/10/2026

## Direção confirmada

Construir decisões editoriais executáveis e verificar seu efeito em vídeos completos. Prioridade: motion e demonstração real de interface. Remotion compõe; FFmpeg finaliza e mistura áudio uma única vez. After Effects é referência de capacidades do futuro editor, sem integração Adobe ou troca para Alight nesta fase. Limite de APIs: o saldo do teto compartilhado de US$ 10 existente, incluindo tentativas; esta implementação local não autoriza outro orçamento.

Qualidade dirigida antecede autonomia. Intervenção editorial explícita é permitida na primeira etapa e impede declarar direção autônoma. Código, testes e render bem-sucedido não aprovam estética.

## Diagnóstico com evidência

| Observação | Causa provável / decisão | Evidência e limite |
|---|---|---|
| Pilotos com tomadas de mundos diferentes e produto estático ao final | Aquisição precisa atender continuidade e função narrativa previamente definidas | Pesquisa Aurora em `research/AURORA_REFERENCE_GAP_AND_RESEARCH_DECISIONS_2026-09-30.md`; não é medida de qualidade de novos vídeos |
| Seis animatics sintéticos de quatro segundos sem áudio | Baseline de engenharia visualmente reprovado; não usar como referência aprovada | Baseline JSON em `benchmarks/studios/video/visual-quality-baseline-2026-09-30.v1.json` |
| Estudo “Dê forma à ideia” funcionou pela API | Há infraestrutura; faltam direção canônica completa e revisão humana | `research/STUDIO_MOTION_SYSTEM_TEST_2026-10-01.md`; direção manual, sem comprovação de autonomia |
| Receitas persistidas eram rejeitadas em bloco antes do Remotion | Lacuna de tradução real entre contrato e runtime | `remotion_projection.py`, anterior `motion_recipe_engine_not_qualified` |
| Revisão de materiais exigia duas fontes filmadas e embalagem | Regra válida para produto, inadequada a motion/interface | `visual_quality_program.material_readiness`; separar linguagem por metadado explícito |

As referências de Instagram foram observadas com amostragem e áudio silenciado. Não registrar como tutorial integral assistido, nem inferir sincronismo sonoro. Fontes, intervalos e classificação de evidência continuam no repertório existente; nenhuma base paralela foi criada. A aplicação abaixo é inferência editorial original a partir de mecanismos abstratos, não reprodução de autoria ou estilo pessoal.

## Mecanismos aprendidos e aplicações

| Mecanismo | Operação executável | Aplicação / contraprova |
|---|---|---|
| Objeto persistente conduz a atenção | IDs e conteúdo canônico mantidos durante mudança de posição | Organização: três itens legíveis chegam à estrutura; troca de texto sob o mesmo ID invalida continuidade |
| Preparação, transformação, consequência | Intervalos de expectativa, movimento, acomodação e leitura | Comparação: o mesmo conjunto muda de relação; simples deslocamento sem diferença explicável falha |
| Passagem ligada ao gesto | Oclusor gráfico e matte seguem a mesma trajetória | Máscara deve revelar o estado correto atrás da passagem; borda solta falha |
| Hierarquia e pausa | Parenting, movimentos locais e palavra inteira | Texto chega, acomoda e permanece; caracteres cortados ou título escondido falham |
| Ação produz resposta | Captura real de tarefa com dados fictícios | Interface: alteração → confirmação → resultado; cursor decorativo não demonstra tarefa |

Lentes públicas empregadas pela skill `cinematic-mind-council`: clareza espacial/atenção e tradução visual/escala. Traduções operacionais aqui são inferências. Risco: coreografia excessiva pode esconder informação; cada recurso precisa de papel narrativo verificável.

## Contrato dos novos estudos

`ContextualPlanRequestV2.visualStudyLanguage` explicita `motion_graphics` ou `interface_capture`. Exige direção de arte, conteúdo canônico, plano de ações e afirmações semânticas em todas as cenas; 450 frames a 30 fps. Interface exige vídeo vinculado. Documentos antigos omitem esse campo e mantêm as validações antigas.

Cada estudo deve definir promessa, mundo visual, motivo recorrente, estado inicial, evento, estado final, atenção, relação entre camadas, motivo e consequência das passagens, entrada, movimento, acomodação, leitura, saída e papel do som. Cada afirmação declara objeto, intervalo e evidência; sua contraprova acompanha o plano de revisão. Pixels diferentes não provam compreensão.

## Execução e auditoria

Percurso obrigatório: direção tipada → `scene_compiler` → documento/graph persistidos → digest → projeção Remotion → manifesto e assets verificados → runtime → MP4 → probe/QC → revisão.

O compilador de receitas nativas traduz dados para operações registradas, conserva IDs, versões e frames absolutos antes dos hashes. Rejeita disputa de autoria sobre a mesma propriedade, target ausente, recursos de profundidade/refração e espaços de coordenadas ambíguos. Interpolação ocorre em keyframes do graph; o runtime não executa código entregue pelo planejador.

| Recurso | Escopo inicial | Limite explícito |
|---|---|---|
| Coreografia | Tracks, curvas por intervalo, pivôs, antecipação/acomodação via keyframes e holds por valores iguais | Z/câmera 3D pendentes |
| Hierarquia | Parent grupo explícito, coordenadas locais, movimento de filho independente | Receita não converte automaticamente coordenadas globais |
| Tipografia | Palavras completas ou caracteres, stagger, entrada, hold; medição da fonte carregada para shrink | Compreensão e wraps extremos exigem inspeção |
| Oclusão | Matte ligado a oclusor retangular irmão, translação num eixo crescente | Formas/rotação/escala arbitrárias permanecem pendentes |
| Traço | Caminho vetorial existente e progresso animado | Não é morph arbitrário de vetores |
| Desfoque temporal | Amostras de exposição para gráficos; ângulo e número explícitos | Não usa blur estático como substituto; composição das amostras pode alterar cor/opacidade e precisa de revisão |

Documentação oficial consultada: [Remotion motion blur](https://www.remotion.dev/docs/motion-blur/camera-motion-blur). É documentação, não tutorial acompanhado. O recurso deve ser restrito aos gráficos necessários e ficar nítido na pausa. Geometria DOM de amostras não mede cobertura de pixels nem prova a máscara; recibos declaram esse limite.

## Estudos e montagens

1. **Organização:** itens “Ideia”, “Plano”, “Resultado” dispersos chegam a uma estrutura, mantendo texto/identidade. Ancorar um motivo verde e manter leitura final. A prioriza acomodação; B prioriza ritmo escalonado; controle apresenta os mesmos estados sem coreografia dirigida.
2. **Tarefa real:** captura do res em ambiente de teste, conteúdo fictício, editando uma informação e mostrando consequência. A corta para o resultado em 9,5 s; B antecipa esse corte para 9,2 s e muda o enquadramento, preservando a ordem temporal da ação; controle é sequência simples dos mesmos trechos. Captura ausente fica pendente, sem falsa interface animada.
3. **Comparação:** mesmo conjunto passa de disperso para relacionado, com máscara motivada e vetor originando conexão. A transforma continuamente; B usa pausa inicial mais longa e revelação mais rápida; controle alterna estados.

Saída de todos: 15 s, 1080×1920, 30 fps. Textos/vetores próprios; fonte vinculada com licença e checksum. Três variantes por estudo; mesmas fontes e manifesto de materiais. Som deve pontuar o evento, não compensar ausência de ação. Animação de fotografia não conta como filmagem.

## Correções executáveis e revisão

Achado: cena, intervalo, causa (`material`, `direction`, `translation`, `render`), observação, mudança tipada, revisão anterior/nova, hash anterior/novo e autor. Mapear ao recibo de revisão existente sem apagar causas antigas. Sem mudança em plano/material/mixagem não criar outro render.

Revisão humana: vídeo inteiro em velocidade normal, tamanho de celular, abertura, cortes, estados intermediários, fechamento, identidade, sincronismo e leitura. Seleção cega randomizada dos A/B/controle; congelar revisão, checksum e materiais. Nenhuma nota humana é pré-preenchida ou inventada. Achados automáticos são triagem.

Aceite dirigido: QC aprovado, transformações compreensíveis, quatro notas humanas ≥4/5 (clareza, ritmo, continuidade, acabamento), preferência por versão dirigida, diferenças frente à referência registradas, intervenções identificadas. Aceite autônomo posterior: três briefs novos, mesmos operadores/código, mudanças de texto/material parametrizadas pelo planejador, sem correções ocultas, revisão humana novamente. Estados separados no Studio: técnico, visual e autonomia.

## Sequência e entregas

Documentos/matriz → baseline e direção → capacidade por capacidade com testes negativos → estudos A/B/controle → API/Studio → revisão/correção humana → transferência/autonomia. Ficam pendentes etapas sem evidência, mesmo com infraestrutura pronta.

Entregar planos executados, composição, manifests, MP4s, controles, fontes e checksums, recibos de custo/tempo, achados e formulário de avaliação vazio. Relatório de execução em `research/VISUAL_DISTANCE_IMPLEMENTATION_2026-10-02.md` registra o que de fato foi executado nesta rodada.
