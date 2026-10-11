# Handoff de implementação a partir do estudo open source

Data: 02/10/2026. Base: [pesquisa e evidências](README.md). Alterar apenas o incremento em execução; preservar as mudanças locais existentes. O estudo não modifica contratos compartilhados nem envia comandos para outro chat.

## Incremento zero — restaurar prova real e diagnóstico

Resultados: 28 testes de domínio aprovados; suíte adicional de render com 3 aprovados e 3 falhas. Dois renders de trim/speed (fonte 24 e 60 fps) falharam; o teste API encontrou `heavy_media_execution_in_progress`. Ler `render-tests.xml`, `diagnostic/worker.log` e `diagnostic/reproduction.json`. Não interpretar o sucesso dos testes de domínio como render aprovado.

Depois de a operação proprietária da lease de mídia concluir, executar novamente as suítes, sem apagar lease de processo ativo. Se a falha `OffthreadVideo` persistir, isolar extração no frame indicado usando a mídia sintética preservada, verificar timestamps/gaps e memória/cache real, comparar frames acessíveis e limites do renderer. A documentação oficial fornece hipóteses, não causa confirmada. Preservar versão/hash e log completos antes de mexer na configuração. Não corrigir trocando silenciosamente de engine ou substituindo vídeo por imagem.

Em `backend/app/providers/studios/remotion_render.py`, estruturar a primeira causa do worker antes de truncar logs: atualmente começo/fim podem omitir o erro central. Manter stdout integral como evidência restrita do job quando adequado, e retornar diagnóstico curto com target/frame/código. Aceite: falha deliberada mantém a causa útil no recibo; teste real 24/60 e teste API passam, MP4/checksum/QC existem e cancelamento não publica. Não mexer no núcleo em paralelo sem verificar as alterações existentes.

## Incremento 1 — tipografia íntegra e medida

Parte implementada: unidades canônicas Unicode 17, whitespace e hold em [TYPOGRAPHY_RECEIPT.md](TYPOGRAPHY_RECEIPT.md); medição posterior de fonte final, wraps/altura/piso e métricas de ink em [TEXT_LAYOUT_RECEIPT.md](TEXT_LAYOUT_RECEIPT.md). Compilador v3/provider native.7, compatibilidade registrada e provas API/job/MP4. O componente nativo `integrated_typography` V1 permanece legado; clipping transformado, kerning/shaping, extremos no celular e leitura humana continuam pendentes. Não confundir métricas de ink com cobertura de pixels ou aprovação estética.

Propósito: manter palavras, marcas combinadas e conteúdo legíveis durante entrada e hold. Referência: medição de linhas no Motion Canvas; reprodução local de segmentação em `runtime-study.json`.

Entradas: `backend/app/services/studios/native_motion_recipes.py`, `workers/remotion-benchmark/src/hybrid.tsx`, projeção em `backend/app/providers/studios/remotion_projection.py`, testes em `backend/tests/test_native_motion_recipes.py` e `backend/tests/test_remotion_native.py`.

Definir uma política comum para palavras/caracteres/grafemas e whitespace. O contrato atual só aceita `word`/`character`; decidir se `character` deve significar grafema precisa de versão de capacidade/compatibilidade. Não adicionar um enum ou renormalizar texto sem registrar migração e leitores. Se a segmentação ocorrer no compilador, persistir o resultado como operação registrada e vinculada ao digest; o runtime não deve manter outra decisão conflitante. Se ocorrer no browser, documentar versão/política e garantir que duração/hold usem a mesma contagem.

Medir depois de carregar a fonte final: retângulos de linhas/spans, altura total, wraps, dimensões de glyph/ink quando aplicáveis e exposição completa após o último elemento chegar. Diferenciar caixa de layout, geometria transformada e pixels efetivamente visíveis. Falha de asset/checksum/fonte deve bloquear com target/correção. Não chamar uma fonte substituta de resultado final.

