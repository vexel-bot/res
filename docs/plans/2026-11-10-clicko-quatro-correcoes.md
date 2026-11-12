# Clicko: quatro correções no fluxo de edição

## Objetivo e situação

O anúncio anterior foi reprovado pelo usuário. Essa decisão continua válida. As causas técnicas e editoriais foram registradas no [diagnóstico da referência](2026-11-10-diagnostico-e-referencia.md). Esta entrega corrige os mecanismos que restringiam o trabalho. Não promove o anúncio anterior e não presume que uma integração corrigida já produz boa publicidade.

O modo **Claude Opus 5.5 · edição por referência**, com **Direção livre** ligada, usa `editorial.openEdit=true` no endpoint normal de tarefas da Clicko. O modo anterior permanece disponível ao desmarcar essa opção, para manter comparações reproduzíveis. Nenhuma credencial nova é cadastrada por esta entrega.

## Correções implementadas

| Problema | Alteração executável | Prova e limite |
|---|---|---|
| Direção limitada a três cenas, paletas e composições fixas | O Opus propõe a composição canônica completa. Pode criar camadas, faixas, captions e keyframes, escolher contagem de cenas, cores, geometria, ordem, tomadas e transições. Cada decisão aponta IDs existentes na proposta. O mesmo validador do editor verifica materiais, itens bloqueados e comandos. | Teste integrado com quatro momentos e cor fora das paletas antigas. O render é real. A resposta do modelo é simulada nesse teste. A correspondência semântica entre intenção e imagem continua sujeita à revisão visual. |
| Referência descrita sem imagem | A pessoa escolhe ou envia até duas referências do workspace. Para vídeo, informa o intervalo e a Clicko extrai seis quadros aproximados, em ordem. A chamada recebe JPEGs reais, cobertura, checksum e intervalo. | Testes com imagem e vídeo. Escopo e intervalo inválidos são recusados antes da inferência. URLs registram procedência; não são baixadas implicitamente. A trilha de referência não é ouvida por esse mecanismo. |
| Briefing de anúncio desconectado de produto e copy | O painel existente de produto, materiais e copy entra na área de produção. O anúncio exige dossiê aprovado antes de reservar API; o contexto fornece produto, público, problema, benefício, oferta, fontes, limites, provas, roteiro e CTA. A proposta precisa manter o CTA. A versão do dossiê e os materiais ficam vinculados à tarefa. | Dossiê ausente bloqueia sem chamada. Uma alteração na copy invalida a avaliação e aplicação antigas. O modo explícito de estudo permite aprender uma técnica sem afirmar que existe um anúncio comercial aprovado. A descoberta continua manual; o modelo não ganha autorização para inventar fatos. |
| Verificação técnica confundida com qualidade editorial | Render técnico, parecer do modelo, avaliação humana e validação com espectadores são estados separados. O parecer visual registra problemas com tempo, dimensão e evidência. O parecer do modelo não aprova o anúncio. A decisão humana aponta o checksum do MP4 e o digest dos comandos. | Aplicação é recusada sem avaliação da prévia; reprovação mantém a proposta sem aplicar. Checksum errado, revisão de projeto antiga ou copy alterada não são aceitos. Os testes simulam as decisões humanas para exercitar o contrato; não são um painel de espectadores. |

## Fluxo prático

1. Abrir um projeto de vídeo na Clicko e preparar/importar os materiais reais do produto.
2. Em Produção, escolher Claude e manter Direção livre ligada. Para anúncio, preencher e aprovar o dossiê existente. Para uma reprodução de técnica, selecionar Estudo de técnica.
3. Enviar ou selecionar a referência visual e delimitar o trecho observado. O arquivo de estudo não é inserido no anúncio automaticamente. Mídia de saída precisa constar entre os materiais autorizados do projeto.
4. Pedir a edição. O Opus recebe os materiais, o dossiê, as fichas compatíveis, os quadros da referência e o contrato do editor. A Clicko valida a composição e renderiza um primeiro corte.
5. O modelo recebe quadros do render e da referência em uma chamada de revisão. Pode devolver uma correção localizada por composição. Uma revisão inválida preserva a primeira proposta válida, com a lacuna registrada. A Clicko renderiza a proposta final e executa a verificação técnica. Não retoca silenciosamente o corte depois desse parecer.
6. Assistir à prévia em reprodução normal e no celular, registrar critérios e observações com tempo. Aprovar ou solicitar ajustes. Aplicar preserva o histórico e exige os vínculos de projeto, materiais, copy, proposta e MP4 vigentes.

## Indicadores e critérios que permanecem anotados

Alinhado ao plano de Alfredo, Bruno e Dener: foco no anúncio e na prova do benefício; repetição e custo ficam registrados por etapa; qualidade não é deduzida de gasto ou de render concluído. Os próximos experimentos devem comparar cortes com os mesmos materiais, copy e áudio quando a pergunta for a contribuição da edição.

