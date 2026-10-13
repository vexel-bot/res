# KLIC — retry e validação real em 12/09/2026

## Escopo

Alterações limitadas ao backend de geração da KLIC, testes e diagnóstico. Frontend, autenticação, arquitetura de dados e persistência não foram modificados. `.env`, Google Cloud e TTS preservados. Credencial utilizada somente pelo cliente backend existente; nenhum valor, header ou payload de erro do SDK foi registrado.

## Diagnóstico e limites da evidência

O registro histórico `74b458cc-5b82-4e58-9cff-d3e108aa099c` contém HTTP 503 e `KLIC_PROVIDER_UNAVAILABLE`, mas não preservou o código canônico/razão upstream. Não é possível reconstruir esses campos nem afirmar a causa exata daquela falha a partir desse registro.

Os novos logs extraem exclusivamente status HTTP e códigos/razões Google conhecidos. Mensagens livres, headers e metadados são descartados. São tratados os envelopes JSON do SDK, inclusive prefixo de erro de streaming e array de um elemento. Um HTTP 503 sem código canônico reconhecido não dispara retry automático por suposição.

## Política implementada

- Somente HTTP 503 (`UNAVAILABLE`) e HTTP 429 (`RESOURCE_EXHAUSTED`) permitem retry. Quando o SDK omite o rótulo textual, o próprio status HTTP canônico é aceito; qualquer código conflitante ou razão permanente bloqueia a repetição.
- Falhas permanentes de autenticação, permissão, configuração, faturamento ou modelo não permitem retry.
- Máximo de três tentativas totais (a inicial e duas repetições), com o mesmo modelo.
- Backoff exponencial com jitter: 750–1250 ms antes da segunda tentativa; 1500–2500 ms antes da terceira.
- Retry nativo do SDK permanece desabilitado (`attempts: 1`), evitando multiplicação de chamadas.
- AbortSignal/deadline da operação continua sendo respeitado, inclusive durante a espera.
- Nenhuma repetição automática depois de publicar conteúdo parcial: evita duplicar texto já enviado ao chat.
- Logs por tentativa: requestId quando disponível, provider, modelo, etapa, tentativa, evento, status/código/razão seguros e espera programada.

## Chamadas REAIS — provider `developer-api`, modelo `gemini-3.8-flash`

| Teste / requestId | Status upstream | Código/razão de erro | Tentativas | Resultado |
| --- | --- | --- | --- | --- |
| Diagnóstico inicial `fb4c2cfa-2593-4c7f-a887-6f34fa8446db` | 200 | Não se aplica | 1 | Resposta exata `KLIC funcionando.` |
| Diagnóstico com retry instalado `e0f1efe5-7d2b-4f80-9da9-c11c791fc9a5` | 200 | Não se aplica | 1 | Resposta exata `KLIC funcionando.` |
| Chat, execução inicial `d917667c-5296-4de2-bed9-f8e0496dcf53` | 503 | Não extraído pelo parser inicial | 1 | Falha explícita, sem fallback |
| Chat, repetição manual do mesmo requestId após ajuste | 200 | Não se aplica | 1 nesta execução | Resposta exata `KLIC funcionando.`, confirmada no navegador |
| Contexto após reload, execução inicial `c0bb4fcc-d493-44fe-8276-705fad24c51a` | 503 | Não extraído nessa execução | 1 | Falha explícita, sem fallback |
| Contexto, repetição manual do mesmo requestId após ajuste | 200 | Não se aplica | 1 nesta execução | Recuperou corretamente a resposta anterior, sem ela constar no novo pedido |
| Nova conversa `f1bdf5f0-76fb-44ca-9431-2685ca54bac6` | 200 | Não se aplica | 1 | Resposta exata `KLIC funcionando.` |
| Diagnóstico final `be5ed473-cfd0-40e1-bd01-aeb719da9b2d` | 200 | Não se aplica | 1 | Resposta exata `KLIC funcionando.`, com a versão final do retry |
| Google Chrome `36b40770-74c0-47bc-93fa-6af05aaae16d` | 200 | Não se aplica | 1 nesta execução | A mensagem `oi` recebeu resposta real da KLIC no navegador externo |

O fluxo normal de retry manual reutiliza o requestId, portanto as execuções manuais acima não devem ser confundidas com as tentativas automáticas de uma única execução.

O problema relatado no Chrome foi reproduzido. Tanto o Chrome quanto o navegador do Codex chegaram à mesma rota autenticada e ao mesmo backend. A diferença observada era a intermitência HTTP 503 do provider, combinada com um envelope do SDK que por vezes preservava apenas o status HTTP. O retry passou a reconhecer o status canônico 503/429 mesmo quando o rótulo textual é omitido, continuando a rejeitar códigos conflitantes e razões permanentes. Após reiniciar o backend, a repetição no próprio Chrome concluiu com resposta real.

Histórico e resposta foram confirmados visualmente após reload. A nova conversa foi aberta pelos controles existentes, sem alterar sessão, permissões ou armazenamento. As respostas de sucesso vieram da Gemini Developer API, nunca de mock ou fallback local.

## Modelo mantido

`gemini-3.8-flash` permaneceu configurado: ele voltou a responder, inclusive no chat real. A condição para testar/substituir por `gemini-3.7-flash` (503 persistente após o ciclo de tentativas) não ocorreu na validação final. Não foi feita chamada ao 3.7 ou ao Vertex AI. Há evidência de falha intermitente, não de indisponibilidade contínua nem de uma razão específica de capacidade confirmada pelo Google.

## Regressão

Testes controlados cobrem três tentativas, 503 e 429, backoff/jitter, erro permanente sem repetição, cancelamento, deadline, stream parcial sem replay e ausência de credenciais nos diagnósticos. Esses testes unitários não são usados como evidência de resposta real do provedor.

Validação final: 70 testes aprovados, `npm run lint` (TypeScript) aprovado e `npm run build` aprovado. O aviso preexistente de bundle acima de 500 kB permanece; o bundle frontend manteve o mesmo hash `index-CPQbDhTj.js`.

Diagnóstico backend repetível: `npx tsx scripts/diagnose-klic-provider.ts`. Ele lê a configuração privada existente, exige Developer API e registra apenas metadados seguros e se a resposta exata foi recebida.