Aceite: textos `AÇÃO`, `AÇÃO`, emoji composto, palavras longas e multiline; espaçamento e peso animados; hold com início exato; título em grupo com scale/rotation; fonte ausente e checksum incorreto; nenhum corte em tamanho de celular. Salvar fonte/checksum, projeto, digest, manifesto, frames críticos e MP4 de job real. Leitura humana permanece necessária.

## Incremento 2 — curva, pico e diagnóstico da revisão

Parte implementada: comandos/inspeção em `EDITOR_KERNEL_RECEIPT.md`; picos contínuos, intervalo e proteção contra recibos legados em `MOTION_DERIVATIVE_COMPATIBILITY.md`. Permanecem split que preserve a curva, geometria mundial e testes visuais adicionais. A correção dos limites não modifica a interpolação do renderer.

Propósito: graph, inspetor e render representam a mesma interpolação. Referências: Glaxnimate para curva temporal e divisão; Olive para distinguir controles em tempo/valor dos controles normalizados. O estudo numérico não encontrou motivo para substituir `valueAt`.

Entradas: `backend/app/domain/studios/motion.py`, `backend/app/domain/studios/motion_recipes.py`, `native_motion_recipes.py`, `src/studios/VideoStudio.tsx`, `src/studios/useVideoStudio.ts`, runtime e projeção existentes.

Mostrar no frame escolhido: valor authored, intervalo, easing/controles, valor avaliado, unidade e espaço local/global. Não persistir um segundo conjunto de keys no frontend. Extração do estudo deve ser substituída por função compartilhada somente quando houver necessidade real de uso na UI, com compatibilidade de bundle e render.

Pico/velocidade: definir unidade e semântica das constraints existentes. Não apresentar secante de trecho como velocidade máxima da curva. Para Bézier, usar derivada dy/dx com tratamento de extremos/degeneração ou estimador com erro documentado; amostragem por frame sozinha pode perder picos subframe. Migração deve distinguir resultados antigos. Preservar overshoot permitido para propriedades em que faz sentido e bloquear valores inválidos na propriedade final quando necessário.

Aceite: `runtime-study.json` continua passando; contraprova 100 px/1 s com ease-in e limiar 150 distingue média 100 de pico 200; hold muda exatamente na key seguinte; inserir/dividir curva mantém pixels nos frames anteriores/intermediários ou declara alteração; digest muda com parâmetro. Diagnóstico traz método, tolerância e versão, sem promover QC a aprovação visual.

## Incremento 3 — comandos atômicos e inspeção temporal

Propósito: edição automática com histórico, replay e conflito explícito. Referências: operações compostas de Kdenlive e escopo de undo/offsets no Shotcut; espaços temporais no OpenTimelineIO.

Entradas: comandos em `src/studios/videoTimeline.ts`, compatibilidade em `backend/app/services/studios/compatibility.py`, documento/timeline em `contracts.py`, rotas/serviços de edição já existentes e jobs.

Cada comando usa documento e revisão esperada, idempotency key, targets e parâmetros tipados; autor vem da autenticação. Validar todas as alterações e dependências antes de persistir. Undo cria a próxima revisão conforme o contrato e conserva lineage; não sobrescreve uma revisão publicada. Replay devolve o recibo; conflito não aplica metade de um grupo de keys. Não criar um segundo modelo de comandos se o existente puder ser estendido.

Mostrar tempo absoluto da timeline, local da cena e fonte, com taxa numerador/denominador. Usar os vetores de `contract-study.json` para exigir política explícita em 24→60, 60→24 e 24000/1001→30. Marcadores apontam para eventos observáveis e mantêm seu espaço temporal ao fazer trim/speed/ripple. Não inferir áudio sincronizado a partir de frames visuais.

Aceite: operação em dois targets falha inteira se um target/revisão faltar; replay não duplica mudança/job; revisões antigas conflitam; undo após outra edição não apaga trabalho; split/trim/speed respeitam intervalo semiaberto; som finalizado uma vez; cancelamento não publica. Executar testes de contrato antigo e jobs existentes.

