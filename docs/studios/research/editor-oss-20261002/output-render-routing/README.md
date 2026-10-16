# Encaminhamento da saída para o plano da composição

05/10/2026. O botão `VIDEO-RENDER-PREVIEW` da aba Saída chama `useVideoStudio.render`. Antes, esse método fixava `builtin.ffmpeg-ugc-v1` e não enviava contextualPlanId, inclusive para documentos com plano contextual. O backend exige vinculação de plano para os motores contextuais e executa verificações diferentes no percurso UGC. Isso podia impedir o render ou pedir a execução de outro percurso.

Correção: `src/studios/videoRenderRequest.ts` monta a requisição a partir do documento persistido. Mantém renderer, plano, revisão, versão, canvas e fps contextual; documentos UGC conservam seu percurso. Composições contextuais pedem qualidade `high`; UGC conserva `draft`. Os dois métodos de render do hook usam essa mesma preparação. Bindings inválidos ou planos diferentes falham antes do POST; indisponibilidade de um motor não troca de motor. As validações editoriais e do backend continuam existentes.

O schema TypeScript gerado do cliente ainda possui o union antigo UGC/HyperFrames CLI. O tipo estreito usado nesta preparação inclui apenas os motores contextuais declarados em `CreateVideoRenderJobRequest` no backend atual e contextualPlanId, sem modificar o contrato canônico nem o schema gerado integral. Submissão usa o mesmo apiFetch já empregado no percurso contextual.

Verificação: quatro testes de regressão em `tests/unit/videoRenderRequest.test.ts` passaram, sem skips. Typecheck do projeto via `npm run lint` passou, inclusive depois dos ajustes de reprodução. Esses testes demonstram requisição e guards. A prova real complementar abaixo demonstra API → job → MP4 e reprodução de um estudo existente; não certifica qualidade visual comercial. A primeira execução encontrou erro sintático e depois a incompatibilidade do schema gerado; ambos corrigidos antes dos checks finais.

Os bytes anteriores do hook e SHA estão em before.json/useVideoStudio.before.ts. Não houve alteração de backend, compra de API, envio ao Higgsfield ou promoção de capacidade.

## Prova pela interface real

Workspace de laboratório existente, documento `0ae12fe1-c3aa-4f42-a764-33d076ade8cd`, revisão 2/versão 1, plano `364e858f-4334-4cb7-b384-38ef0207547a`. Intervenções explícitas: selecionar Saída, colocar o botão em vista, clicar uma vez para cada uma das duas solicitações, reproduzir pelo controle real, testar reinício e clicar no link de download. Não houve direção autônoma, novo briefing ou nova cena gerada por serviço externo.

| Pedido pelo botão Saída | Job | Saída |
|---|---|---|
| Primeiro pedido, antes de elevar a qualidade | `2eefc3af-edad-4b2f-afb0-87037f1666cd` | Draft, 307.059 bytes, SHA `3725a7cb8cadf075ec5529ea35e870e070896a09bf38c113e6117a46c766d51b` |
| Pedido posterior em alta qualidade | `bfc6a1c9-afd0-410f-a635-f7654d676f7f` | High, 2.635.718 bytes, SHA `1b856b62acb23b07d488c1c6f9582af75fa5cf074f49c465cdab0a40d6943925` |

Ambos terminaram `succeeded`, uma tentativa, Remotion `4.0.527-native.14`, 1080 × 1920, 30 fps, 15 s/450 frames, H.264/AAC e QC técnico passado. A primeira tentativa de clicar antes de colocar o botão em vista não criou job; depois da rolagem, a submissão real foi observada. Recibos: [primeiro job](job-terminal.json), [job high](high-job-terminal.json), [verificação independente high](high-media-verification.json) e [ffprobe high](high-probe.json). O high levou 120.859 ms no renderer e aproximadamente 133 s entre criação e término do job. São observações individuais deste computador, sem p95 ou promessa de velocidade.

O asset high foi obtido pela API autenticada do laboratório; tamanho e SHA conferem. `ffprobe -count_frames` contou 450 frames e duração de 15 s em vídeo e áudio. Decodificação integral via FFmpeg retornou zero, sem stderr. O SHA high coincide com o MP4 histórico da mesma composição: a correção de encaminhamento e o pedido high reproduziram seus bytes, sem reautorar o estudo.

O QC conserva aviso de silêncio: aproximadamente 82,4%. Loudness −13,06 LUFS, true peak −1,56 dBFS, delta A/V zero. Áudio materializado e reprodução desmutada não equivalem a avaliação humana da escuta.

## Reprodução e download

A prévia central exibiu o SHA correto e os mesmos bytes do job. O observador é passivo: [script](../../../../../scripts/validation/editor-output-render-playback.ps1). O primeiro registro chegou a 15 s em 1×, mas falhou no guard de ausência de busca, porque o controle buscava o frame zero desnecessariamente. Os registros negativos [arm](high-ui-playback-arm.json) e [collect](high-ui-playback-collect.json) permanecem intactos. O controle agora evita essa busca quando já está no frame solicitado e, após `ended`, reinicia no frame zero.

A segunda observação [settled](high-ui-playback-settled-collect.json) passou: fim real em 15 s, 1×, cerca de 15,484 s de relógio, nenhuma busca durante a reprodução, nenhum outro vídeo tocando e nenhum erro de mídia. [Reinício pelo controle](high-ui-replay-after-end.json) começou novamente perto de zero, em vez de reproduzir apenas o último frame. O canvas não adicionava overlays de legenda/marca ao MP4. Isso mede comportamento do player neste estudo, sem certificar apresentação de cada frame no monitor ou estética.

O comando `agent-browser download` 0.27.0 retornou `Download was canceled`, inclusive com caminho curto e nome temporário seguro. O nome original foi restaurado; não alteramos o produto para mascarar a falha. [Fonte upstream examinada](download-cli-source.json) registra canonicalização do caminho e tratamento dos eventos; a causa exata do cancelamento desse comando não foi provada. Uma sessão nova, autenticada no mesmo laboratório, com `--download-path` configurado e clique normal no link original baixou o MP4. Chrome conservou os dados e substituiu `/` por `_` no nome. [Recibo do download](high-ui-download.json) confere 2.635.718 bytes e SHA idêntico ao job; [arquivo baixado](interface-a-output-ui-download.mp4) preservado.

## Escopo e pendências

A interface distingue composição de UGC no título/canvas e não mostra instrução de ingestão ou perfil foley UGC como requisito de uma composição pronta. O cartão de pedido agora distingue a requisição em andamento do último MP4 concluído e oculta o cartão antigo de job nesse intervalo. Essa indicação foi alterada e passou no typecheck; seu estado durante uma nova submissão não foi novamente observado após a mudança. Não realizamos um terceiro render pesado apenas para obter essa captura.

[Auditoria após a correção](api-after.json): as composições/assets/revisões dos nove estudos, nove MP4s históricos e labels das três sessões cegas permanecem iguais; revisões humanas continuam `not_assessed`. O documento ativo retornou exatamente o mesmo JSON antes/depois. [Fontes](sources.json): 73 hashes atuais, 62 fontes qualificadas intactas e quatro backups originais conferidos. Não requalifica automaticamente todos os fluxos da UI ou do backend.

Ainda faltam avaliação estética/escuta, comparação dos geradores por cena aprovada, três novos briefs de autonomia após o aceite dirigido, outras duas linguagens na timeline real e limpeza dos clones recusada pela revisão automática. O carregamento inicial ainda espera catálogos/auditorias junto com o documento; separar essa dependência é o próximo incremento de disponibilidade do editor. O objetivo integral continua aberto.
