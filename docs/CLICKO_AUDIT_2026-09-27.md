# Auditoria funcional e técnica da Clicko

**Data:** 27 de setembro de 2026  
**Ambiente auditado:** desenvolvimento local (`http://127.0.0.1:3000`)  
**Resultado:** aplicação compilando, lint aprovado e 104 testes automatizados aprovados.

## 1. Escopo e método

A auditoria cobriu navegação, segurança, permissões, isolamento por ambiente, integrações sociais, KLIC, fluxos operacionais, temas e responsividade. A validação combinou:

- leitura das rotas e serviços de frontend e backend;
- análise de permissões e dependências entre módulos;
- testes automatizados do projeto;
- compilação de produção;
- inspeção funcional no navegador em desktop e viewport móvel;
- verificação dos temas claro e escuro;
- inspeção de estados de integração e prontidão do backend.

As áreas **Imagem** e **Vídeo** foram tratadas como módulos protegidos. Nenhum ajuste, refatoração ou redesign foi realizado em seus componentes ou fluxos internos nesta execução.

## 2. Telas e áreas revisadas

Foram abertas e verificadas as seguintes rotas do sistema interno:

- Dashboard;
- KLIC AI;
- Conexões / Contas conectadas;
- Clientes;
- Estratégia;
- Biblioteca;
- Calendário;
- Analytics;
- Automações;
- Aprovações;
- Equipe;
- Criação textual;
- Configurações;
- Plano e assinatura.

Também foram revisados por testes os fluxos de cadastro, verificação de e-mail, login, logout, recuperação de senha, troca de ambiente, perfis pessoal e corporativo, licenças, limites de plano, permissões e isolamento entre tenants.

## 3. Problemas encontrados e corrigidos

### 3.1 Conexões dependiam indevidamente da licença da KLIC

O serviço de Conexões consultava o tipo de conta por uma função que também exigia acesso ao módulo `ai-chat`. Isso fazia uma integração social legítima poder falhar apenas porque o usuário não possuía acesso à KLIC.

**Correção:** a leitura do tipo de ambiente foi separada da autorização da KLIC. Conexões agora depende somente das regras e permissões próprias do módulo.

### 3.2 Rotas de status e sincronização sem autorização específica

As rotas de status e sincronização de providers estavam autenticadas, mas não exigiam explicitamente as permissões funcionais adequadas.

**Correção:**

- consulta de status exige `connections.read`;
- sincronização exige `connections.manage`;
- testes foram adicionados para membros com acesso restrito;
- o frontend oculta ações de escrita de usuários com acesso somente de leitura.

### 3.3 Ações de IA textual sem governança granular

Algumas rotas legadas de criação textual, estratégia, calendário e analytics não aplicavam de forma uniforme módulo, permissão e tenant antes de chamar o provider.

**Correção:** as rotas auditadas agora exigem autenticação e as capacidades correspondentes:

- campanhas e briefing: estratégia + criação de conteúdo;
- calendário: calendário + criação de conteúdo;
- copy e matriz criativa: criação textual + criação de conteúdo;
- análise de métricas: analytics + leitura de analytics.

### 3.4 Respostas locais simuladas como se fossem respostas da IA

Algumas rotas retornavam conteúdo fabricado localmente quando o provider não estava configurado ou falhava. Isso podia apresentar uma operação como bem-sucedida sem ter ocorrido geração real.

**Correção:** os falsos sucessos foram removidos das rotas textuais auditadas. Falhas do provider agora retornam erro explícito e sanitizado, com código, possibilidade de retry e `requestId`, sem expor credenciais. A análise sem dados reais continua retornando um estado honesto de indisponibilidade, sem fabricar métricas.

### 3.5 Falha silenciosa na criação textual

A interface de criação textual apenas registrava parte dos erros no console.

**Correção:** o erro agora é apresentado de forma clara na própria tela e é removido quando uma nova tentativa começa.

### 3.6 Interface de Conexões incompatível com permissões de leitura

