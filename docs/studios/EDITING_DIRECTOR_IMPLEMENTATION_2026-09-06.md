# Direção editorial e recursos sob demanda — res

Data: 6 de setembro de 2026. Escopo: estúdio de edição de vídeo.

## Resultado e limite da entrega

O caminho contextual ganhou pedidos estruturados de materiais, aquisição por fontes cadastradas, resolução de variantes de fontes, importação de SVG estático, composição por cena e um segundo adaptador de vídeo. Os arquivos obtidos entram no catálogo do cliente e passam pela validação do renderizador.

Isso **não certifica edição de qualquer vídeo em qualquer situação**. As capacidades executáveis continuam delimitadas pelo registro do renderizador. Geração por provedores externos, continuidade de personagens/figurino e qualidade editorial em sete gêneros ainda precisam de qualificação com material real. Nenhum candidato gerado recebe aprovação visual automática com base na nota do próprio modelo.

## Alterações implementadas

| Área | Comportamento verificável |
|---|---|
| Intenção e texto | Roteiro e fatos fixos chegam ao planejamento. Texto novo exige uma unidade completa da fonte; propostas não admitidas aparecem para revisão. |
| Transcrição | O planejador recebe o conteúdo e os vínculos da transcrição. Revisão alterada invalida o job antes da chamada ao modelo. |
| Restrições | Beats omitidos pelo modelo, técnicas exigidas, escolhas explícitas de material e decisões de seleção do usuário são preservados. |
| Amostragem visual | Início, meio e fim do intervalo de cada um dos primeiros 24 clipes. O registro informa a cobertura e que não se trata de análise integral do vídeo. |
| Materiais | `materialNeeds` descreve cena, tipo, consulta, finalidade, papel, obrigatoriedade, origem oficial e critérios. Não há lista de marcas ou personagens no código. |
| Aquisição | Consulta ao projeto/acervo, fontes cadastradas com aquisição autorizada e conector Google Fonts. Ausências e ambiguidades aguardam escolha. |
| Fontes | Família/variante consultadas na API, arquivo TTF/OTF obtido, versão fixada e glifos portugueses validados. O mesmo asset pode ser usado na prévia e no FFmpeg. |
| Logos vetoriais | SVG estático validado e rasterizado com transparência. O acervo guarda PNG e checksum do SVG de origem; o SVG original não é armazenado separadamente. |
| Proveniência | Conteúdo igual não substitui uma origem distinta. Reimportações com mesmo conteúdo e metadados reutilizam o asset; origens distintas mantêm registros próprios. |
| Repertório | Treze novas fichas de princípios editoriais reutilizáveis, com finalidade, contraindicações, materiais e parâmetros, somadas à base existente. |
| Composição | `beats[].compositionTechniqueId` permite selecionar um componente registrado por cena. Inserções automáticas respeitam margem quando há espaço no quadro. |
| Provedores | Planejamento, imagem e vídeo têm seleção própria. Gemini permanece padrão; API compatível atende planejamento; Runway atende geração/transformação de vídeo. |
| Jobs | Provedor/modelo/revisão/fontes ficam vinculados. Identificador remoto é persistido para consulta; timeout de submissão sem identificador não provoca reenvio automático. |
| Revisão visual | Todo material gerado permanece candidato até avaliação explícita. A avaliação automática é apenas evidência auxiliar. |

A admissão literal de texto não é um detector geral de verdade: uma sentença pode depender de outra ressalva em outra parte do roteiro. A ordem sugerida pelo modelo fica pendente quando não foi definida pelo usuário. Revisão editorial continua necessária para qualificar o comportamento semântico.

## Interfaces e configuração

Contratos estendidos: `ContextualPlanRequestV1.materialNeeds`, `ContextualEditPlanV1.materialRequests`, `EditingBeatV1.compositionTechniqueId` e `EditingMaterialNeedV1.fontVariant`.

Rotas de fontes do acervo:

- `GET/POST /api/v1/studios/v1/editing/resource-sources?workspace_id=...`
- `POST /api/v1/studios/v1/editing/resource-sources/{id}/acquire?workspace_id=...`

O cadastro registra URL HTTPS exata, condições de uso e `autoAcquire`. A aquisição automática exige essa opção; o cadastro não dá ao modelo permissão para baixar URLs arbitrárias. Resolução de DNS, endereço público, redirecionamentos, tamanho e formato continuam validados pelo downloader existente. A marcação de origem oficial é uma declaração do responsável pelo acervo, não uma autenticação independente de titularidade.

As chaves e opções estão documentadas em `.env.example`. Os padrões continuam desativados. `STUDIO_EDITING_AI_VIDEO_PROVIDER=runway` seleciona o adaptador alternativo; não muda o planejador nem o gerador de imagens. Não há failover silencioso depois de uma submissão paga incerta.

O adaptador Runway usa API `2024-11-06`, `gen4.5` para geração e `aleph2` para transformação. O contrato foi conferido no SDK oficial; disponibilidade na conta e qualidade de saída permanecem pendentes. Este adaptador aceita uma imagem e um vídeo no máximo, com entrada inline limitada a 3,7 MB por arquivo. Arquivos maiores precisam de um adaptador de upload. A imagem de referência em transformação é um keyframe inicial, não uma promessa de transferência precisa de figurino. Geração sem imagem usa quadro vertical ou horizontal; composição quadrada acontece no editor.

Limites são explícitos: SVG com script, recursos externos, texto, filtros e outros elementos fora do subconjunto aceito é rejeitado. Google Fonts depende de uma chave configurada; na ausência dela o plano pede o arquivo. Busca aberta em qualquer site, compras e downloads de pacotes musicais não estão automatizados.

