# Operações editoriais no res: primeira implementação

**Escopo:** transformar a pesquisa de 45 Reels em decisões rastreáveis no planejamento contextual V2. Esta é uma versão experimental de software, não uma declaração de qualidade visual aprovada. Nenhum frame, áudio, logo ou prompt dos Reels foi incorporado aos materiais de produção.

## Conhecimento e qualificação

As 12 fichas originais permanecem em `INSTAGRAM_EDITING_OPERATION_CARDS_2026-09-30.json` como registro de pesquisa. Uma cópia versionada instalada no backend alimenta o repertório existente por `ensure_repertoire`, deduplicado pelo digest. Cada ficha mantém fontes, critérios de recusa, verificações, limites do método, observações visuais e inferências. O player do Instagram estava mudo; por isso as fichas não trazem prova de mixagem ou sincronismo sonoro.

Quatro técnicas agora têm contrato e implementação inicial: `action_progression`, `motif_continuity`, `gesture_occlusion_reveal` e `moving_variant_mask`. As outras oito continuam `knowledge_only`; se solicitadas como execução no plano V2, criam um impedimento explícito. As quatro primeiras são `implemented`, jamais `render_verified` por mera existência de código ou por um teste com material sintético.

| Operação | Condição executável nesta versão | O que ainda depende de julgamento visual |
|---|---|---|
| Progressão de ação | Pelo menos dois vídeos em intervalos não sobrepostos, ações distintas no plano de tomadas, motivo de corte e materiais verificados. | Se o gesto realmente continua e a consequência é compreensível. |
| Continuidade por motivo | Duas aparições temporalmente distintas com o mesmo `contentIdentity` declarado e âncora nomeada. | Se o motivo é reconhecível sem ler legenda. |
| Revelação sob gesto | Base e variante registradas, mesmo enquadramento/tempo, oclusor acima das duas camadas com máscara fornecida, momento da troca definido. O oclusor percorre o mesmo eixo e progresso da borda revelada. | Se o recorte representa um gesto natural e esconde totalmente a passagem. |
| Máscara móvel entre variantes | Base e variante registradas, janela circular com início, fim, raio e duração tipados. | Halos, alinhamento fino e estabilidade fora da janela. |

## Caminho de execução

O planejador emite `techniqueIds` e `operationBindings` por cena. Cada vínculo contém `version`, `targetIds`, `anchorId`, `cutMotivation`, `newInformation` e tipo de evidência. Para as duas revelações, a cena também fornece um `nativeComponent` registrado. Não há código executável no retorno do planejador. O contrato recusa componente desconhecido, geometria incompatível, troca fora do intervalo e oclusor sem máscara.

Antes de liberar o plano, `evaluate_operation_bindings` confere materiais e direitos, estrutura temporal e vínculo entre operação e componente. O resultado vai para `manifest.operationDecisions` e `editorialEvidence`, com razão, alternativa, hash do vínculo e intervalos das fontes de vídeo. Um bloqueio impede que a semelhança textual do repertório seja confundida com capacidade de renderização.

O compilador persiste os vínculos em `CreativeDocument.composition.narrative.editorialV2.operationBindings` antes do hash de composição. Cada camada indica os IDs das operações que a usam. O manifesto Remotion inclui esses vínculos no digest; a resposta do renderer inclui `nativeCompositionDigest`, operações e amostras de geometria. Alterar tempo ou trajetória da máscara produz outro digest. A versão do compilador passou a `res.scene-compiler.v2.15` e o renderer nativo a `4.0.527-native.3`; planos com o compilador anterior continuam reconhecidos.

O Studio mostra a qualificação das referências, a decisão de elegibilidade, a razão de pendência e os vínculos do plano. O vídeo continua em revisão humana. A revisão exige notas digitadas pelo avaliador, vinculadas ao checksum do MP4, e agora pode registrar a causa principal da correção. Exemplos aceitos ou rejeitados guardam versões e parâmetros dos vínculos; `trainingApplied` permanece falso. Uma avaliação isolada não promove uma técnica automaticamente.

## Verificações executadas

Os testes exercitam a catalogação de 12 fichas, os contratos das duas revelações, direitos ausentes, geometria incompatível, bloqueio de uma ficha de pesquisa, idempotência da recompilação e mudança de hash. Um teste de pixels renderiza uma máscara móvel em Remotion e verifica que a variante aparece somente dentro da região esperada, além de conferir o recibo e a geometria observada. Outro teste renderiza um oclusor mascarado e confirma que ele acompanha a borda de troca, escondendo a passagem. A suíte nativa existente também cobre corte/velocidade com fontes de 24 e 60 fps, checksums e cancelamento.

Um teste parametrizado aplica o mesmo componente a três briefs fictícios — bebida enlatada, mochila urbana e aplicativo de tarefas — com dois ritmos cada. Ele comprova reutilização de contrato e invalidação do resultado quando o ritmo muda. Além disso, `backend/scripts/render_editorial_operations_animatics.py` gera seis animatics locais de quatro segundos, com os mesmos quatro materiais dentro de cada par A/B, um plano executado por variante e recibos de checksum/custo. A diferença A/B altera o ponto de corte e o tempo da máscara. Há também um baseline por brief feito por concatenação simples dos mesmos quatro materiais. Os desenhos são fixtures próprios, com ação interna deliberadamente simples. **Eles não são seis anúncios publicáveis nem prova de qualidade visual comercial.**

O custo de API desta implementação e dos testes locais é **US$ 0**, registrado em `output/editorial-operations-20260930/receipts.json`. A opção nativa continua experimental e desligada por padrão. Não foi feita chamada de geração paga nem integração Higgsfield.

## Aceite que permanece aberto

Ainda faltam material filmado/gerado elegível e identificado para cada um dos três briefs, comparação cega com montagem por concatenação, checagem de áudio em reprodução normal e notas humanas de ao menos 4/5 em clareza, ritmo, continuidade e acabamento. Os seis animatics cobrem a comparação técnica de ritmos, mas não a qualificação estética. Os testes sintéticos provam a mecânica da máscara e a rastreabilidade; não provam naturalidade de gesto, continuidade perceptiva, impacto narrativo, qualidade de som ou autonomia do sistema para selecionar materiais sem assistência. A promoção a `render_verified` depende dessas evidências guardadas por checksum e versão.