| Indicador | Critério de análise | Registro |
|---|---|---|
| Gancho | A abertura mostra uma ação ou promessa específica, ligada ao problema. Reprovar abertura sem mudança reconhecível ou chamada genérica desconectada do produto. | Critério humano `hook`, observação e tempo; achados visuais do modelo separados. |
| Produto e prova | O benefício aparece em uma ação observável. Identidade reconhecível, condições e alegações consistentes com as fontes aprovadas. Imagem decorativa sozinha não prova desempenho. | `product`; dossiê/versionamento e lacunas de mídia. |
| Continuidade | A relação entre estado inicial, ação e estado final sobrevive aos cortes. Inspecionar perda de orientação, saltos, bordas e emendas em movimento. | `continuity`; frames e reprodução, com cobertura declarada. |
| Leitura no celular | Texto e demonstração podem ser lidos durante a exibição em tamanho de consumo, sem cobrir rosto, produto ou ação essencial. Verificação de tamanho/contraste é um filtro técnico. | `legibility`; parecer humano e `preview.status` separados. |
| Fidelidade funcional à referência | A operação estudada aparece executada e ajuda a explicar este produto. Cor parecida ou animação decorativa não comprova a técnica. | `reference`; cobertura da referência e IDs que executam a decisão. |
| CTA | Chamada autorizada, clara e legível, coerente com a oferta; oportunidade real de leitura no fechamento. | `cta`; conteúdo aprovado, checagem de presença e avaliação do vídeo. |
| Tempo | Registrar preparação, direção, primeiro render, revisão do modelo e tempo total até a prévia. Comparar esforço médio e alto no mesmo brief antes de escolher uma configuração. | `stageTimesMs`, `planningTimeMs`. Não misturar tempo de captura de materiais com tempo de inferência. |
| Custo | Somar todas as chamadas, inclusive resposta inválida, revisão e falha. Uma reserva é teto, não gasto. Resultado pendente mantém a incerteza. | `directionUsage`, `measuredCostUsd`, `llmReservationUsd`. Teto compartilhado de US$ 1,50 por proposta. |
| Retrabalho/aprovação | Registrar reprovação, causa, intervalo, menor alteração e nova proposta. Custo por aprovado exige aprovação real, sem contar aprovações simuladas de testes. | Eventos `studio.agent.editorial_reviewed`, notas e critérios. |
| Compreensão | Continua sem conclusão nesta entrega. Teste cego, gabarito e amostra devem existir antes de alegar ganho de compreensão. | `audienceValidation=not_performed`. Nenhuma nota cinematográfica substitui espectadores. |

Para anúncio, os seis critérios precisam ser observados e atendidos antes da aprovação editorial. Para estudo, a aprovação diz respeito a gancho, continuidade, leitura e técnica; não aprova produto ou CTA como peça comercial.

## Prova reproduzível e gasto

`backend/tests/test_production_editing.py` exercita rotas autenticadas, upload, dossiê, reserva compartilhada, transporte Anthropic em memória, composição, render FFmpeg, download por checksum, avaliação e aplicação. A comunicação com modelo usa `httpx.MockTransport`: nenhuma requisição alcança um provedor pago. Valores de uso retornados pelo transporte são dados sintéticos para testar a contabilidade e não devem entrar no livro de gastos reais.

Os arquivos de engenharia ficam em `output/clicko-quatro-correcoes-2026-11-10` na pasta de trabalho da conversa: MP4 local, projeto e recibo `verificacao.json`. São fixtures para verificar o fluxo, não um novo anúncio recomendado.

**Gasto real de API desta entrega: US$ 0.** A melhoria estética do próximo vídeo real permanece sem validação até o render ser visto e avaliado. Permanecem limites do motor atual: 24 camadas locais, 16 faixas, 32 keyframes por item, 30 segundos e limite de resolução/mídia da prévia. Máscara de pessoa e voz exigem materiais/etapas próprios; o modelo precisa registrar a ausência quando não existirem.

### Verificação concluída

- 33 testes passaram no conjunto de direção, montagem anterior, copy, aplicação e novo fluxo. O novo módulo também passou por rechecagem após fortalecer o vínculo entre decisão e intervalo executável. Uma camada invisível ou fora do intervalo não satisfaz a decisão.
- Prova por pixels de faixas intercaladas: a caption aparece de um lado e é ocultada pelo primeiro plano com máscara do outro. A proposta passa pelas rotas de tarefa e pelo render normal, com transporte do modelo em memória.
- Referências de imagem e vídeo foram enviadas ao adaptador como conteúdo visual, com cobertura declarada. Legendas de timeline pequenas demais agora recebem uma falha técnica específica.
- Interface real em localhost: seleção do novo planejador, arquivo de referência e tentativa de anúncio sem dossiê. O servidor respondeu 422 antes da chamada de modelo e a interface mostrou a orientação para completar/aprovar o dossiê. Nenhuma alteração foi aplicada ao projeto usado nessa conferência.
- Verificação TypeScript e validação estática do novo módulo passaram. O localhost foi reiniciado para carregar o fluxo atualizado.
