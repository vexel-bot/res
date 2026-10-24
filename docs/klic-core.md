# KLIC Core — integração operacional

Implementação incremental, sem redesenho da interface. O Core orquestra consultas e recomendações; os módulos existentes continuam donos dos dados e das ações. Imagem e Vídeo não são ferramentas do Core, não emitem eventos para ele e mantêm seus endpoints e executores anteriores.

## Arquitetura

`Módulo existente → /api/klic → sessão e permissões → contexto mínimo → registry/adaptador → serviço existente → resultado + rastreamento`

- `src/klic/contracts.ts`: contratos de contexto, fontes e escopo.
- `server/klic/context.ts`: seleção de domínios por intenção/origem, limites, allowlists e isolamento.
- `server/klic/core.ts`: registro de ferramentas, timeouts, eventos, recomendações e cache temporário de insights.
- `server/klic/adapters.ts`: adaptadores para governança, integrações, Radar e snapshots locais autorizados.
- `server/klic/recommendations.ts`: correlações determinísticas com evidências; separa associação de causalidade.
- `server/klic/store.ts`: persistência atômica de preferências consentidas, deduplicação de eventos e traces.
- `server/klic/router.ts`: fronteira HTTP autenticada, limites por usuário, geração de texto reutilizando o provedor atual, observação de eventos após commit.
- `src/klic/useKlicClient.ts`: ponte para os stores existentes, com descarte de respostas após troca de usuário, Workspace ou cliente.
- `src/klic/KlicOperationalBridge.tsx`: assinatura headless dos contextos operacionais, sem elementos visuais novos.

## Integrações efetivamente conectadas

O chat não relacionado a mídia, Radar (inclusive a superfície existente do Dashboard), análise solicitada pelo Analytics e sugestão de fluxo do construtor de Automações usam a mesma fronteira do Core. A geração de texto permanece no serviço Gemini já adotado pelo servidor, sem nova biblioteca de IA.

Marca, clientes, calendário e biblioteca fornecem metadados mínimos dos stores atuais. Imagens, vídeos, uploads, credenciais e tokens não entram nesse snapshot. Governança fornece aprovações, equipe e histórico autorizado diretamente do serviço. Contas conectadas fornece apenas plataforma e estado de conexão/configuração, nunca tokens.

O bridge emite revisões de contexto com debounce. Operações bem-sucedidas de aprovações/equipe e sincronização/desconexão observadas no servidor alimentam o bus após a resposta original ser concluída. Falhas de consumidores não interrompem a operação original. Eventos têm deduplicação por usuário + Workspace + cliente + revisão; não constituem uma fila durável com entrega garantida.

Recomendações de eventos ficam disponíveis por cinco minutos em `/insights`, isoladas também pelo módulo de origem. O cache contém somente o resultado derivado, sem registros brutos, tem limite de 200 entradas e revalida permissões na leitura. Ele é descartado ao reiniciar. Analytics e chat consultam diretamente o mesmo mecanismo de evidências; nenhum novo card, botão ou plasma foi adicionado.

## Dados, segurança e limites reais

