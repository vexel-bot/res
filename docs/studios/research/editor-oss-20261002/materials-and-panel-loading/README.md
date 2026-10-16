# Materiais corretos e consultas iniciadas quando necessárias

05/10/2026. O editor mostrava os assets tipográficos e de áudio como “Take”, com “Prévia pendente”, e tentava representar qualquer URL por um elemento de vídeo. O painel de direção também consultava seus catálogos e capacidades enquanto estava oculto, inclusive uma verificação pesada do difusor local. A correção atua nos dois componentes existentes; preserva CreativeDocument, revisões, planejamento e Remotion/FFmpeg.

`VideoStudio.tsx` classifica o card pelo MIME canônico: vídeo, imagem, áudio, fonte tipográfica ou arquivo. Usa o nome original quando disponível; o fallback informa o tipo. Miniaturas de vídeo são reservadas a vídeos, imagens usam imagem quando uma prévia já está disponível e fontes/áudio têm identificação do tipo. Não foi criado um carregador de áudio ou fontes para esses cards. Direitos continuam vindo do asset, sem nova aprovação. Os cinco assets reais da interface foram observados: uma fonte WOFF2, um áudio WAV e três MP4s; os três MP4s conservaram suas miniaturas. O ramo de imagens e tipos genéricos não recebeu qualificação de mídia real nesta rodada.

O painel de direção é montado na primeira abertura de Revisão e continua montado ao alternar abas no mesmo escopo, preservando o rascunho. O gate de revisão editorial continua montado separadamente. Isso adia consultas, sem afirmar cancelamento das que já começaram ou persistência de formulário após revisão/rota/recarga. O carregamento do aplicativo e outros painéis continuam existindo.

`ContextualEditingPanel.tsx` consulta `/scene-generation-capability` pelo botão Verificar gerador local. Enquanto consulta, mostra o estado e impede nova consulta concorrente; erro oferece nova tentativa. A resposta informa capacidades reais e não seleciona automaticamente a geração local. O contrato HTTP e as verificações do backend não foram alterados. A inclusão do trecho experimental continua exigindo seleção explícita e os gates existentes.

## Evidência real e limites

[Verificador](../../../../../scripts/validation/editor-materials-panel-verify.py), [observador passivo](../../../../../scripts/validation/editor-materials-panel-observe.py), [80 fontes atuais](sources.json) e [comandos de validação](validation-commands.json). Typecheck passou depois das duas alterações. Oito regressões existentes de carregamento/encaminhamento do render passaram depois da mudança em VideoStudio; os helpers testados permaneceram iguais na mudança posterior de consulta opcional. Esses testes não cobrem a aparência dos cards; a prova desse comportamento vem do DOM e das capturas reais.

| Situação | Evidência |
|---|---|
| Abertura da interface com fonte, áudio e três vídeos | [Registro](probe-final-initial-settled.json): tipos/IDs corretos, vídeos com miniaturas; direção ausente; zero consultas de capacidade local, repertório e plano latest |
| Primeira abertura de Revisão | [Registro](probe-final-open.json): painel e inspetor disponíveis, gate editorial preservado; zero consultas de capacidade local |
| Clique para verificar, com falha provocada localmente | [Registro](probe-failed.json): status 0, aviso específico, opção desmarcada; MP4 continua decodificado |
| Nova tentativa após remover a interceptação | [Durante](probe-retrying.json) e [resposta real](probe-recovered.json): botão ocupado e depois HTTP 200; serviço indisponível/recursos bloqueados reportados, sem seleção automática |
| Rascunho e alternância de abas | [Aberto](final-draft-open.json), [oculto](final-draft-hidden.json) e [reaberto](final-draft-reopened.json): mesmo rascunho, sem envio de comando editorial |
| Instância final sem rascunho | [Registro](final-clean-settled.json) e [captura examinada](final-interface-settled.png) |

