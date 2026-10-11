# Editor potente do res — direcionamento para implementação

Data: 02/10/2026. Objetivo: operação automática com projeto inspecionável e execução fiel. After Effects exemplifica capacidades de composição; não é motor escolhido, requisito de instalação nem escopo de clonagem.

## Handoff para o outro chat

> Construir as capacidades do editor e de sua execução sobre os contratos atuais do res. Priorizar operação automática, fidelidade da composição e diagnóstico. Não trocar o motor, criar outro modelo de projeto ou montar uma interface demonstrativa sem ligação ao render real. Entregar cada capacidade com testes e evidência de saída.

Este chat define direção, repertório, estudos e avaliação visual. O outro pode construir o núcleo do editor e a execução. Antes de alterar contrato compartilhado, registrar arquivo, versão, significado, migração, leitores e teste de compatibilidade. Preservar mudanças locais existentes; não assumir um checkout limpo. Repositório local: `C:/Users/edugu/Downloads/res`.

## Arquitetura e fonte de verdade

**Diretor:** transforma briefing/referências em mensagem, ações, continuidade, composição, ritmo e requisitos de materiais. Usa `CinematicArtDirectionV1`, `CinematicShotIntentV1`, conteúdo canônico, assertions e receitas. Nenhum código livre, XML ou comando de dispositivo.

**Editor:** aplica operações tipadas sobre `CreativeDocumentV1`, timeline, camadas, `MotionGraphV1`, tracks/receitas e assets. Representa grupos, parâmetros e intervalos executáveis; valida autoria de propriedades e dependências. Mantém revisão e histórico. Não decide que uma operação técnica foi esteticamente boa.

**Renderer:** recebe snapshot imutável, capacidades/versionamento e assets com checksum; executa operações registradas, devolve vídeo/recibo/evidências. Remotion e FFmpeg permanecem. Falha interrompe o job com diagnóstico; não muda silenciosamente de motor.

Fluxo: edição canônica → validação → persistência → hashes → snapshot → compilação → manifesto → render visual sem som original → finalização FFmpeg → probe/QC → revisão. Timeline, grafo, prévia e exportação representam a mesma revisão. Storyboard/aproximação devem ser identificados como tais.

## Mapa de código existente

| Responsabilidade | Entradas principais |
|---|---|
| Documento/timeline/assets/revisões | `backend/app/domain/studios/contracts.py`, `services/studios/compatibility.py` |
| Direção e plano | `domain/studios/contextual_editing_v2.py`, `cinematic_direction.py` |
| Receitas e repertório | `domain/studios/motion_recipes.py`, `services/studios/editing_repertoire.py` |
| Compilação canônica | `services/studios/scene_compiler.py`, `native_motion_recipes.py` |
| Projeção/runtime | `providers/studios/remotion_projection.py`, `workers/remotion-benchmark/src/hybrid.tsx` |
| Render/job/QC | `providers/studios/remotion_render.py`, `services/studios/video_render.py`, `jobs.py` |
| UI real | `src/studios/VideoStudio.tsx`, `useVideoStudio.ts`, `videoTimeline.ts`, `ContextualEditingPanel.tsx` |
| Revisão humana/programa | `domain/studios/visual_audit.py`, `services/studios/visual_review.py`, `visual_quality_program.py` |

## Matriz de capacidade — auditada, sem alegar qualificação estética

| Capacidade | Estado | Próximo incremento / aceite |
|---|---|---|
| Timeline por frame, trim/speed e som | Existente; testes reais de vídeo em fps diferentes | Markers inspecionáveis e vínculo de eventos; não duplicar áudio |
| Texto, vetor, imagem, vídeo, grupos e ordem | Existente | Inspeção hierárquica ligada ao documento real |
| Curvas, posição/escala/rotação/opacidade/pivôs | Existente; receitas nativas conectadas nesta fase | Graph, manifest e pixels concordam nos frames críticos |
| Parenting e coordenadas locais | Existente, rigor aumentado nas receitas | Filho move uma vez com o pai, sem deriva; ciclos rejeitados |
| Tipografia final medida | Incompleto: carregamento/fontes e shrink existem; leitura humana pendente | Bounds com fonte final, wraps em extremos, palavras inteiras, hold verificável |
| Máscaras e oclusão | Incompleto: assets e oclusão retangular dirigida | Mattes arbitrários exigem operador novo, testes de pixels e recursos declarados |
| Traço/progresso vetorial | Existente para polyline/quadratic | Não anunciar morph de caminhos arbitrários |
| Motion blur temporal de gráficos | Implementado nesta fase, qualificação visual pendente | Exposição amostrada; avaliar cores, transparência, tempo e nitidez em repouso |
| Cor/efeitos | Parcial; efeitos não qualificados rejeitados pelo nativo | Stack registrado e evidência por efeito, sem aceitar JS/CSS livre |
| Scrubbing, seleção e diagnóstico | UI existente, incompleta para inspeção fina | Frame exato, propriedades computadas, revision/hash, diferença preview/export |
| Edição automática/idempotência/jobs | Existente em planos e renders | Comandos granulares esperam revisão/autoria; cancelamento/retomada comprovados |
| 3D, tracking, roto, refração | Ausente ou conhecimento/contrato sem execução qualificada | Etapas posteriores com fixtures reais e limitações próprias |