## Incremento 4 — parenting, mattes e strokes

Parte implementada: [ASSET_MATTE_RECEIPT.md](ASSET_MATTE_RECEIPT.md) registra o novo `asset_matte` v1, PNG alpha/luminância/inversão em espaço mundial, dependências/bindings explícitos e testes reais entre pais distintos, inclusive borda no pai, contain/cover e pixels intermediários. Compiler v4/library 6/native.8 conservam leitores antigos e tipografia v3. Não qualifica estética nem roto/tracking; stacks sobre a fonte permanecem rejeitados. A fixture antiga de máscara/stroke/parenting/blur também passou na regressão desta versão.

Propósito: consequência visual correta em composição hierárquica. Referências: matrizes local/mundo de Motion Canvas; comprimento/trim de Glaxnimate; dependências explícitas do Natron. Não portar seus engines.

Entradas: `MotionNodeV1`/graph, `native_motion_recipes.py`, projeção/runtime e testes reais de pixels.

Primeiro comprovar os operadores atuais: oclusor retangular irmão, movimento em eixo crescente, parenting explícito, stroke polyline/quadratic. Os targets da fixture `study-motivated-matte` exigem cena real correspondente; validá-la isoladamente não resolve geometria/material.

Para matte arbitrário novo: definir operador/versionamento, geometria e fill rule, coordenadas, transformação e instante de amostragem, combinação/inversão alpha, fonte/checksum quando for asset e limites de custo. Não aceitar CSS/JS ou XML livre. Falta de operador/asset devolve capability pending com target. Representar os dados no contrato existente; registrar migração antes de qualquer extensão.

Aceite: pai desloca filho uma vez; mover/rotacionar/escalar preserva espaço definido; ciclo é rejeitado; alpha amostrado em pontos internos/externos da máscara nos frames intermediários; transparência, bordo e oclusão não alteram identidade; progresso 0/0,5/1 respeita comprimento de caminho. Negativos: matte deslocado e título oculto devem falhar. Bbox DOM sozinho não comprova cobertura.

## Incremento 5 — exposição temporal e prévia mensurável

Parte implementada: [TEMPORAL_EXPOSURE_RECEIPT.md](TEMPORAL_EXPOSURE_RECEIPT.md) registra a política original centrada/truncada, redução no repouso e shutter zero, binding de parâmetros, margem de hold tipográfico e sete jobs reais com MP4/probes. Native.9/library 7 e finalizador 1.3.0 identificam PNG intermediário e qualidade cumprida nos dois encodes. O controle e shutter zero coincidem nos 60 frames RGB; fases de bundle/seleção/render-encode são medidas. Sem p95, aprovação humana ou qualificação ampla de rigs afins/exposição aninhada; compressão standard e pixels individuais de borda conservam seus limites observados.

Propósito: acabamento opt-in com nitidez no hold e custo conhecido. A fixture `study-temporal-exposure` usa apenas a capacidade existente. Cache do Olive inspira estudo posterior, sem alegar implementação.

Entradas: `CameraMotionBlur` no runtime, worker/render e recibos existentes. Comparar variantes com 0/2/8/16 samples; o controle sem blur conserva fonte, materiais, tracks e revisão editorial. Examinar alpha/cor em sobreposição, exposure perto de cuts e frames de repouso. Restringir ao necessário.

Aceite: frames de pausa coincidem com controle nítido; ausência de fantasmas em corte; tempo/bundle/compile/render/finalização, resolução/fps/duração/layers/tracks/samples e tamanho registrados no hardware local. Não publicar p95 com uma amostra. Cache futuro tem quota e eviction; chave deve incluir digest, checksums, versões, frame e configuração. Prévia renderizada identifica engine/versão/digest; storyboard mantém seu limite explícito.