A interceptação foi aplicada somente ao GET local de capacidades e removida antes da nova tentativa. A falha provocada não é atribuída ao servidor. A recuperação consultou o serviço existente; não executou geração. Não houve compra de API, download de modelos, criação de render ou modificação de projeto. O backend continua sem mudanças desta rodada.

[Auditoria autenticada atual](api-preservation.json): nove composições/assets iguais aos snapshots de render originais, nove SHA dos MP4s históricos preservados, revisão 2/versão 1; respostas integrais dos documentos de interface e comparação também preservadas. As três comparações humanas permanecem `not_assessed`, sem review nem mudança dos rótulos. As provas históricas não foram promovidas a aprovação estética.

## Latência investigada, ainda não resolvida

O código de `local_diffusion.capability()` pode executar preflight para cada um dos três perfis quando não recebe capacidades do worker. Cada preflight roda um subprocesso com verificação de ambiente; a consulta anterior de capacidades levou 38.533,5 ms nesta observação. A API de inspeção valida documento/plano, calcula tracks e lê histórico; seu tempo não foi atribuído automaticamente a esse preflight.

[Tempos detalhados anteriores à última mudança](interface-resource-timing.json): uma consulta de catálogo ficou 14.836,7 ms antes do request; outra gastou 14.814,6 ms entre request e início da resposta. A primeira inspeção ficou aproximadamente 1.066 ms antes do request e 13.513,5 ms até a resposta. Após adiar o preflight, a inspeção ainda levou 12.651,1 ms em outra abertura; a verificação local solicitada pelo botão levou 24.949,8 ms. São poucas observações, com cache/carga diferentes, sem comparação controlada ou p95. Elas comprovam trabalho pesado e espera em caminhos distintos, não uma redução causal nem um tempo de inspeção aceitável.

A amostra [de memória](host-memory.json) registra pouca RAM livre em uma máquina de aproximadamente 8 GB. Não comprova a causa de uma consulta anterior. Os próximos passos são medir a inspeção no servidor, separar tempo de banco/validação/serialização e investigar a fila do proxy e catálogos.

## Diagnósticos preservados

- `initial.json`: protótipo do observador tinha um operador unário indevido e retornou `null`; não é prova de UI. Foi corrigido antes dos registros qualificados.
- `interface-initial.json` e `probe-final-initial.json`: observação de 20 s terminou antes da prévia/projeto estarem disponíveis. A mesma sessão foi consultada novamente, sem reiniciar os servidores; os registros `settled` demonstram o estado posterior.
- Os primeiros registros de rascunho da comparação tinham seletor explícito `aria-label`, enquanto o textarea recebe nome pelo label. O campo capturado ficou `null`; não são usados para certificar preservação do rascunho. O observador passou a localizar o label visível, e a prova foi repetida na interface, inclusive depois da última mudança de produto.
- `final-clean.json` e `final-interface.png`: alteração do script de validação provocou recarga completa pelo Vite. O ref anterior já não existia; a instância estava reconstruindo e não havia prévia. Não são passe. O log do servidor confirmou `page reload scripts/validation/editor-materials-panel-observe.py` às 16:59:47. `final-clean-settled` foi observado depois da reconstrução, com rascunho vazio e zero consultas automáticas de capacidade local. A prova de rascunho cobre alternância de abas, não recarga do navegador.

Backups exatos e diffs dos dois componentes estão neste diretório. Entre os 77 hashes do checkpoint anterior, só VideoStudio mudou; os outros 76 continuaram iguais. ContextualEditingPanel não constava daquela lista e foi acrescentado com seu backup exato nesta rodada. Nenhum snapshot anterior de fontes foi reescrito.

O objetivo permanece aberto: desempenho do inspetor, repertório/planejamento, avaliação humana dos estudos, três briefs novos após aceite dirigido, avaliação/integração de geradores externos e limpeza dos clones recusada. Esta etapa melhora o editor existente e seus diagnósticos, sem substituir o resultado audiovisual final por testes de UI.
