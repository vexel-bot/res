# Recuperação da KLIC — evidências e bloqueadores

Atualização: 11/09/2026. Esta recuperação não está concluída. Testes com provedores controlados não são apresentados como respostas reais do Gemini.

## Causas confirmadas

1. **Acesso ao provedor ausente.** O ambiente ativo seleciona a Gemini Developer API, mas não possui `GEMINI_API_KEY` nem `GOOGLE_API_KEY` utilizável. `configured: false` foi confirmado novamente em 11/09. A presença de credenciais de Text-to-Speech não autoriza automaticamente o chat.
2. **Alternativa Vertex AI bloqueada.** A chamada real ao modelo, usando a conta de serviço Google existente e Vertex explicitamente selecionado somente no processo de diagnóstico, retorna HTTP 403 `SERVICE_DISABLED`. Repetido em 11/09. O serviço `aiplatform.googleapis.com` precisa estar habilitado e a identidade de execução precisa ter acesso. Nenhuma API, permissão ou cobrança foi ativada por esta tarefa.
3. **Reload interrompia o envio no desenvolvimento.** A pasta de persistência `.clicko-data` era observada pelo Vite. Criar a conversa ocasionava recarregamento e interrompia o envio antes de chegar ao provedor. Após excluir os dados privados do watcher, o teste pelo navegador passou a preservar a mensagem e a alcançar o erro específico de configuração no backend. Um teste com Vite real confirma que gravações atômicas, backups, locks e novas subpastas não geram reload, enquanto alterações no HTML continuam gerando HMR.
4. **Erros mascarados por respostas prontas.** Os caminhos antigos de chat devolviam texto local com HTTP 200 quando o provedor falhava. Esses fallbacks foram removidos do chat operacional e de `/api/ai/chat`.

## Correções aplicadas

- Seleção centralizada do provedor KLIC: chave no servidor ou Vertex AI explicitamente habilitado por configuração. Sem chave hardcoded, sem credencial no frontend e sem ativação automática de serviços Google.
- Modelo de chat configurável em `KLIC_CHAT_MODEL`, com `gemini-2.5-flash` como padrão. Os caminhos de chat deixaram de percorrer a lista antiga de modelos de outros geradores. A disponibilidade real do modelo neste projeto ainda não foi comprovada, porque a autorização falha antes da geração.
- Erros separados para configuração ausente, API desativada, credencial/permissão recusada, faturamento, cota, modelo, rede, timeout, resposta vazia e bloqueio do provedor. Logs incluem código, etapa e identificador da requisição, sem copiar o payload ou a credencial do SDK.
- Falhas do chat deixam de ser respostas de IA simuladas. O streaming termina com evento de erro e estado persistido de falha, não `complete`. HTTP 200 inicial do transporte NDJSON não significa geração bem-sucedida.
- Limites de espera no transporte JSON, cancelamento e reconciliação do histórico. Erros de proxy HTML não aparecem como mensagens cruas do parser JSON.
- Leitura incremental de UTF-8, reconhecimento da última linha sem newline e encerramento ao receber evento terminal, sem esperar indefinidamente pelo EOF do proxy.
- Bloqueio de envio durante troca/limpeza de conversa. Resposta tardia de favorito altera somente o favorito, sem substituir o histórico por um snapshot antigo.
- Verificação de cancelamento e autorização também depois do último fragmento recebido. Um iterator que termina normalmente após abort não pode salvar resposta parcial como concluída.
- Watcher do Vite ignora persistência privada; HMR de código permanece habilitado.

Nenhum redesenho de interface, alteração de permissões ou desativação da autenticação foi feito por esta recuperação. Alterações anteriores do repositório foram preservadas.

## Evidência do navegador real

Ambiente de desenvolvimento, perfil corporativo, `http://localhost:3000/klic`:

| Verificação | Resultado observado |
| --- | --- |
| “Olá, responda apenas: KLIC funcionando.” | Requisição recebida pelo backend; mensagem preservada; erro `KLIC_PROVIDER_NOT_CONFIGURED`. Nenhuma resposta de modelo. |
| Tentar novamente | Mesmo requestId nos dois logs; sem duplicação da mensagem. Continua bloqueado por configuração. |
| Atualizar a página | Mensagem e erro específico recuperados do histórico. |
| “Qual foi a frase que pedi para você responder anteriormente?” | Segundo envio aceito depois de falha e reload; novo erro de configuração. Contexto do modelo não validado. |
| “Quanto é 7 vezes 8? Responda em uma frase curta.” | Envio realizado pela interface; não constitui aprovação, pois o provedor continua sem configuração. |

O requestId observado na primeira mensagem e na tentativa foi `a4be1741-8117-4864-95fc-996f2e212d88`. Os logs registraram `conversation-stream` e `KLIC_PROVIDER_NOT_CONFIGURED` sem conteúdo privado do provedor.

## Testes automatizados

Rodada final em 11/09/2026: `npm test` **63 aprovados, zero falhas**; `npm run lint` (`tsc --noEmit`) **aprovado**; `npm run build` **aprovado**, incluindo bundle do servidor e worker de anexos. Esses resultados não substituem a validação do provedor real.

A suíte inclui regressões de autenticação, isolamento por usuário/workspace, persistência, duplicação, concorrência, cancelamento, contexto limitado, anexos e transporte. Os testes de geração usam um provedor controlado explicitamente dentro dos testes; isso não demonstra disponibilidade do serviço Google.