Usuários com `connections.read`, mas sem `connections.manage`, ainda visualizavam ações de conectar, sincronizar, testar ou desconectar.

**Correção:** a interface agora apresenta o estado “Somente leitura” e não oferece ações que o backend rejeitaria.

## 4. Validações funcionais realizadas

### Autenticação e sessão

- cadastro e validações de dados;
- consentimento legal;
- verificação de e-mail;
- login e logout;
- recuperação e redefinição de senha;
- persistência e expiração de sessão;
- foto de perfil e persistência após novo login.

### Governança e isolamento

- separação entre perfil pessoal e workspace corporativo;
- isolamento de tenant;
- papéis e permissões;
- escopos de clientes, contas sociais, projetos e recursos;
- transferência de titularidade;
- convites, assentos e licenças;
- bloqueios por capacidade e consumo;
- complementos de plano e entitlements.

### Assinatura e cobrança

- catálogo de planos;
- ativação idempotente por evento assinado;
- bloqueio de acesso conforme status da assinatura;
- limites e consumo;
- proteção contra duplicação de eventos.

Não foi concluída uma transação financeira real, pois isso exige confirmação externa do provedor de pagamento e ação do titular. O contrato interno, a assinatura de webhook e os gates de acesso foram validados por testes.

### Integrações sociais

- estado dos oito providers;
- tokens armazenados de forma protegida;
- refresh, revogação e reconexão;
- seleção de páginas, canais, organizações e boards;
- múltiplas conexões quando suportadas;
- sincronização;
- publicação, agendamento e idempotência;
- analytics social;
- isolamento por workspace e permissões.

O seletor exibiu corretamente o estado atual:

| Provider | Estado observado |
|---|---|
| Instagram | Disponível para conectar |
| Facebook | Disponível para conectar |
| TikTok | Configuração necessária |
| YouTube | Conectada; permite adicionar outra |
| LinkedIn | Configuração necessária |
| Threads | Configuração necessária |
| Pinterest | Configuração necessária |
| X | Disponível para conectar |

Não foi iniciado OAuth externo durante a auditoria, pois a conclusão depende da autorização interativa da conta de cada rede.

### KLIC

- autenticação e isolamento de conversas;
- persistência de conversa e contexto;
- anexos;
- sanitização de erros do provider;
- retry transitório para `503` e `429`;
- voz e transcrição;
- temporização do balão;
- integração do mini chat;
- controle de acesso por módulo.

O provider está configurado como Developer API, com o modelo definido no ambiente. Nenhuma credencial foi lida, exibida ou registrada nesta auditoria. Não foi enviada uma geração real nesta rodada; a fronteira do provider e os comportamentos de erro/retry foram validados pelos testes existentes.

## 5. Interface, temas e responsividade

As principais rotas foram verificadas em desktop e em viewport móvel de `390 × 844`, nos temas claro e escuro.

Resultados:

- nenhum overflow horizontal global nas telas verificadas;
- nenhuma imagem quebrada detectada;
- nenhum ID duplicado detectado;
- nenhum botão vazio sem nome acessível detectado;
- nenhum erro ou warning de aplicação observado no console durante a navegação;
- tema claro sem combinações diretas de texto branco sobre fundo branco ou texto preto sobre fundo preto;
- tema escuro restaurado ao final da inspeção;
- azul `#6EB8F5` localizado apenas em contextos da KLIC/Plasma;
- controles horizontais do Calendário e da Criação móvel permaneceram dentro de trilhas intencionais, sem cortar a página inteira.

Uma varredura estática dos botões fora de Imagem e Vídeo encontrou apenas:

- botões de submit dos formulários de autenticação, corretamente acionados pelo formulário;
- “Atualizar senha”, corretamente desabilitado enquanto a integração específica não está disponível.

## 6. Prontidão do backend

Após as correções, o servidor foi reiniciado e respondeu:

- `/api/health`: `ok`;
- `/api/ready`: `ready`;
- armazenamento social local: `json`;
- Gemini/KLIC: configurada;
- e-mail transacional: não configurado.

