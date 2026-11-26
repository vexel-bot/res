# Mapa do produto

A Clicko reúne contexto de marca, planejamento, criação de conteúdo e acompanhamento da operação. Consulte o estado de cada entrega no [[Roadmap]].

| Área | O que faz | Onde começar |
|---|---|---|
| Dashboard e navegação | Apresenta a operação e o acesso às áreas por conta | [Sidebar](https://github.com/vexel-bot/res/blob/main/src/components/Sidebar.tsx) |
| Studios | Mantém briefing, materiais, entregas e revisão de imagem, publicidade e vídeo | [Ponte dos Studios](https://github.com/vexel-bot/res/blob/main/server/studios/proxy.ts) · [[Estúdio de Vídeo]] |
| KLIC | Apoia o trabalho com o contexto autorizado da conta | [Arquitetura da KLIC](https://github.com/vexel-bot/res/blob/main/docs/klic-central-architecture.md) |
| Clientes, equipe e permissões | Define identidade, acesso e contexto de trabalho | [Governança](https://github.com/vexel-bot/res/blob/main/server/governance.ts) |
| Biblioteca | Organiza materiais e disponibiliza mídia do Studio de acordo com as permissões | [API de arquivos](https://github.com/vexel-bot/res/blob/main/backend/app/routers/assets.py) |
| Calendário, aprovações, conexões e analytics | Organiza a operação, a revisão e as integrações | [Mapa central da Clicko](https://github.com/vexel-bot/res/blob/main/docs/evolution/2026-10-29-documentacao-sistema.md) |
| Evolução | Expõe o catálogo de registros pela aplicação | [Catálogo versionado](https://github.com/vexel-bot/res/blob/main/docs/evolution/catalog.json) |

## Como o código se conecta

O frontend React apresenta a navegação e os formulários. O servidor Express resolve a sessão e o contexto da conta. Para os Studios, encaminha as operações ao FastAPI pela ponte autenticada. A API guarda projetos e trabalhos. Os workers executam as tarefas de mídia, e o armazenamento entrega os arquivos ao usuário autorizado.

O [mapa central da Clicko](https://github.com/vexel-bot/res/blob/main/docs/evolution/2026-10-29-documentacao-sistema.md) é uma referência histórica de 29/10/2026. Para a montagem de vídeo após a migração de novembro, consulte [[Estúdio de Vídeo]].