Novas coberturas desta recuperação:

- Seleção de provedor e rejeição de placeholders; credencial TTS não implica autorização Gemini.
- Classificação dos erros sem vazamento de detalhes sensíveis.
- UTF-8 fragmentado, último evento sem newline, evento terminal sem fechamento da conexão.
- JSON inválido, resposta HTML de proxy e tentativa posterior válida.
- Timeout e cancelamento de requisições JSON.
- Cancelamento com iterator que retorna normalmente.
- Watcher Vite real com dados temporários, exclusão de gravações privadas e controle positivo de HMR.

## Build de produção/local equivalente

O build foi compilado e iniciado com `NODE_ENV=production`, em porta separada (3102), sem alterar o servidor de desenvolvimento:

| Verificação | Resultado |
| --- | --- |
| `/api/health` | HTTP 200, processo ativo. Não é healthcheck do provedor. |
| `/klic` | HTTP 200, HTML do build servido. |
| `/api/capabilities` | `geminiConfigured: false`. |
| `/api/governance/auth/session` sem sessão | HTTP 401. Bypass de desenvolvimento não ativo. |
| Envio ao chat com identidade apenas em headers do cliente | HTTP 401. |
| Chat autenticado com geração real em produção | **Não validado.** Acesso ao provedor ausente; não foi criada uma sessão privilegiada artificial para mascarar esta limitação. |

O build possui o aviso já existente de bundle frontend acima de 500 kB. Esta tarefa não redesenhou o carregamento geral da plataforma para ocultar o aviso.

## Status de contexto, voz e multimodalidade

- **Contexto:** montagem, isolamento e persistência cobertos por testes controlados. Recuperação da mensagem após reload observada no navegador. Uso semântico desse contexto pelo modelo real não aprovado.
- **Voz e anexos:** não aprovados ponta a ponta nesta recuperação. A prioridade definida foi restabelecer primeiro o texto real; essa etapa segue bloqueada. Testes locais de parsers e testes anteriores de TTS não equivalem a uma conversa multimodal funcional.
- **Estabilidade real:** não aprovada. Três mensagens com falha não equivalem a três respostas corretas.
- **Perfis pessoal/corporativo e produção:** regras de isolamento e autenticação cobertas pela suíte; respostas reais por perfil e nos dois ambientes ainda precisam ser validadas.

## Ação necessária para continuar

O responsável deve disponibilizar **uma** das opções no servidor:

1. Configurar `GEMINI_API_KEY` válida, com acesso e cota para o modelo selecionado. Não colocar a chave em variável `VITE_*`, código frontend, chat, commit ou documentação.
2. Habilitar o serviço Vertex AI no projeto Google, verificar faturamento/cota e autorizar a identidade do servidor; então configurar `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT` e `GOOGLE_CLOUD_LOCATION` (padrão `global`). Manter a credencial privada fora do repositório ou usar a identidade do runtime.

Reiniciar o servidor após alterar o ambiente. Primeiro executar as três mensagens reais, validar streaming e contexto, depois repetir em nova conversa, após reload e navegação, nos dois perfis e no build de produção. Somente com esse fluxo aprovado avançar para a validação completa de voz e anexos.

Referência de configuração: [Google Gen AI SDK — inicialização da Developer API e Vertex AI](https://googleapis.github.io/js-genai/release_docs/classes/client.GoogleGenAI.html).

## VEREDITO DE FUNCIONALIDADE DA KLIC

**KLIC NÃO FUNCIONAL / NÃO PRONTA PARA LANÇAMENTO**

Foram corrigidos defeitos locais verificáveis, mas o fluxo principal ainda não tem acesso autorizado ao provedor. Nenhuma resposta real bem-sucedida foi obtida nesta recuperação. A conclusão depende da configuração externa e da validação ponta a ponta posterior.

## Atualização — 12/09/2026

- A configuração da Gemini Developer API passou a aceitar **exclusivamente** `GEMINI_API_KEY`. `GOOGLE_API_KEY` é ignorada pela KLIC para impedir que uma chave usada pelo YouTube/Radar substitua silenciosamente a credencial do chat.
- `GET /api/capabilities` agora informa com segurança `{ mode, model, configured, configurationIssue }`, sem chave, projeto, cabeçalho ou token. Em desenvolvimento e no build de produção local, retornou `mode: developer-api`, `model: gemini-2.5-flash`, `configured: false` e `KLIC_GEMINI_API_KEY_REQUIRED`.
- A ausência de credencial agora produz a orientação explícita: “A variável privada GEMINI_API_KEY precisa ser configurada no servidor da Clicko.”
- Cada geração textual registra somente evento de início/conclusão, `requestId`, provedor, modelo, duração e quantidade de caracteres. Prompt, resposta, chave e headers não são registrados.
- `.env.example` documenta `GOOGLE_GENAI_USE_VERTEXAI=false` para a Developer API e deixa Vertex como opção deliberada.
- Nova execução: `npm test` 63/63, lint/typecheck aprovado e build aprovado. O build de produção iniciou em porta separada, serviu `/klic` e respondeu ao healthcheck; o capability continuou `configured: false`.

Os testes de três respostas reais, contexto semântico, reload com nova resposta, nova conversa, perfis, voz e anexos permanecem bloqueados. Nenhuma credencial válida foi adicionada ao ambiente até esta atualização; portanto, o veredito acima permanece inalterado.