O armazenamento JSON é adequado ao ambiente local atual. A configuração de produção deve utilizar PostgreSQL, requisito que já é validado pelo projeto.

## 7. Testes e qualidade

| Verificação | Resultado |
|---|---|
| `npm run lint` | Aprovado |
| `npm test` | 104 testes aprovados; 0 falhas |
| `npm run build` | Aprovado |
| `git diff --check` | Aprovado; apenas avisos de conversão LF/CRLF do Git |

O build emitiu um aviso de bundle JavaScript acima de 500 kB: aproximadamente **1.066,52 kB**, ou **302,83 kB gzip**. Não foi feito code splitting nesta execução porque uma reorganização global de imports poderia impactar indiretamente os módulos protegidos.

## 8. Arquivos alterados nesta auditoria

- `server/integrations.ts` — autorização das operações sociais e desacoplamento da KLIC;
- `server/governance.ts` — leitura centralizada e independente do tipo de ambiente;
- `server/integrations.test.ts` — cobertura de permissões de leitura e gestão;
- `server.ts` — governança de rotas textuais, provider configurado, retry centralizado e remoção de falsos sucessos;
- `src/components/ConnectedAccountsView.tsx` — ações condicionadas à permissão de gestão;
- `src/components/CreationStudioView.tsx` — feedback visível de falha na geração textual;
- `docs/CLICKO_AUDIT_2026-09-27.md` — este relatório.

O worktree já possuía diversas alterações anteriores. Elas foram preservadas e não foram revertidas nem absorvidas como parte das correções desta auditoria.

## 9. Pendências reais e dependências externas

1. **Credenciais sociais:** TikTok, LinkedIn, Threads e Pinterest ainda precisam de configuração válida no servidor.
2. **OAuth real:** cada provider deve ser homologado com uma conta real, incluindo callback, escopos aprovados, seleção de ativos, refresh e revogação no ambiente de destino.
3. **E-mail transacional:** serviço ainda não configurado; notificações por e-mail dependem desse provider.
4. **Segurança avançada da conta:** alteração de senha autenticada, 2FA e gerenciamento detalhado de sessões permanecem identificados na própria interface como integrações pendentes. O fluxo de recuperação de senha está coberto.
5. **Pagamento real:** checkout e liquidação financeira ainda exigem homologação com o provider e uma operação autorizada pelo titular.
6. **Persistência de produção:** PostgreSQL deve estar configurado no deploy. O backend impede o uso da configuração local inadequada em produção.
7. **Estado operacional no navegador:** parte do contexto de clientes, campanhas e biblioteca ainda usa persistência local/seed de inicialização. Antes de prometer durabilidade multi-dispositivo, esses dados devem migrar para armazenamento transacional no servidor.
8. **Performance:** o bundle principal deve ser dividido futuramente, com uma estratégia que preserve o carregamento e não altere Imagem ou Vídeo.
9. **Testes manuais de autenticação:** não foi encerrada a sessão ativa do navegador durante esta inspeção. Os fluxos completos foram validados pela suíte automatizada.

## 10. Confirmação dos módulos protegidos

- A opção **Imagem não foi modificada nesta auditoria**.
- A opção **Vídeo não foi modificada nesta auditoria**.
- Nenhuma funcionalidade interna dessas áreas foi alterada.
- Nenhum redesign foi realizado nessas áreas.
- Nenhuma integração específica dessas áreas foi substituída.
- As correções aplicadas ao restante do sistema não introduziram falhas detectáveis em Imagem ou Vídeo: lint, build e suíte completa permaneceram aprovados, e a navegação para ambas continuou disponível.

## 11. Conclusão

A Clicko está operacional no ambiente local e passou nas verificações automatizadas e visuais executadas. As correções desta auditoria eliminaram uma dependência indevida entre Conexões e KLIC, reforçaram autorização e permissões, impediram falsos resultados de IA e alinharam o frontend aos controles do backend. As pendências restantes são principalmente integrações externas, infraestrutura de produção, persistência multi-dispositivo e otimização de bundle; elas não foram mascaradas como concluídas.