## Incremento 6 — sombra canônica e blur espacial

Implementado e qualificado nas fixtures: [SPATIAL_EFFECTS_RECEIPT.md](SPATIAL_EFFECTS_RECEIPT.md), provider native.12, 171 casos únicos/23 guards/22 vídeos API. Canonical x/y/blur/color/opacity e depth são validados e executados; o backend explícito swangle corrige a divergência temporal observada nos sigmas pequenos. Compiler/library/finalizador e autoria permanecem. Contraprovas native.10/native.11 e diagnóstico GL ficam históricos. A inspeção e sua ligação à revisão agora estão comprovadas no incremento 7 abaixo. Próximo passo concreto: combinação exposição+matte com pai externo animado. Não promover todos os sigmas/stacks nem substituir avaliação humana pelas fixtures.

## Incremento 7 — parâmetros espaciais na inspeção real

[SPATIAL_INSPECTION_RECEIPT.md](SPATIAL_INSPECTION_RECEIPT.md) registra leitura de sombra/depth, blur central calculado pela API e exposição solicitada, sem mudar contratos/runtime. UI normal autenticada, comando existente de keyframe, documento/plano 2→3, rejeição da associação com MP4 anterior, novo render ligado ao checksum. Dois MP4s draft reais/QC passed e 12 probes comprovam o deslocamento e retorno no hold; TypeScript/Ruff e verificador de hashes/evidências passaram. Esses vídeos não aumentam o conjunto high de qualificação Gaussian nem contam como estudos comerciais. A prévia de material central do VideoStudio não foi qualificada como composição; usar o MP4 do inspetor para conferência. Revisão humana/autonomia e limpeza recusada permanecem pendentes.

## Recibo exigido por incremento

Atualização em andamento, posterior ao incremento 7: [TEMPORAL_MATTE_CHECKPOINT.md](TEMPORAL_MATTE_CHECKPOINT.md), candidato native.13. Contexto de tempo efetivo e fundo da inversão foram implementados; a admissão para matte sob pai externo animado foi restaurada como pending após três probes residuais no primeiro frame. Passaram 188 casos de regressão com 22 MP4s admitidos e negativo APNG, mais API422 atual; 12 MP4s experimentais preservam contraprovas. A próxima ação é estudar desenho/acumulação de subframes, inclusive filter opacity versus opacidade do compositor, sem aumentar tolerância ou excluir variantes. Não reconsolidar recibos históricos sobre as fontes atuais.

Atualização de 03/10, posterior ao native.9 acima: [TEMPORAL_RIG_RECEIPT.md](TEMPORAL_RIG_RECEIPT.md), native.10/finalizador 1.4.0, qualifica grupo ou filho exposto com affine/pivô/bordas/opacidade e scopes disjuntos; nested com overlap recebe diagnóstico explícito. São 146 casos únicos e 19 vídeos retidos. A perda de borda foi isolada no encode final e corrigida em high=14, sem aumentar a tolerância. Próxima correção concreta: `editorialShadow` é emitido como x/y/blur/color/opacity, mas o runtime lê outros aliases e ignora opacity. Provar campos canônicos e blur espacial não zero em MP4 real antes de qualificar esses efeitos. Exposição+matte sob pai externo animado, revisão humana e autonomia permanecem pendentes.

Registrar arquivos alterados e seus hashes; contrato/capacidade/versão, significado anterior/novo, leitores, migração e compatibilidade; comando/revisão/autor; projeto/assets e checksums; job/manifest/video checksum; QC técnico; evidência de pixels; revisão humana separada. O novo checksum torna a aprovação anterior obsoleta. Não preencher notas humanas por testes automatizados.

Executar os três estudos do direcionamento em A/B/controle sobre os mesmos materiais. Só depois da qualificação dirigida tentar três briefs novos para avaliar autonomia. Este handoff especifica trabalho; não declara as capacidades aprovadas nem a implementação concluída.
