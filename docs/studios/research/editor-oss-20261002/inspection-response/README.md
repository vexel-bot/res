# Inspeção com resumo de avaliação — 05/10/2026

O painel do editor original em Downloads agora pede `evaluationDetail=summary`. A resposta real caiu de aproximadamente 7,2 MB para 42 KB, sem mudar documento, revisão, grafo, tracks/valores, cenas, receitas, materiais, hashes, histórico ou renderer. A versão completa continua sendo o padrão da API e conserva os mesmos hashes da investigação anterior nos três frames. A mudança é uma projeção de leitura: nenhum evento ou evidência de QC foi apagado/regravado.

## Diagnóstico e contrato

[payload-sizes.json](payload-sizes.json) localizou 7.160.359 bytes na avaliação do plano de Interface A, incluindo 7.039.551 bytes no eixo técnico; documento e manifesto são pequenos. A hipótese inicial de documento/manifesto grande foi substituída por essa medida. O painel não consumia o campo de avaliação detalhada, mas o recebia a cada frame.

[COMPATIBILITY.md](COMPATIBILITY.md) foi salvo antes da mudança. A API mantém `studio.editor-inspection.v1` e o payload integral para chamadas antigas/default ou `evaluationDetail=full`. O opt-in `summary` devolve `studio.editor-inspection.v2`, com `EditorEvaluationSummaryV1`: cada estado vem exclusivamente do próprio eixo; status ausente, booleano ou outro formato sem string explícita retorna null. QC não preenche estado humano. O caminho da avaliação integral indica o mesmo documento/frame e exige a mesma autenticação. Não há migração de projeto/plano/recibo ou novo motor.

Foram alterados apenas o contrato aditivo de resumo, a função/resposta de inspeção, o parâmetro de leitura da rota e uma URL no painel. `_bound_plan`, `get_plan`, edição, revisão, idempotência, histórico e avaliação de curvas permanecem preservados. O verificador compara AST de seis funções anteriores do serviço e hashes das outras fontes.

## Respostas reais

[http-parity.json](http-parity.json) registra seis chamadas autenticadas diretas, alternando full/summary, sem nova geração. A igualdade exata de todos os outros campos foi verificada em cada par, e os hashes canônicos full coincidem com o perfil anterior.

| Frame | Bytes full | Bytes summary | Full HTTP | Summary HTTP |
| --- | ---: | ---: | ---: | ---: |
| 0 | 7.201.865 | 41.758 | 6.008 ms | 3.266 ms |
| 244 | 7.201.895 | 41.790 | 2.675 ms | 762 ms |
| 449 | 7.201.869 | 41.764 | 2.684 ms | 920 ms |

Redução de volume de aproximadamente 99,4% demonstrada nessas respostas. Os tempos são três pares na ordem full→summary, com aquecimento/cache do SO e atividade concorrente, incluindo testes no começo da observação. Não são uma experiência randomizada, p95 ou percentual garantido de aceleração. O status humano real continua `pending`; as evidências integrais mantêm os hashes originais.

## Interface real e preservação

Na sessão própria existente, a primeira observação de 20 s ainda estava carregando; [summary-ui-initial.json](summary-ui-initial.json) conserva o negativo. A reobservação da mesma página mostrou cinco cards e MP4 decodificado; não houve reinício por timeout. O único reinício da API ocorreu após os testes para ativar as fontes: processo 9520 encerrado, processo 27188 confirmado pronto.

A seleção da linha `title` abriu a inspeção resumida e conservou o target `ed2-895c9ff7a0a9ce1cb92ec080`. Nos frames 0/244/449, foram conferidos texto do frame calculado, input, seleção, HTTP 200 com query summary e vídeo pausado sem seek pendente a 0/8,133333/14,966666 s, dentro de meio frame. Os recibos são [summary-ui-open.json](summary-ui-open.json), [summary-ui-frame244.json](summary-ui-frame244.json) e [summary-ui-frame449.json](summary-ui-frame449.json); [captura do frame 449](summary-ui-frame449.png) inspecionada visualmente.

As respostas de inspeção no navegador duraram aproximadamente 3.746/5.152/785 ms, respectivamente. O painel funciona com a resposta menor, mas a primeira abertura e a inspeção de todos os frames ainda não são interativas em tempo real. Não atribuir causalmente diferenças frente aos 20 s anteriores somente a esta mudança. `get_plan` continua decodificando/validando o histórico a cada inspeção e é a próxima frente de desempenho, sem enfraquecer a validação. Não foram testados playback contínuo sob mudança rápida de frames nem concorrência entre respostas e comandos nesta rodada.

## Validação

Passaram nove casos novos: estados explícitos/independentes/desconhecidos, compatibilidade full/default, paridade de todos os outros campos nos frames 0/4/14, opção/frame inválidos, autenticação/workspace, conflito de vínculo e comando seguido de inspeção na revisão correta. Passaram seis casos de consulta/histórico anteriores e duas regressões de comando/replay/undo e atomicidade da falha: 17 casos no total. TypeScript passou. Ruff passou após corrigir quebras de linha e seguir a convenção existente de imports de fixtures; o resultado negativo inicial foi registrado. As alterações posteriores aos nove casos foram formatação e uma atribuição equivalente no teste, sem mudança de comportamento; as oito regressões seguintes usaram o serviço final.

Os backups conservam quatro arquivos sujos completos. Uma tentativa inicial colidiu os dois basenames `editor_commands.py` e parou antes de alterar fontes; o backup parcial foi retido, depois os quatro backups foram identificados pelos caminhos completos. Nenhuma alteração externa foi sobrescrita.

[preservation.json](preservation.json) confere pela API nove composições/assets iguais aos snapshots, revisão 2/version 1 e os nove MP4s originais por hash. As três comparações cegas continuam `not_assessed`, review null e labels intactos. [sources.json](sources.json) fixa 91 fontes: 83 das 85 anteriores intactas, duas mudanças esperadas e seis fontes adicionais. [verification.json](verification.json) sela a evidência.

Sem novo render nem chamada paga. Qualificação estética/humana e três briefs autônomos permanecem pendentes. A limpeza antiga recusada pela revisão automática continua pendente; nenhum método equivalente foi tentado nesta rodada.
