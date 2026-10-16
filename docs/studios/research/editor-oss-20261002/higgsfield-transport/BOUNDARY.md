# Adaptador Higgsfield: limite deste incremento

05/10/2026. A rodada anterior produziu evidência nova: nota humana geral 1/5 e escolha de anúncio com cenas/narração. Isso muda a prioridade para geração de materiais e direção. O objetivo completo segue pendente.

Implementar transporte backend para estimar, submeter com intenção imutável/idempotência, consultar e solicitar cancelamento de pedidos. Modelos desta primeira versão: Kling Standard 3.0 texto→vídeo e imagem→vídeo, Ideogram 4.0 geração/edição de imagem. Parâmetros de plano único; não anunciar multi-shot ou campos de schema desconhecido. Não registrar o adaptador em jobs, frontend ou configuração de produção nesta etapa.

Arquivo novo: `backend/app/providers/studios/higgsfield.py`. Os tipos `PreparedGeneration`, `GenerationQuote` e `GenerationReceipt` são internos ao transporte, não contratos compartilhados de Studio ou segundo modelo de projeto. Não há alteração/migração de CreativeDocumentV1, GenerativeVideoRequestV1 (Sora), jobs ou schema de API. Leitor neste incremento: testes explícitos. Integração persistida ao serviço de materiais permanece necessária antes de habilitar produção.

A intenção guarda JSON canônico, modelo e chave explícita; seu digest vincula estimativa e submissão. A chave deve ser persistida pelo futuro serviço antes do POST. Estimativa em Decimal usa USD retornado pela conta, não a tabela promocional. Teto e validade local da estimativa são pré-condições do transporte; não constituem ledger, reserva por workspace ou teto agregado de produção. Não há aquisição de credenciais, consulta ao .env ou chamadas reais nesta rodada.

O pedido fornecido pelo servidor precisa de URLs de polling/cancelamento vinculadas à origem e ao request_id. Nunca enviar credenciais a URL arbitrária ou seguir redirect. Falha ambígua preserva a intenção; não existe retry automático nem criação de chave nova. Receipt completed contém candidatos remotos; não aprova qualidade, não baixa mídia ou insere material no documento.

Estimativas também ficam vinculadas ao fingerprint das credenciais utilizadas. Mudança de credenciais exige nova cotação, sem tratar fingerprint como identidade comprovada da conta. Validade local de cinco minutos é política interna, não garantia de preço do fornecedor. Cotação transitória usa relógio monotônico; o serviço deve recotar ao recuperar um pedido e conservar a reserva/intenção persistidas para reconciliar resultados ambíguos.

Cancelamento 202 significa pedido aceito, não prova de estado canceled; consultar depois. A partir de in_progress, não prometer interromper custo. Polling retorna uma observação por chamada, sem loops/sleeps ou inferência de terminalidade por timeout.

Fontes verificadas nesta rodada: [texto→vídeo](https://open.higgsfield.ai/models/kling-video/v3.0/std/text-to-video/api-reference), [imagem→vídeo](https://open.higgsfield.ai/models/kling-video/v3.0/std/image-to-video/api-reference), [Ideogram](https://open.higgsfield.ai/models/ideogram/v4.0/api-reference), [autenticação](https://docs.higgsfield.ai/docs/authentication), [idempotência](https://docs.higgsfield.ai/docs/concepts/idempotency), [lifecycle](https://docs.higgsfield.ai/docs/concepts/requests), [estimate](https://docs.higgsfield.ai/docs/concepts/billing-and-retention).

Teste HTTP simulado comprova comportamento local de falhas, bindings e cabeçalhos. Não comprova acesso na conta, geração, cobrança, qualidade ou preservação de produto. Antes de gasto real: serviço com intenção/reserva/reconciliação persistidas e escopo autenticado; admissão de mídia em storage, checksum/probe; direito de uso e avaliação do piloto. O direcionamento anexado proíbe comprar APIs. Geração permanece desativada por padrão.
