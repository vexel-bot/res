# Radar de Trends da Clicko

## Estado e fontes

O Radar existente já usava o feed público de tendências do Google, notícias para corroboração e, quando configurada, a API oficial do YouTube (`videos.list`, `chart=mostPopular`). Esta evolução preserva essas fontes e adiciona a API oficial de tendências do Pinterest quando houver autorização específica. Ausência de credencial, falha de uma fonte ou ausência de resultados nunca produz tendências simuladas.

| Fonte | Implementação | Limite importante |
| --- | --- | --- |
| Google Trends | Feed RSS público regional (`BR` ou `US`) | `GLOBAL` usa EUA como referência, não representa todos os países. A [API oficial de Trends](https://developers.google.com/search/apis/trends) é alpha e requer acesso próprio; não é presumida. |
| Google Notícias | Feed RSS público, somente corroboração de assuntos já encontrados | Matérias sem correspondência não viram trends. Termos privados do workspace não são enviados à busca externa. |
| YouTube | [API oficial `videos.list`/`mostPopular`](https://developers.google.com/youtube/v3/docs/videos/list), com `YOUTUBE_API_KEY` ou `GOOGLE_API_KEY` no servidor | Ranking de vídeos populares não equivale a volume de busca ou tendência geral; só é vinculado quando o título corresponde. |
| Pinterest | [Trends API oficial](https://developer.pinterest.com/docs/analytics-and-reports/trends/) com `RADAR_PINTEREST_ACCESS_TOKEN` no servidor | Acesso limitado pela plataforma; dados disponíveis para a data atual e até 50 resultados por chamada. A implementação consulta até 25 palavras-chave em crescimento por região. Crescimento percentual semanal é apresentado apenas quando retornado. |
| Instagram, Facebook, Threads, TikTok, X, LinkedIn | Status explícito de indisponibilidade, sem sinais atribuídos | Nenhuma API, permissão ou plano aprovado para tendências globais foi presumido. É necessário avaliar e habilitar cada fonte individualmente, com escopos autorizados e dados compatíveis com seus termos. Dados de contas conectadas não devem ser confundidos com tendências globais. |

Referências adicionais: [TikTok Research API](https://developers.tiktok.com/docs/en/research-api-get-started), [TikTok Display API](https://developers.tiktok.com/docs/en/display-api-overview), [LinkedIn Community Management](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview?view=li-lms-2026-06), [limites do Pinterest](https://developer.pinterest.com/docs/reference/rate-limits/).

Habilitação pendente por rede: Instagram e Facebook exigem definir um caso de uso permitido e seus escopos para dados das contas autorizadas; Threads exige validar busca/insights e permissões concedidas; TikTok exige acesso aprovado ao produto apropriado (o Display API de vídeos próprios não é um feed global); X exige plano, endpoints e quota contratados; LinkedIn exige avaliação do produto e [aprovação para Community Management](https://learn.microsoft.com/en-us/linkedin/marketing/community-management-app-review?view=li-lms-2025-11). Em todos os casos faltam uma credencial/entitlement verificável e uma especificação de dado realmente disponível para o Radar. Nenhuma dessas redes foi marcada como conectada só porque há suporte OAuth em outra parte da Clicko.

## Arquitetura e fluxo

- `server/radar.ts`: orquestra feeds existentes, normalização para `RadarTrend`, deduplicação textual, score, status e cache de snapshot. Google, YouTube e Notícias continuam adaptadores locais, para preservar o Radar já funcional.
- `server/radar/pinterest.ts`: provider opcional e independente, com validação de resposta, cache de dez minutos, single-flight, no máximo três tentativas apenas para HTTP 429/503, backoff com jitter, prazo total de oito segundos e circuit breaker curto.
- `server/radar/history.ts`: observações de score por escopo e tendências salvas. Em produção exige `SOCIAL_DATABASE_URL` e usa tabelas privadas PostgreSQL; no desenvolvimento usa `.clicko-data/radar-history.json`, fora de `public`/`dist`. Amostras antigas são retidas por até 30 dias.
- `server/klic/router.ts`: `/api/klic/radar` e `/api/klic/radar/saved`, ambos atrás da autenticação e validação de escopo existentes. O endpoint de salvos aceita apenas IDs de tendências obtidas pelo próprio Radar; não aceita objetos de tendência arbitrários do navegador.
- `src/components/KlicRadarSection.tsx`: visões, filtros baseados em dados realmente presentes, histórico de score, fontes, tendências salvas e ações que reaproveitam KLIC, handoff dos estúdios e rascunho do calendário.

O escopo de histórico de score deriva do isolamento validado pelo servidor. Tendências salvas são separadas por `workspaceId`, `userId` e `clientId` autenticados, nunca por IDs livres enviados pelo cliente. Segredos e respostas brutas privadas não são enviados ao frontend nem persistidos no histórico. A resposta normalizada mantém evidências públicas com origem, URL e data para auditoria do resultado exibido. Respostas completas de terceiros não são arquivadas nesta versão.

## Score e evidência

`Trend Score` é um índice *interno* de 0 a 100: atualidade até 25 pontos, diversidade de fontes/publicadores até 25, sinal de busca ou crescimento medido até 30, evidências de apoio até 20. `Brand Relevance` é outra inferência interna baseada em correspondência de termos com o contexto autorizado. Esses números não são métricas oficiais de Google, Pinterest ou YouTube. Não são preenchidos volumes, percentuais, engajamento, hashtags, competição ou duração estimada quando a fonte não os oferece.

Google Trends pode fornecer tráfego aproximado; Pinterest pode fornecer crescimento percentual e série relativa de interesse (0–100, não volume absoluto). O histórico local registra score e o valor observado disponível. A direção é calculada somente a partir de crescimento informado pelo Pinterest ou da comparação de duas observações de tráfego do Google; mudança isolada de score não é tratada como crescimento real. Os estados “Explodindo”, “Em alta”, “Crescendo” e “Emergente” são classificações internas. “Explodindo” exige crescimento medido, não apenas volume alto. Quando não há evidência suficiente, o Radar exibe estado vazio.

Assuntos são agrupados por tokens e sobreposição textual, inclusive entre fontes, com limiar conservador; assuntos de um único token relevante exigem correspondência da expressão completa para evitar associações espúrias. Isso **não** é equivalência semântica multilingue nem prova de propagação temporal entre redes. Até haver uma fonte aprovada e uma camada semântica validada, o Radar não afirma que um assunto “migrou” de uma rede para outra. Uma fonte isolada pode aparecer como tendência da própria plataforma, claramente identificada.

## Atualização, segurança e limites

Feeds são consultados em paralelo quando independentes. O cache de feed e de snapshot dura dez minutos; consultas simultâneas idênticas compartilham uma requisição. Uma atualização manual feita nos primeiros 30 segundos reutiliza o resultado para limitar pressão na API; falhas de feeds públicos são retidas por um minuto. A tela atualiza a cada dez minutos enquanto montada, e permite atualização manual. Isso não é um worker periódico independente da abertura da tela: para monitoramento 24/7, será necessário um job agendado por workspace com controle de quotas. A falha de uma fonte não derruba as demais; o painel “Fontes” expõe seu estado sem vazar credenciais ou corpo de erro sensível.

O limite da API e as permissões do Pinterest seguem a [documentação oficial](https://developer.pinterest.com/docs/reference/rate-limits/). Tokens ficam somente no backend. `RADAR_PINTEREST_ACCESS_TOKEN` deve ser concedido para Trends pelo Pinterest, não inferido de uma conexão social de usuário. Google News e RSS são públicos; qualquer substituição por API sujeita a contrato precisa de análise própria.

## Configuração e expansão

Opcionalmente configure `RADAR_PINTEREST_ACCESS_TOKEN` e/ou `YOUTUBE_API_KEY` no ambiente **do servidor**. Não publique estas variáveis com prefixo `VITE_`. Para produção, configure `SOCIAL_DATABASE_URL` conforme a infraestrutura existente; a ausência impede apenas a persistência histórica/salvos, e deve ser corrigida antes do lançamento. Não reutilize tokens de contas conectadas sem autorização e isolamento explícitos.

Para adicionar uma fonte, crie um provider independente que valide a licença/escopo, normalize apenas campos observados, forneça evidências e status de disponibilidade, implemente limites/retries apenas para erros transitórios e adicione testes de schema, erro, cache e isolamento. Integre-a ao orquestrador sem alterar Imagem, Vídeo ou Conexões. Não habilite uma rede com resultados de scraping, mock ou dados de outra plataforma rotulados como seus.

Ainda não há período personalizado pesquisável em provedores, estimativa de duração/competição sem métrica de origem, leitura de áudios/hashtags de redes sem acesso aprovado, deduplicação semântica multilíngue ou cronologia comprovada de propagação entre plataformas. Os filtros de 24h/7d/30d recortam os assuntos disponíveis no snapshot e nas tendências salvas; não consultam arquivo histórico de conteúdo completo. A linguagem segue a região disponível (pt-BR para Brasil, en-US para referência EUA), não um detector independente. Não se deve apresentar essas capacidades como disponíveis até haver dados e testes apropriados.

## Testes

`node --import tsx --test server/radar/radar.test.ts` cobre persistência, isolamento, normalização Pinterest, cache e retry/permissão. `npm run lint`, `npm test` e `npm run build` validam o projeto. Os testes usam respostas controladas para exercitar comportamento; **não** comprovam acesso real ao Pinterest. A validação live depende de token de Trends autorizado e quotas disponíveis.