## Consumo e política de produção

GPT permanece restrito a testes locais. Configurações conhecidas de OpenAI/GPT são rejeitadas no caminho de produção. Ao cadastrar um endpoint compatível de terceiros, seu operador ainda precisa garantir a identidade real do modelo; o sistema não consegue inspecionar o roteamento interno desse serviço.

Produção registra uso, tentativas, duração, processamento e armazenamento sem aplicar teto financeiro por vídeo. Reservas conservadoras de teste são isoladas por provedor e não são tarifas reais. Runway está marcado `unpriced`; não há estimativa de cobrança completa nem promoção de modelo implícita.

Na configuração local inspecionada, Gemini e Runway estão desativados e suas credenciais específicas de teste estão ausentes; a chave Google Fonts também está ausente. Nenhuma chamada generativa paga foi realizada nesta entrega.

Existem credenciais gerais no projeto, mas o valor encontrado no alias genérico do Gemini não foi identificado como uma chave Google. Ele não foi transmitido ao Google nem reaproveitado como credencial do estúdio. `model-metadata.json` registra que não houve consulta de modelos nem geração; disponibilidade dos modelos continua não verificada.

## Evidências de validação

Diretório: `artifacts/validation/editing-director-20260906/`.

- `regression.xml`: 83 testes de backend passaram, cobrindo montagem, recursos, planejadores, admissibilidade editorial, Runway e worker.
- `runway.xml`: cinco testes passaram, incluindo rejeição de entrada inválida sem reserva ou submissão paga e aplicação somente após revisão.
- `fonts.xml`: quatro testes passaram; descoberta/download são simulados, mas os bytes da fonte, a conversão SVG e os MP4s são reais.
- `layout.xml`: 36 testes passaram na nova execução do conjunto contextual e de aquisição após o ajuste de margem. O teste de pixels confirma que a forma SVG aparece e respeita a margem superior.
- Três vídeos `materials-320x320`, `materials-360x640` e `materials-640x360`, acompanhados do plano e de um quadro exportado.
- Três testes Playwright passaram: espera por escolha, seleção de material com texto pendente visível e aplicação localizada de transformação revisada. A fronteira de API nesses testes é simulada.
- TypeScript (`tsc --noEmit`), Ruff nos módulos revisados e build Vite passaram. O build ainda informa o aviso de bundle acima de 500 kB; divisão geral do aplicativo está fora deste escopo.

Os vídeos desta rodada usam um fundo sintético e uma forma vetorial simples para testar composição e tipografia. Não representam três anúncios acabados nem certificam qualidade generativa. O atributo `humanReview` permanece pendente: inspeção de quadros pelo agente não equivale a aprovação do cliente.

## Qualificação ainda necessária

Usar os contratos de benchmarking existentes para registrar cada execução, checksum, modelo, custo observado e avaliação humana. A matriz mínima permanece:

| Cenário real | Vertical | Quadrado | Horizontal |
|---|---|---|---|
| Apresentação para câmera | Pendente | Pendente | Pendente |
| Tutorial de tela | Pendente | Pendente | Pendente |
| Entrevista | Pendente | Pendente | Pendente |
| Demonstração de produto | Pendente | Pendente | Pendente |
| Narrativa com arquivo | Pendente | Pendente | Pendente |
| Composição com fotografias | Pendente | Pendente | Pendente |
| Vídeo sem fala | Pendente | Pendente | Pendente |

Para cada célula: selecionar arquivos representativos, comparar objetivos diferentes, verificar texto/ressalvas, legibilidade, continuidade, emendas e áudio; registrar falhas e revisão humana. Comparar Gemini e Runway em tarefas equivalentes apenas após habilitação e credenciais de teste. Não preencher evidências com respostas simuladas.

Tracking, rotoscopia, máscaras temporais, rampas de velocidade, estabilização e composição avançada continuam fora da primeira ampliação executável. Paridade geral HyperFrames/prévia/FFmpeg, detecção integral de eventos e acústica, descoberta aberta de arquivos e planejamento automático de geração em cadeia ainda não estão concluídos. A ausência dessas capacidades deve gerar alternativas, nunca uma promessa de execução universal.

## Fontes técnicas consultadas

- [Google Fonts Developer API](https://developers.google.com/fonts/docs/developer_api).
- [Runway — modelos](https://docs.dev.runwayml.com/guides/models/), [versão da API](https://docs.dev.runwayml.com/api-details/versions/2024-11-06/) e [saídas dos jobs](https://docs.dev.runwayml.com/assets/outputs/).
- [SDK oficial — video-to-video](https://github.com/runwayml/sdk-python/blob/main/src/runwayml/types/video_to_video_create_params.py) e [image-to-video](https://github.com/runwayml/sdk-python/blob/main/src/runwayml/types/image_to_video_create_params.py).
- [resvg-py — API](https://resvg-py.readthedocs.io/en/latest/api.html), versão fixada `0.5.0`; XML defensivo com `defusedxml==0.7.1`.
- Skill [Code Review da Anthropic](https://github.com/anthropics/knowledge-work-plugins/blob/main/engineering/skills/code-review/SKILL.md), instalada em `C:/Users/edugu/.codex/skills/code-review/SKILL.md` e aplicada nesta revisão.

O relatório `EDITING_CODE_REVIEW_2026-09-06.md` e suas falhas de teste foram preservados como histórico. Esta entrega corrige os quatro casos adversariais relatados e substitui aprovação visual por autoconfiança por revisão explícita; a qualificação geral de produto continua pendente.
