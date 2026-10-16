# NullMotion, Ideogram 4.5 e Higgsfield para a Clicko

Análise em 05/10/2026, no projeto original `C:/Users/edugu/Downloads/res`. Pesquisa pública e leitura de código; gasto externo nesta rodada: US$ 0. Nenhuma chave criada, geração enviada, assinatura comprada ou modelo instalado. Disponibilidade documentada não significa acesso confirmado na conta da Clicko.

## Decisão recomendada

Priorizar Higgsfield como candidato a fornecedor de cenas e imagens. Usar Ideogram 4.5 quando a necessidade for corrigir uma imagem preservando o produto e a composição. Estudar NullMotion para melhorar interação e diagnóstico da prévia. Manter CreativeDocumentV1, MotionGraphV1, receitas tipadas, Remotion e FFmpeg como percurso de autoria e execução do editor.

Minha hipótese comercial é oferecer peças com direção, materiais selecionados, texto editável, identidade visual e montagem verificável. Gerar apenas o material que falta pode reduzir custo e retrabalho. Essa hipótese precisa de um piloto com avaliação humana e custo por entrega aceita; preço anunciado por geração não comprova margem nem qualidade.

## NullMotion: o que foi encontrado no código

Repositório analisado: [blixvip/NullMotion](https://github.com/blixvip/NullMotion/tree/2795457432a63e7e28879210601cede25915e561), commit `2795457432a63e7e28879210601cede25915e561`, de 04/10/2026. Leitura em memória, sem clone, execução ou incorporação. URLs, SHA-256 e tamanhos estão nos três recibos `NULLMOTION_IDEOGRAM_HIGGSFIELD_20261005.*.json`.

O [README nessa revisão](https://github.com/blixvip/NullMotion/blob/2795457432a63e7e28879210601cede25915e561/README.md) distingue o produto hospedado Null Studio do projeto público. O público apresenta referências, trechos e drafts HTML sincronizados; geração não está conectada. Não há licença geral do projeto identificada na árvore examinada. Os avisos de bibliotecas não concedem licença ao restante do código. Não tratar este repositório como componente comercial livre para copiar.

Observações próprias da leitura dos arquivos no commit fixado:

| Arquivo e trecho | Mecanismo observado | Aplicação possível no res |
|---|---|---|
| `public/editor-model.mjs:13–19` | Localiza trecho e tempo da fonte a partir do tempo da sequência | Conferir a diferença entre frame da composição e tempo da fonte; testar limites de corte e speed sobre os contratos atuais |
| `public/editor.mjs:240–278` | Prévia segue relógio do vídeo; usa tolerâncias em segundos e avança para próximo trecho | Usar vídeo decodificado para observação; conservar frames inteiros no documento e no inspector do res |
| `public/editor.mjs:122–140` | Salva seleção de clipes em localStorage; undo conserva até 30 estados de clipes | Referência de interação. Nosso histórico exige persistência, autoria e conflito de revisão; não importar esse histórico local como fonte de verdade |
| `public/demo.mjs:264–320` | Exporta canvas por WebCodecs; rVFC recebe mediaTime, fila pausa a fonte, encoder tem limite de fila, depois adiciona áudio | Estudar instrumentação de timestamps e descarte de recursos. Não substituir o renderer já qualificado |
| `media.js` | Suporta resposta HTTP Range, inclusive 206/416 | Investigar acesso parcial e cache de vídeos grandes, mantendo checksum e autorização por asset |
| `scripts/plan-sections.mjs` | FFmpeg detecta mudanças com limiar de cena | Candidato a marcadores para inspeção; um corte detectado não determina narrativa ou aprovação estética |
| `public/drafts.mjs` | Beats escritos manualmente, GSAP, canvas de referência e tamanho de fonte por heurística | Repertório visual para receitas existentes; não usar heurística por comprimento como medição de fonte final |
| `server.js:24–25,75,115` | Diagnóstico NOT_CONNECTED, capacidades de geração/render falsas e rotas não implementadas retornam 501 | Tornar capacidade pendente explícita; não exibir geração operacional onde só há interface |

Os testes lidos em `test/editor.test.js` cobrem segmentação, localização de trecho e reorder; `test/reference-policy.test.js` cobre curadoria. Não executei esses testes. A alegação do exportador de não perder frames não foi comprovada aqui: callback de apresentação e fila limitada não bastam para demonstrar decodificação de todos os frames sob carga, VFR ou seeks. Essa verificação exigiria contagem e timestamps contra a fonte completa.

As mídias de demonstração não foram baixadas nem adotadas para campanhas. Não instalar dependências ou levar os drafts e outro modelo de timeline para o res para obter apenas essas ideias.

## Ideogram 4.5: papel concreto

A versão existe e é apresentada como modelo de edição precisa, incluindo alterações de produto, cor e texto, com menor deriva em edições sucessivas. São alegações do fornecedor; ainda não fizemos comparação com materiais da Clicko. [Página oficial](https://ideogram.ai/models/4.5).

A API documenta geração e precise-edit em `/v2/image/generate/ideogram-4-5` e `/v2/image/precise-edit/ideogram-4-5`, com opção assíncrona. Podemos importar o resultado como asset e manter títulos, preço, CTA e marca em camadas editáveis do documento. Uma imagem gerada não vira automaticamente vetor, fonte editável ou grafo de animação. [API oficial](https://developer.ideogram.ai/ideogram-api/api-overview).

No Higgsfield confirmei **Ideogram 4.0**, a US$ 0,03 por imagem; não confirmei 4.5 no catálogo examinado. Não usar esse preço como preço do 4.5. [Modelo no Higgsfield](https://open.higgsfield.ai/models/ideogram/v4.0/playground). A [tabela direta do Ideogram](https://ideogram.ai/pricing/?pricing_tab=api) não expôs o valor numérico do 4.5 na leitura pública desta rodada; esse valor permanece pendente.

Os pesos publicados identificados são do Ideogram 4.0. Código de inferência Apache-2.0 e pesos com licença não comercial são coisas distintas. A licença comercial self-serve de hospedagem própria não inclui acesso de terceiros semelhante a API; produto voltado a clientes exige enquadramento Enterprise ou termos da API hospedada. Não baixar pesos supondo 4.5 gratuito para produção da Clicko. [Licenciamento oficial](https://ideogram.ai/licensing/).

## Higgsfield: custo e limites da comparação

Higgsfield oferece uma API de geração de mídia assíncrona. Sua cobrança usa saldo separado das assinaturas e créditos do site. Também não oferece acesso a modelos de texto/LLM nessa API: portanto não substitui por si só a função de planejamento e inspeção hoje exercida pelo Gemini no res. [API e termos, seções 1.2–1.3](https://open.higgsfield.ai/terms-of-service).

Estimativas aritméticas de **uma tentativa de 15 segundos**, em USD, com taxas públicas observadas nesta data:

| Opção | Taxa usada | Custo calculado | Limite |
|---|---:|---:|---|
| Kling 3.0 Standard TTV pelo Higgsfield, promoção | 0,042/s | **0,6300** | Promoção de 50%; resolução e parâmetros exatos precisam de estimate da conta |
| Mesmo modelo, taxa normal anunciada | 0,084/s | **1,2600** | Não fixar a margem assumindo promoção permanente |
| Gemini Omni Flash / Preview, Standard, saída 720p | 5.792 tokens/s × 17,50 / milhão | **1,5204** | Acrescentar entradas a 1,50/milhão e saída de texto/thinking a 9,00/milhão |
| Seedance 2.5 pelo Higgsfield, 720p, 16:9, sem vídeo de entrada, antes de desconto | 0,4622/s | **6,9330** | Diferente do preço mínimo de catálogo em 480p; modelo e capacidade também diferem |

Fontes: [Kling](https://open.higgsfield.ai/models/kling-video/v3.0/std/text-to-video/playground), [Google](https://ai.google.dev/gemini-api/docs/pricing), [Seedance](https://open.higgsfield.ai/models/bytedance/seedance-2.5/text-to-video/playground). Valores calculados no recibo `NULLMOTION_IDEOGRAM_HIGGSFIELD_20261005.costs.json`. Arredondamento final, inputs, áudio/configuração, créditos da conta e impostos dependem da requisição real. Não são orçamentos de peças completas nem comparação controlada de qualidade.

Há uma oportunidade de economia com Kling nessa configuração; não existe evidência para dizer que todo modelo no Higgsfield é mais barato que Omni. Na produção, substituir a tabela pública pelo estimate autenticado com o mesmo modelo e parâmetros: `POST /estimate/{model}`. O exemplo de créditos da documentação é ilustrativo, não preço do catálogo. [Estimativa e cobrança](https://docs.higgsfield.ai/docs/concepts/billing-and-retention).

Exemplo de proposta para um anúncio de 15 s: gerar uma cena de 5 s e duas imagens com Ideogram **4.0**, compondo o restante localmente. Material em uma tentativa: US$ 0,27 na promoção ou US$ 0,48 sem promoção. Admitindo no máximo duas tentativas pagas para cada material, teto aritmético US$ 0,54/0,96 por peça; seis peças: US$ 3,24/5,76. São hipóteses de mix, não limites já aprovados, comportamento executado ou preço do Ideogram 4.5. Render local, direção, inspeção, armazenamento e trabalho humano continuam tendo custo.

Medida para decidir: soma dos gastos de todos os candidatos / quantidade de entregas aceitas. Se metade for aceita, o custo médio de material por entrega dobra; se nenhuma for aceita, não reportar custo por entrega zero. Separar esse custo de latência, correções, infraestrutura e preço de venda. Para margem em BRL, usar câmbio efetivo e taxas do pagamento no momento da compra, sem conversão presumida nesta pesquisa.

### Pergunta do usuário: vídeo de um minuto

Na taxa publicada do Kling 3.0 Standard TTV, 60 segundos gerados custam US$ 2,52 na promoção de 50% ou US$ 5,04 na taxa normal. O modelo documenta até 15 segundos por geração: exemplo de entrega de um minuto é montar quatro clipes de 15 segundos. Isso não estabelece continuidade automática entre os clipes nem comprova a qualidade de um minuto final.

Para planejamento conservador sem promoção, gerar o equivalente ao minuto duas ou três vezes custa US$ 10,08 ou US$ 15,12. Esse cálculo representa cenários de tentativas, não taxa de rejeição medida ou garantia de orçamento suficiente. Áudio, resolução e modelo podem alterar a cotação; confirmar a requisição no estimate da conta. Montagem, narração separada, música, imagens de referência e demais custos não estão incluídos. Fonte de taxa/duração: [Kling no Higgsfield](https://open.higgsfield.ai/models/kling-video/v3.0/std/text-to-video/playground).

O feedback do usuário é que o editor atual está ruim e ainda não consegue entregar os vídeos desejados. Os renders e testes técnicos anteriores não resolvem essa lacuna de produto. A recomendação passa a enfatizar demonstrar uma entrega útil com geração externa e montagem verificável antes de expandir recursos do editor; esta rodada não executou esse vídeo nem atribuiu aprovação visual.

### Entrega com montagem pelo sistema: orçamento inicial, sem média medida

Para provisionar o piloto com Kling Standard sem desconto e novas tentativas, reservar US$ 15–20 por peça de um minuto é uma decisão de planejamento. A parcela calculável de geração é US$ 10,08–15,12 para 120–180 segundos gerados e seleção de 60 segundos. O saldo é apenas folga: não corresponde a uma tarifa ou medição de montagem, planejamento, armazenamento ou infraestrutura.

Não temos média medida do percurso Higgsfield → admissão → montagem → entrega aceita. A montagem local não adiciona uma tarifa Higgsfield por minuto, mas usa recursos próprios. Trabalho humano, narração e música contratadas à parte, impostos e configuração de áudio/resolução não estão cobertos por um custo demonstrado. O piloto deve medir essas parcelas antes de definir margem ou preço de venda. A promoção reduz a mesma parcela de geração para US$ 5,04–7,56; não deve sustentar uma promessa permanente de preço.

## Integração proposta sobre o código existente

Esta rodada prepara o contrato de implementação; não registra um provider operacional nem altera a fonte canônica.

1. **Escopo do material.** Diretor pede imagem, imagem corrigida ou cena de duração definida, com critérios de produto/marca, fonte autorizada e intervalo de uso. A saída candidata entra pela biblioteca e pelos serviços de materiais; montagem e texto continuam no CreativeDocumentV1.
2. **Orçamento antes da submissão.** Estimate autenticado, modelo exato, configurações, validade do preço, reserva por workspace e teto por peça/mês. Reutilizar a semântica do orçamento existente; uma falha incerta mantém reserva até reconciliação. Não tratar `estimated_cost_cents` de edição como prova de que já há ledger completo para Higgsfield.
3. **Operação persistida.** Guardar intenção, request hash, workspace, usuário, revisão, reserva, idempotency key e request_id no backend antes de permitir polling/publicação. Chaves ficam no servidor. No timeout, replay somente com a mesma chave, endpoint, corpo e webhook; parâmetros distintos retornam conflito. [Idempotência](https://docs.higgsfield.ai/docs/concepts/idempotency).
4. **Ciclo de vida explícito.** Mapear queued/in_progress/completed/failed/nsfw/canceled para o job local. Cancelamento remoto só é possível em fila; depois de iniciado, cancelamento local impede publicação, mas não promete interromper geração nem evitar cobrança. [Estados e cancelamento](https://docs.higgsfield.ai/docs/concepts/requests).
5. **Receber sem confiar em callback isolado.** O webhook é notificação: correlacionar request_id com o tenant, deduplicar e confirmar estado pelo GET autenticado antes de admitir assets. A página consultada não estabeleceu um mecanismo de assinatura que pudéssemos considerar verificado. Persistir o evento e responder rapidamente; polling continua recuperando entregas perdidas. [Webhooks](https://docs.higgsfield.ai/docs/how-to/webhooks).
6. **Material próprio e revisão.** Copiar a mídia gerada para storage autorizado, medir SHA-256, duração/resolução/fps/áudio, registrar modelo/parâmetros/origem/custo. URLs remotas não são armazenamento permanente; retenção documentada mínima de sete dias. Admitir o candidato contra critérios de briefing; completed não significa approved. Troca de checksum invalida revisão anterior.

Entradas locais inspecionadas para essa implementação:

| Responsabilidade | Código existente | Lacuna que precisa de mudança versionada |
|---|---|---|
| Seleção de capacidades e custo por resultado aceito | `backend/app/domain/studios/hybrid_video.py` | Higgsfield precisa de perfil experimental; o enum atual não contém geração/edição de imagem |
| Porta de geração e registro | `backend/app/domain/studios/providers.py` | Registro pago genérico está vazio por intenção; manter desativado até qualificação |
| Operações de vídeo | `backend/app/domain/studios/generative_video.py` | V1 tem provider literal Sora e estimativa específica; não reutilizar preenchendo Higgsfield como Sora nem ampliar V1 silenciosamente |
| Aquisição e admissão de material | `backend/app/services/studios/production_materials.py` | Integrar request_id/recibo externo com revisão e checksum já conferidos pelo serviço |
| Cenas locais | `backend/app/services/studios/scene_generation.py` | Hoje ligado a local_diffusion; não apresentar API remota como geração local |
| Reservas de inspeção/planejamento | `backend/app/services/studios/gemini_editing.py` | Adaptar invariantes de reserva/reconciliação; preservar o planejamento existente |

Antes de mudar contrato compartilhado, registrar versão, leitores, migração e compatibilidade. Não atualizar contratos e implementar um segundo projeto no frontend para acelerar a integração.

Os termos permitem funcionalidades dentro de uma aplicação que agregue valor, mas restringem exposição/revenda direta da API e também mencionam operações de outsourcing/reselling. Uso comercial dos outputs não resolve automaticamente esse enquadramento. Para a Clicko, a proposta de direção + edição é mais consistente com agregação de valor; se o serviço contratado for outsourcing ou revenda de geração, confirmar enquadramento/autorização escrita antes de lançamento. Materiais privados de clientes também exigem conferir a opção de treinamento e termos do modelo escolhido. [Seções 3–5, 7 e 12](https://open.higgsfield.ai/terms-of-service). Isso é uma pendência concreta de lançamento, não motivo para interromper estudo ou edição local.

## Piloto preparado e critérios de decisão

Proposta, ainda sem execução paga: seis briefs curtos, dois de produto, dois de serviço e dois de demonstração de interface. Para interface, usar gravação real autorizada; geração não deve inventar funcionalidades. Máximo de duas tentativas por necessidade de material, registradas como intervenções. Modelo econômico primário: Kling 3.0 Standard; Ideogram 4.0 é apenas cenário de custo, e o 4.5 merece experimento separado após preço confirmado.

Avaliar produto reconhecível, texto/CTA correto, continuidade, legibilidade e acabamento, além de tempo até entrega aceita e custo total. Comparar uma alternativa com o material atual e, onde fizer sentido, com Omni em condições explicitadas. Promover somente os casos de uso que passarem. Não prometer substituição universal de Gemini, autonomia ou qualidade a partir de exemplos do fornecedor.

Trabalho executado aqui: descoberta e pin do repositório, leitura de fontes/testes, comparação de preço, identificação das portas locais e preparo deste handoff. Nenhum novo clone ocupa o computador; permanecem somente os relatórios e recibos pequenos. A limpeza de clones antigos continua registrada no estudo anterior, pois a revisão automática bloqueou a exclusão com `blocked by policy`; não tentei contornar esse bloqueio.