“Existente” não significa `render_verified` comercial. “Implementado” não significa aprovado humano. Conferir o relatório desta rodada antes de promover capacidades.

## Contratos de operação

Estender operações de edição existentes; caso uma operação granular nova seja necessária, definí-la como união discriminada e versionada, sem criar outro formato de projeto. Campos obrigatórios: ID/idempotency key, documento, revisão esperada, autor autenticado, ação/targets/parâmetros tipados. Resposta: revisão resultante, digest, alterações aplicadas, avisos e pendências. Replay do mesmo comando retorna o mesmo recibo; outra revisão conflita. Autor não é fornecido livremente pelo planejador.

Exemplo real de receita dentro de `ContextualPlanRequestV2.scenes[].motionRecipes`:

```json
{
  "id": "organize-title", "version": 1, "technique": "motion_choreography",
  "targetIds": ["title"], "startFrame": 0, "endFrameExclusive": 450,
  "intent": "O título acomoda e permanece para leitura", "continuityAnchor": "Mesmo texto e fonte",
  "parameters": {"pivot": [0, 0.5], "tracks": [{
    "targetId": "title", "property": "y", "keyframes": [
      {"frame": 0, "value": 30, "curve": [0.22, 0.75, 0.25, 1]},
      {"frame": 24, "value": 0}, {"frame": 449, "value": 0}
    ]}]}, "verification": ["Sem salto ao acomodar; texto inteiro permanece legível"]
}
```

Saída na composição canônica: node com pivot, MotionTrack `position_y` em frames absolutos, parâmetros/versionamento em `narrative.editorialV2.nativeRecipeOperations`, digest antes de snapshot. Projeção produz `position.y`, runtime aplica uma única translação. Recibo conserva checksum do manifesto/vídeo; geometria DOM observada não comprova cobertura da máscara. Não criar listas paralelas de keyframes no frontend como fonte de verdade.

Capacidade ausente retorna `motion_recipe_capability_pending:<técnica>` ou diagnóstico equivalente, indicando target e correção executável. Profundidade não vira zoom, blur temporal não vira filtro estático, material ausente não vira ícone.

## Interface de inspeção

Primeiro incremento: carregar documento/revisão reais; selecionar scene/layer; scrubbing por frame; mostrar propriedade authored e avaliada; targets/parents; intervalos; fonte/checksum; pendências; render associado e comparação. Controles aplicam comandos e exibem conflito de revisão. Nunca exportar um mock independente. Prévia renderizada mostra motor/versão/digest; storyboard mostra limite claramente.

Quadro de qualidade sempre separado: QC técnico, estado visual (não avaliado/correção/reprovado/aprovado) e autonomia. Novo checksum torna revisão anterior obsoleta. Não preencher notas por QC ou análise automática. Achados exigem cena, intervalo, causa, observação e mudança executável. Um comentário sem alteração não produz job.

## Desempenho e instrumentação

Medir em hardware local: resolução/fps/duração, número de layers/tracks, samples de blur, tempo de compile/bundle/render/finalização, CPU/memória quando disponíveis, tamanho de artefatos e percentis após amostra suficiente. O worker já retorna duração de render. Um único vídeo não mede p95. Registrar limites observados no relatório; metas iniciais são objetivos, não resultados: scrubbing interativo em resolução de prévia e render de 15 s sem exceder timeout configurado. Não prometer realtime 1080p sem medição.

## Testes exigidos

Contratos/compatibilidade antigos; fonte ausente/checksum divergente; Unicode com acentos; trim e speed em 24/60 fps; preservação da proporção; easing/hold/pivot; parenting/ciclo/dupla transformação; máscara nos frames intermediários; stroke progress; exposição temporal e ausência de blur na pausa; som sincronizado; digest muda ao alterar parâmetro; cancelamento não publica; revisão antiga não aprova render novo.

Negativos semânticos: identidade/texto trocado sob o mesmo ID, título oculto, transformação invertida, matte desalinhado, deslocamento sem consequência. Software pode rejeitar contradição estrutural; humanos precisam verificar entendimento. Não “aprovar” negativos só porque pixels mudam.

Prova real por capacidade: projeto canônico e assets autorizados → API → job → MP4 → receipt/QC → observação visual. Mocks testam falhas, não demonstram qualidade. Critério dirigido: quatro eixos humanos ≥4/5 e preferência cega frente ao controle nos três estudos. Autonomia exige três novos briefs e intervenções zero ou explícitas, avaliada depois.

## Incrementos pequenos e independentes

1. Matriz e diagnóstico do percurso, compatibilidade e versões.
2. Comandos/curvas/pivôs e parenting, sem expandir superfície manual.
3. Tipografia/medição/holds com fonte final.
4. Mattes/oclusão/strokes com pixels intermediários.
5. Acabamento temporal opt-in e benchmarks.
6. Inspeção real, comparação e revisão humana.
7. Generalização do planejador sobre capacidades aprovadas.

Recurso avançado só entra com propósito, capacidade versionada e custo de execução conhecido. Não instalar Adobe, não comprar API e não retomar Alight. Evitar refatoração global ou outro modelo canônico como atalho.
