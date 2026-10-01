# Implementação — revisão editorial no Video Studio

Data: 05/09/2026. Workspace canônico: `C:\Users\edugu\Downloads\res`.

## Entrega

O controle editorial do backend agora tem interface em **Video Studio → Revisão**. Este incremento permite registrar planos, examinar arquivos privados e registrar decisões humanas. Não produz uma voz melhor por si só e não constitui a entrega de um novo anúncio.

Complementa o [registro do backend](CLICKO_EDITORIAL_IMPLEMENTATION_2026-09-05.md), sem substituir as rejeições ou aprovações anteriores.

## Como usar

1. Abra um conteúdo de vídeo autenticado que já tenha um documento canônico e evidências na biblioteca.
2. Na aba **Revisão**, consulte o estado retornado pelo servidor. Um documento legado não é inscrito automaticamente.
3. Use **Preparar inscrição UGC/avatar**. Preencha objetivo, CTA e beats. Cada beat exige mensagem, ação visual, motivo do corte e evidência do próprio documento.
4. Registre o plano. Prova do produto, roteiro, storyboard, animatic, voz, rosto/atuação e cenário começam pendentes.
5. Selecione uma evidência em **Arquivo da prévia** e clique em **Carregar prévia verificada**. O arquivo é obtido pela rota autenticada; os bytes são comparados ao SHA-256 registrado antes de abrir a prévia.
6. Para comparar, abra **Comparar referência e candidata**, selecione o segundo arquivo e carregue-o explicitamente. Áudio ou vídeo podem ser examinados em players separados; começar um pausa o outro e restaura a velocidade a 1×.
7. Escolha a etapa, selecione as evidências, escreva observações com timestamps e confirme que as examinou. Só então use **Aprovar etapa** ou **Rejeitar etapa**. O servidor exige owner/admin e registra autor e data.

A comparação não é cega, não iguala automaticamente o volume e não calcula naturalidade, preferência ou eficácia. Os dois seletores não atribuem novos direitos ou origens aos arquivos. Abrir uma prévia nunca aprova uma etapa.

## Comportamento implementado

- Cliente TypeScript regenerado a partir do OpenAPI do backend local; três métodos tipados de plano, revisão e prontidão.
- Evidências de áudio, vídeo e imagens raster compatíveis podem ser examinadas. Outros formatos têm download após conferência, sem execução em iframe.
- Checksum ausente/inválido, divergência ou arquivo acima de 100 MiB impedem a prévia. A verificação de tamanho no cliente ocorre após receber o blob; não é um limite de tráfego de rede.
- Prévia usa URL local temporária de blob, revogada na troca ou desmontagem. Fechar a aba desmonta os players; nova abertura exige recarregar as evidências.
- POSTs usam chave de idempotência mantida para repetição do mesmo payload após resposta incerta. As decisões não são inventadas no cliente.
- Trocar etapa ou evidências limpa a confirmação. Mudar documento/revisão limpa confirmação e rascunhos locais.
- Substituir um plano exige confirmação específica e não herda suas sete decisões.
- Falha de consulta bloqueia os controles até recuperar o estado do servidor.
- O botão de render consulta o estado editorial: para documentos inscritos, pendência, rejeição ou plano obsoleto bloqueiam render. Os controles do backend e worker permanecem independentes da interface.
- Documentos não inscritos preservam os gates existentes. A consulta indisponível bloqueia preventivamente o botão, mesmo nesse caso.
- A tela apresenta a decisão vigente por eixo; o histórico completo continua preservado no servidor, mas não há navegador completo de histórico nesta entrega.
- Pré-produção aprovada não equivale a publicação autorizada. O fluxo inscrito continua bloqueado para publicação até integrar a revisão final do render.
- CSS isolado em `.vs-editorial`, sem alteração de tokens globais ou da landing page Robyn Hod.

## Verificação executada

| Verificação | Resultado |
|---|---|
| `npm run lint` — TypeScript | Passou |
| `npm run build` — Vite + servidor | Passou; aviso de chunk JS acima de 500 kB permanece |
| `tsx --test tests/unit/editorialReview.test.ts` | 3 testes passaram |
| `playwright test tests/e2e/editorial-review.spec.ts --workers=1` | 5 testes passaram |
| `playwright test tests/e2e/critical-journeys.spec.ts --grep 'Video Studio' --workers=1` | 2 testes passaram |

São **10 cenários de teste** neste incremento, não a suíte inteira do produto nem dez vídeos criativos aprovados. Os 37 cenários do backend estão registrados separadamente na entrega anterior, sem serem contados novamente aqui.

Os cinco testes novos de navegador cobrem:

1. Inscrição, rejeição explícita, conferência de bytes privados, comparação e pausa entre players.
2. Mudança de revisão, limpeza de confirmação e novo plano sem decisões herdadas.
3. Resposta de mídia adulterada bloqueada antes da prévia.
4. Falha de conexão, bloqueio preventivo e recuperação sem confirmação automática.
5. Integração na aba real do Video Studio, bloqueio do botão de render e persistência após recarga.

Os testes usam API FastAPI real com banco e armazenamento isolados. Interceptações deliberadas existem somente para simular arquivo adulterado e falha de conexão. Quatro cenários montam o componente em um host de teste; o quinto usa o Video Studio completo. A regressão legada inclui upload, ingest, edição e render FFmpeg de uma fixture técnica.

O áudio dos testes é um sinal senoidal de quatro segundos, não voz humana. As decisões gravadas pelos testes pertencem exclusivamente aos workspaces descartáveis de teste.

Inspeção visual realizada nas capturas:

- `artifacts/validation/editorial-review-360.png` — painel estreito, sem overflow horizontal.
- `artifacts/validation/editorial-review-1024.png` — host de teste em viewport maior.
- `artifacts/validation/editorial-review-studio.png` — painel integrado. A imagem central de café é o placeholder preexistente do Studio, não um novo vídeo ou evidência criativa gerada neste incremento.

## Limites e próximo trabalho

Não houve chamada paga, leitura de chave, nova síntese de voz, clonagem, render do Caio, publicação, deploy ou promoção de provider. O projeto em OneDrive permaneceu intocado.

Ainda faltam:

1. Casting local com amostras autorizadas, protocolo comparável e medição de naturalidade/prosódia. Os players entregues apoiam a revisão, mas não substituem esse fluxo.
2. Admissão fiel de narração local e fonte visual sintética na composição, com direitos e proveniência, sem chamar voz de som natural ou Sora de upload humano.
3. Composição do apresentador com demonstração, cenários e motion funcional dentro das capacidades reais do renderer.
4. Revisão final de montagem/vídeo vinculada ao render e integração da autorização de publicação.

O Caio e os arquivos privados rejeitados não foram importados automaticamente para um documento fictício. A próxima etapa deverá usar IDs e direitos reais e preservar a rejeição existente.

## Arquivos principais

- `src/studios/EditorialReviewPanel.tsx`
- `src/studios/editorialReview.ts`
- `src/studios/editorial-review.css`
- `src/studios/VideoStudio.tsx`
- `src/api/productApi.ts`
- `src/api/schema.d.ts`
- `tests/unit/editorialReview.test.ts`
- `tests/e2e/editorial-review.spec.ts`
- `tests/fixtures/editorial-harness.tsx` — somente testes, não importado pelo bundle de produção.