1. A identidade vem da sessão do backend, não de IDs de usuário enviados pelo navegador. Workspace, cliente, origem e cada registro são conferidos antes da coleta. As permissões são verificadas novamente antes da resposta HTTP.
2. Os stores de conteúdo existentes são locais ao navegador e não possuem ACL de cliente validada no servidor. Por isso somente administradores podem fornecer esses snapshots. Eles são identificados como `browser-local`, nunca como confirmação de um provedor. Colaboradores não recebem acesso implícito aos dados locais ou a clientes sem ACL disponível.
3. Serviços que não fornecem vínculo com cliente não são misturados em consultas de um cliente específico. Dados ausentes são `unavailable`; uma coleção autorizada e vazia é `empty`. Não são preenchidos com mocks ou zeros.
4. Analytics fornece suas métricas pelo adaptador que reutiliza `metricValue`. Comparações exigem observações válidas e de mesma quantidade. Baseline zero não gera percentual inventado. A análise do Analytics usa escopo de Workspace porque suas fontes atuais não fornecem propriedade por cliente. Demonstração não é enviada à KLIC.
5. O serviço de integrações ainda não fornece séries reais de métricas em todas as conexões. Essa implementação não promete métricas que o serviço não retorna.
6. O construtor existente ainda não tem executor de automações conectado. `/automation-plan` produz uma configuração inativa para revisão usando seu parser atual. `automations.start` fica bloqueado: nenhum campo `confirmed: true` autoriza efeitos externos. Publicação, ativação e demais alterações continuam no módulo responsável e nas confirmações existentes.
7. Mensagens, histórico recente e documentos são entrada não confiável. O Core não transforma resposta do modelo em execução. No máximo seis mensagens anteriores são enviadas, com limite por mensagem, juntamente com os domínios relevantes e preferências consentidas.
8. Radar preserva regiões BR/GLOBAL e atualização manual. O cache do serviço inclui usuário, Workspace, cliente e fingerprint do contexto; o resultado do adaptador é reutilizado sem uma segunda consulta externa.
9. Consultas têm timeout e respostas degradadas explícitas. Os traces não guardam prompts, documentos, credenciais ou erros brutos do provedor. Preferências são salvas somente com consentimento explícito e podem ser apagadas.

## Contrato HTTP

Todas as rotas abaixo exigem sessão válida. POST usa `{ workspaceId, clientId: null | string, source }`, podendo incluir `context` no contrato `KlicEnvelope`. O backend recusa origens não permitidas e aplica limites por usuário. Não use estes endpoints como substitutos dos módulos de escrita.

| Rota sob `/api/klic` | Resultado |
| --- | --- |
| `POST /analyze` | Insight, recomendações, estados das fontes e traceId |
| `POST /insights` | Última análise temporária do mesmo escopo/origem, ou null |
| `POST /tools` | Catálogo autorizado; com `tool`, executa consulta registrada |
| `POST /chat` | Texto contextual, sugestões e estado degradado quando necessário |
| `POST /radar` | Snapshot do serviço Radar existente |
| `POST /automation-plan` | Fluxo validado, inativo, `requiresReview: true`, `executed: false` |
| `POST /events` | Recebimento/deduplicação de evento conhecido |
| `POST /memory` | Preferência `{ key, value, consent: true }` |
| `POST /memory/forget` | Remove a preferência pelo `key` no mesmo escopo |
| `GET /memory?workspaceId=…&clientId=…` | Preferências explícitas do usuário/contexto |
| `GET /traces?workspaceId=…&clientId=…` | Até 50 traces do usuário/contexto |

## Persistência e operação

`.clicko-data/klic.json` reutiliza `AtomicJsonStore`, com gravação atômica e validação ao carregar. Não pode estar em `public` ou `dist`. Limites: 2.000 traces, 1.000 preferências e 1.000 identificadores de eventos. Não há cópia persistente do histórico bruto da plataforma.

Como o backend atual, este repositório JSON é adequado a uma instância de servidor. Escala horizontal exige adaptar a persistência para um serviço transacional compartilhado e o bus para uma fila durável; não iniciar múltiplos processos escrevendo no mesmo arquivo. Gravações são síncronas e limitadas; monitorar latência e volume antes de aumentar a frequência de eventos.

O Core é inicializado sob demanda. Falha do armazenamento ou provedor retorna erro/degradação apenas nas consultas da KLIC. Não impede o carregamento das demais rotas da Clicko. Endpoints legados permanecem compatíveis para os fluxos fora desta migração; eles não recebem automaticamente as garantias da nova fronteira.

## Verificação

`npm run lint`, `npm test`, `npm run build`.

`server/klic/core.test.ts` cobre fronteira autenticada, isolamento entre usuários/Workspaces/clientes, exclusão de mídia, allowlists, indisponibilidade do provedor, persistência e remoção de preferência, eventos após commit, deduplicação, falha isolada de consumidor, cache de insights com revogação de acesso, comparação matemática e bloqueio de efeitos externos. Não depende de contas reais nem dispara publicações.

Validação ao vivo com provedores externos e executor de automações requer as respectivas credenciais/integrações reais. Nenhum resultado externo é simulado para apresentar essas capacidades como concluídas.
