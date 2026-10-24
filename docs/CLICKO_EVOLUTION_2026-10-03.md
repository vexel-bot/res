# Evolução integrada da Clicko — 03/10/2026

## Objetivo

Esta etapa consolidou a Clicko como uma operação de conteúdo orientada por contexto real, sem simular integrações externas. O trabalho priorizou robustez de recursos existentes: isolamento entre clientes, inteligência de marca, continuidade de contexto da KLIC, busca global, saúde operacional e notificações acionáveis.

## Diagnóstico anterior

- A memória de IA era persistida por workspace, mas não distinguia de forma explícita o cliente. Em um workspace com várias marcas, um cliente podia herdar contexto de outro.
- O perfil de cliente já armazenava dados estratégicos relevantes, porém somente parte deles chegava ao contexto da KLIC.
- A busca global apresentava exemplos estáticos em vez de consultar a operação visível ao usuário.
- O Dashboard tratava aprovações e conexões, mas não destacava falhas de publicação nem clientes ativos sem conteúdo futuro.
- A central de notificações mostrava apenas aprovações pendentes.
- A interface de inteligência de marca não deixava clara a cobertura do contexto nem expunha alguns campos já suportados pelo modelo de dados.

## Implementação realizada

### Inteligência de marca e isolamento

- A memória persistente recebeu vínculo opcional com `clientId`.
- Memórias antigas são migradas para o cliente ativo conhecido sem perder o conteúdo existente.
- A composição de contexto passou a respeitar simultaneamente workspace e cliente.
- Dados explícitos do perfil do cliente têm precedência sobre memórias aprendidas.
- A KLIC recebe somente o conjunto permitido de informações da marca: empresa, segmento, produtos, serviços, público, objetivos, posicionamento, identidade visual, cores, tipografia, referências, diferenciais, objeções, concorrentes, termos preferidos e restrições editoriais.
- O backend mantém uma lista explícita de campos aceitos; anexos brutos, tokens e segredos não fazem parte do contexto textual.
- Foi incluído teste automatizado que comprova que memórias do cliente Beta não aparecem no contexto do cliente Alpha.

### Perfil de cliente

- A seção `Marca` passou a se chamar `Inteligência da Marca`.
- A tela apresenta a cobertura percentual dos dados de marca e uma barra de progresso.
- Foram adicionados campos para posicionamento, concorrentes/referências, termos preferidos e assuntos/expressões proibidos.
- A interface informa que campos ausentes não serão inventados pela KLIC.
- Ações genéricas de conteúdo agora abrem a criação de texto, que está operacional, em vez de direcionar indevidamente para módulos sem provider ativo.

### KLIC

- Conversas que geram memória agora registram o cliente ativo.
- A revisão de contexto é calculada dentro do limite do cliente e não pelo histórico inteiro do workspace.
- Campanhas usam a revisão do contexto do respectivo cliente.
- O contrato frontend/backend foi ampliado para a inteligência de marca sem expor credenciais.

### Busca global e navegação

- A busca por `Ctrl+K`/`Cmd+K` foi ligada globalmente.
- Resultados estáticos foram removidos.
- A busca consulta clientes, campanhas, conteúdos e ativos reais que já passaram pelo escopo de permissão do usuário.
- Ao abrir um resultado, o cliente e a campanha correspondentes são selecionados antes da navegação.
- A busca possui navegação por teclado, estado vazio e atalhos limitados aos módulos acessíveis.

### Saúde operacional do Dashboard

- O bloco de atenção passou a representar `Saúde da operação`.
- Falhas de publicação são tratadas como críticas.
- Conexões com problema e aprovações pendentes continuam visíveis.
- Clientes ativos sem conteúdo futuro agendado são sinalizados.
- Nenhum indicador arbitrário ou dado de provider é fabricado.

### Notificações

- A central passou a consolidar eventos reais e autorizados do workspace.
- Ordem de prioridade: falhas de publicação, problemas de conexão, aprovações pendentes e agenda do dia.
- Cada notificação abre diretamente o módulo responsável.
- O contador considera apenas eventos que exigem ação; itens meramente informativos não inflam o alerta.
- O estado vazio agora informa que a operação está em dia.

### Desempenho de carregamento

- As telas operacionais pesadas passaram a ser carregadas por rota com `React.lazy` e `Suspense`.
- O mini chat e a ponte operacional da KLIC também são carregados sob demanda.
- Imagem e Vídeo mantiveram seus componentes e comportamentos atuais.
- O JavaScript inicial minificado caiu de aproximadamente 1,1 MB para 414 kB; o build deixou de emitir o alerta de chunk acima de 500 kB.

## Integrações preservadas

- Autenticação, contas pessoais, workspaces, permissões e escopos existentes foram preservados.
- Conexões sociais continuam independentes por provider e descritas em `docs/SOCIAL-INTEGRATIONS.md`.
- A KLIC continua usando seu contrato real de backend descrito em `docs/klic-core.md`.
- A preferência de tema e o sistema visual claro/escuro não foram substituídos.
- Os módulos Imagem e Vídeo continuam intencionalmente com a mensagem `em construção`; esta etapa não apresentou geração simulada nem alterou providers desses módulos.

## Variáveis e serviços externos

Somente nomes são documentados. Valores reais devem permanecer fora do repositório e do frontend.

- KLIC: `GEMINI_API_KEY`, `KLIC_CHAT_MODEL`, `GOOGLE_GENAI_USE_VERTEXAI`, `KLIC_GOOGLE_TTS_ENABLED`, `KLIC_TRANSCRIPTION_MODEL`.
- Google/YouTube: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_CLOUD_PROJECT`.
- Meta, TikTok, LinkedIn, Threads, Pinterest e X: credenciais e redirect URIs específicas listadas no `.env.example` e em `docs/SOCIAL-INTEGRATIONS.md`.
- Segurança social: `SOCIAL_STORAGE_DRIVER`, `SOCIAL_TOKEN_ENCRYPTION_KEY`, `SOCIAL_ALLOW_SINGLE_INSTANCE_STORE`.
- Aplicação: `APP_URL` e controles de autenticação de desenvolvimento documentados no `.env.example`.

## Validação executada

- TypeScript: `npm run lint`.
- Testes automatizados: `npm test`, incluindo o novo isolamento de contexto por cliente.
- Build de frontend, servidor e worker: `npm run build`.
- Navegador: 14 cenários Playwright pós-otimização passaram, cobrindo temas claro/escuro, rotas, responsividade, KLIC, conexões, Radar, Clientes, Jornadas, Dashboard, aprovações e estados vazios.
- Um teste legado isolado de Imagem/Vídeo ainda espera o fundo antigo `rgb(5, 5, 5)` no menu lateral, enquanto o tema atual usa `rgb(0, 0, 0)`. A interface não foi alterada nesta etapa para satisfazer uma expectativa antiga de um módulo fora do escopo.

## Limites reais e próximos passos

Estes itens continuam dependentes de implementação adicional ou configuração externa e não foram apresentados como concluídos:

- Imagem e Vídeo: telas em construção, sem geração falsa.
- Jornadas/Automações: configuração e validação existem; o executor transacional completo ainda precisa ser conectado antes de ativar rotinas reais.
- Inbox omnichannel, benchmark contínuo de concorrentes, mídia paga, relatórios exportáveis e link-in-bio: requerem contratos de dados e/ou APIs próprias.
- Analytics e publicação real: disponibilidade depende dos providers, permissões, tokens, webhooks e revisão dos aplicativos externos.
- Performance: estabelecer orçamento de bundle e acompanhar regressões de tamanho por release.
- Produção: executar o checklist de credenciais, webhooks, armazenamento persistente, rate limiting, observabilidade e rotação de segredos.

## Critério de verdade adotado

Uma capacidade só aparece como operacional quando há dados reais ou persistidos, permissão válida e contrato funcional. Ausência de provider, credencial, escopo ou dado retorna estado indisponível/configuração necessária; não é convertida em sucesso por mock ou fallback local.
