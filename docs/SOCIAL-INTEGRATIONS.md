# Integrações sociais da Clicko

Auditoria técnica atualizada em **20/09/2026**. Este documento não contém IDs, secrets, tokens ou credenciais reais.

## Estado técnico verificado

| Plataforma | OAuth | Conexão | Publicação | Analytics | Dependência externa |
|---|---|---|---|---|---|
| Instagram | Implementado, não testado com conta real | Páginas e contas profissionais | Imagem, carrossel, Reel/vídeo e Story | Permissão reconhecida; coletor incremental pendente | App Meta, conta profissional e revisão de permissões |
| Facebook | Implementado, não testado com conta real | Páginas administradas | Texto, imagem e vídeo por URL | Permissão reconhecida; coletor incremental pendente | App Meta e revisão de permissões |
| TikTok | Implementado, não testado com conta real | Perfil | Direct Post de vídeo por URL | Não implementado | Login Kit, Content Posting API, auditoria e domínio HTTPS verificado |
| YouTube | OAuth real concluído em ambiente de desenvolvimento | Canal descoberto por usuário; persistência cifrada confirmada após reinício | Não anunciado: upload resumível não está implementado | Snapshot oficial de estatísticas do canal | Para uso público, possível verificação Google |
| LinkedIn | Implementado, não testado com conta real | Perfil; organizações quando aprovadas | Texto; mídia somente com asset previamente registrado | Permissão reconhecida; coletor pendente | Produtos/permissões Community Management para organizações |
| Threads | Implementado, não testado com conta real | Perfil | Texto, imagem e vídeo | Permissão reconhecida; coletor pendente | App Threads dedicado e revisão de permissões |
| Pinterest | Implementado, não testado com conta real | Conta e boards | Pin de imagem por URL | Permissão reconhecida; coletor pendente | Conta Business, app e access tier aprovado |
| X | OAuth 2.0 PKCE real concluído em desenvolvimento | Perfil descoberto por usuário; persistência cifrada confirmada após reinício | Texto implementado; mídia somente com IDs previamente enviados | Snapshot oficial de métricas públicas do perfil | Plano/API compatível continua necessário para operações pagas ou limitadas |

Nenhuma integração deve ser classificada como funcionando de ponta a ponta até concluir OAuth com credenciais reais, persistir a conexão, reiniciar o servidor e repetir leitura/publicação/desconexão em uma conta de teste autorizada.

Contas usadas durante desenvolvimento são dados de um owner de teste, nunca configuração do produto. Não existe fallback por nome, e-mail, username, workspace, página ou token. Um novo assinante começa sem conexões e só recebe conexões criadas por seu próprio consentimento OAuth no contexto pessoal/workspace autenticado.

## Resultado da auditoria dos consoles

- Projeto Google Cloud confirmado: `clicko-studios` / “Clicko Studios”.
- **YouTube Data API v3 ativada** em 19/09/2026.
- Google Auth Platform configurada como app externo em modo de teste; cliente OAuth Web criado, callback local cadastrado e somente `youtube.readonly` selecionado.
- Uma primeira autorização do YouTube retornou zero canais e foi recusada corretamente com `SOCIAL_PERMISSION_INSUFFICIENT`. Depois de existir um canal na conta autorizada, uma nova autorização persistiu a conexão; o teste oficial de perfil passou antes e depois do reinício do backend.
- Meta for Developers está autenticado e a verificação por SMS foi concluída em 20/09/2026. O portal está na etapa final de perfil (“Sobre você”); concluir a inscrição ainda depende da confirmação explícita do titular.
- TikTok for Developers está autenticado, porém o portal de apps não conclui o carregamento enquanto a verificação da conta permanece pendente; o frontend do próprio portal também registrou erro de renderização.
- LinkedIn Developers está autenticado, mas a criação da Página Clicko foi bloqueada pelo próprio LinkedIn porque o perfil ainda não possui conexões suficientes. Sem uma Página elegível, o portal não permite criar o aplicativo.
- Pinterest está autenticado em conta pessoal verificada; o portal exige conta Business para criar a conta de desenvolvedor e aceitar os termos.
- A conta Developer do X foi criada em 20/09/2026. O app padrão está configurado como cliente confidencial Web, com permissão de leitura/escrita, callback local e credenciais OAuth geradas. ID e secret foram importados sem exposição para o `.env` ignorado. O OAuth real de uma conta de teste passou antes e depois do reinício do backend.
- Credenciais reais do Google e do X foram armazenadas somente no `.env` ignorado. Os demais IDs/secrets continuam ausentes porque os portais ainda dependem das etapas externas acima.

### Inventário de infraestrutura em 20/09/2026

- O projeto Google Cloud configurado é `clicko-studios`.
- YouTube Data API v3, Vertex AI e Text-to-Speech estão habilitados.
- Não há serviço Cloud Run, instância Cloud SQL, zona Cloud DNS ou secret cadastrado no Secret Manager desse projeto.
- Cloud Run API, Cloud SQL Admin API e Secret Manager API ainda estão desabilitadas.
- O ambiente local não define `PUBLIC_APP_URL`, PostgreSQL de produção nem domínio HTTPS; por isso `npm run validate:production` falha intencionalmente e impede que a configuração local seja tratada como produção.
- Provisionar banco, hospedagem, DNS ou tier pago requer a escolha oficial de infraestrutura e confirmação de custo. O código e o `Dockerfile` estão preparados, mas nenhum recurso comercial foi criado automaticamente.

## Arquitetura SaaS

O módulo existente de **Conexões** usa adapters independentes em `server/integrations/providers` e o contrato `SocialProvider`. O frontend inicia OAuth e apresenta estados, contas, recursos e capabilities. Authorization codes, client secrets, access tokens e refresh tokens permanecem no backend. O assinante nunca informa credenciais de desenvolvedor: os aplicativos oficiais e seus secrets pertencem à Clicko.

- `personal`: owner isolado pelo contexto pessoal autenticado.
- `workspace`: owner isolado pelo workspace; `actorId` registra quem vinculou/administrou a conta.
- operações administrativas exigem papel privilegiado no backend; headers enviados pelo navegador não definem identidade em runtime.
- unicidade: `ownerType + ownerId + clientId + provider + providerAccountId`.
- um mesmo recurso pode ser conectado a owners distintos somente após OAuth válido em cada contexto; nunca é herdado.

### Persistência

- Desenvolvimento/testes: adapter JSON atômico (`SOCIAL_STORAGE_DRIVER=json`) em `.clicko-data/social-integrations.json` ou `CLICKO_SOCIAL_DATA_FILE`. O servidor recusa caminhos em `public` ou `dist`.
- Produção: adapter PostgreSQL transacional (`SOCIAL_STORAGE_DRIVER=postgres`, `SOCIAL_DATABASE_URL`). As tabelas, índices, chaves únicas e registros de auditoria são inicializados de forma idempotente.
- Em `NODE_ENV=production`, o driver padrão é PostgreSQL. O JSON só inicia com o override explícito `SOCIAL_ALLOW_SINGLE_INSTANCE_STORE=true`, destinado a contingência single-instance e não ao SaaS horizontal.
- A camada HTTP depende de `SocialIntegrationRepositoryPort`, portanto outro banco transacional pode ser injetado sem alterar providers ou frontend.

### Segurança verificada

- Sessão Clicko e autorização administrativa do owner ativo para operações sensíveis.
- Owner isolado como `personal` ou `workspace`.
- `state` OAuth aleatório de 256 bits, armazenado apenas como hash, válido por 10 minutos e consumido uma vez.
- cookie de transação HTTP-only, `SameSite=Lax`, limitado ao callback e vinculado ao mesmo navegador que iniciou o OAuth; impede login CSRF/account linking por callback roubado.
- provider, owner, actor, redirect e retorno são recuperados do estado server-side; o callback não confia em IDs fornecidos pelo navegador.
- quando o provider devolve vários recursos, tokens permanecem cifrados em uma seleção temporária de uso único; somente os IDs escolhidos pelo usuário viram conexões.
- PKCE S256 em YouTube e X.
- Tokens cifrados com AES-256-GCM autenticado; chave de 32 bytes somente no backend. Payloads v2 carregam um identificador não secreto da chave e suportam chaves anteriores durante rotação.
- Tokens, secrets, metadata privada e IDs internos do owner não são retornados ao frontend.
- Timeout externo e até três tentativas apenas para leituras idempotentes em 408, 429 e 5xx.
- Publicações não são repetidas implicitamente e exigem `Idempotency-Key`.
- Logs expõem apenas requestId, código público e status sanitizado.
- `.env`, `.clicko-data`, chaves privadas, PEMs e nomes comuns de JSON de credenciais estão ignorados pelo Git.

## Ambiente local

Execute uma vez, sem imprimir a chave gerada:

```powershell
node scripts/configure-social-env.mjs http://localhost:3000
```

O script configura somente valores determináveis localmente: `APP_URL`, uma chave criptográfica quando ausente e os callbacks. Ele não inventa nem cria credenciais de provedores.

Callback único do backend:

```text
http://localhost:3000/api/integrations/oauth/callback
```

Todas as redirect URIs cadastradas nos provedores precisam coincidir byte a byte com a variável correspondente. Em produção, use o domínio HTTPS real, sem inventar domínio, e repita o mesmo caminho `/api/integrations/oauth/callback`.

## Preparação de produção

- O guia operacional está em `docs/deployment/PRODUCTION.md`.
- `npm run validate:production` valida fail-closed de URL pública, PostgreSQL/TLS, chave de tokens e callbacks configurados sem imprimir valores.
- `npm run migrate:social` aplica a migration transacional e idempotente `server/integrations/migrations/001_social_integrations.sql`.
- `/api/health` é liveness; `/api/ready` confirma inicialização e conectividade do repositório social.
- O `Dockerfile` é multi-stage, executa como usuário sem privilégios e não copia `.env`, dados locais ou arquivos de credenciais.
- As páginas públicas para revisão ficam em `/about`, `/privacy`, `/terms`, `/data-deletion`, `/support` e `/integrations`.
- O material de preparação dos portais está em `docs/app-reviews/`; campos empresariais, domínio e contatos só podem ser preenchidos com informação oficial confirmada.

## Variáveis do servidor

Nunca use prefixo `VITE_` para estes valores.

- Persistência: `SOCIAL_STORAGE_DRIVER`, `SOCIAL_DATABASE_URL`, `SOCIAL_DATABASE_SSL`, `SOCIAL_TOKEN_ENCRYPTION_KEY`; opcionais `SOCIAL_TOKEN_ENCRYPTION_PREVIOUS_KEYS`, `CLICKO_SOCIAL_DATA_FILE` (somente JSON), `SOCIAL_ALLOW_SINGLE_INSTANCE_STORE` (contingência)
- Meta: `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI`, opcional `META_GRAPH_VERSION`
- TikTok: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- YouTube: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- LinkedIn: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`; opcionais `LINKEDIN_SCOPES`, `LINKEDIN_API_VERSION`
- Threads: `THREADS_APP_ID`, `THREADS_APP_SECRET`, `THREADS_REDIRECT_URI`; opcionais `THREADS_SCOPES`, `THREADS_GRAPH_VERSION`
- Pinterest: `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`, `PINTEREST_REDIRECT_URI`; opcional `PINTEREST_SCOPES`
- X: `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_REDIRECT_URI`; opcional `X_SCOPES`

O provider só fica `ready` quando ID, secret, redirect URI e chave de criptografia são válidos.

## Scopes e APIs usados

### Meta — Facebook e Instagram

- Facebook: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_engagement`.
- Instagram: `pages_show_list`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`.
- APIs: Facebook Login e Graph API. O backend troca o code por token de usuário e o converte em token de longa duração antes de derivar tokens de Página/Instagram.
- Instagram exige conta profissional associada a Página quando requerido pela API.

### YouTube

- Scope atual: `https://www.googleapis.com/auth/youtube.readonly`.
- API usada: YouTube Data API v3 (`channels.list`) para perfil e snapshot de `statistics`.
- O escopo de upload não é solicitado porque o pipeline binário/resumível não existe. O produto não anuncia capability de upload.
- YouTube Analytics API/Reporting API não são necessárias para o snapshot atual; só devem ser ativadas quando existir um coletor que realmente as consuma.

### TikTok

- Scopes: `user.info.basic`, `video.list`, `video.publish`.
- APIs: Login Kit, Display API e Content Posting API.
- Antes do Direct Post, o backend chama `creator_info/query`, valida a privacidade permitida para a conta e só então inicia o envio.
- O padrão conservador é `SELF_ONLY`. Visibilidade pública, URLs PULL_FROM_URL e publicação de clientes não auditados seguem as regras do TikTok; o domínio/prefixo de mídia precisa ser verificado.
- Photo Posting não é anunciado até existir adapter próprio e aprovação correspondente.

### LinkedIn

- Padrão: `openid profile email w_member_social`.
- API: OIDC `userinfo` e Posts API versionada.
- Scopes de organização (`rw_organization_admin` e os scopes versionados de feed/leitura/escrita liberados pelo Community Management) só devem ser adicionados após aprovação do produto correspondente. O adapter reconhece tanto os nomes legados quanto `r_organization_social_feed`/`w_organization_social_feed`; use somente o conjunto exibido no portal aprovado.
- Mídia/documentos exigem um asset oficial previamente registrado; este módulo não simula upload.

### Threads

- Padrão: `threads_basic`, `threads_content_publish`, `threads_manage_insights`, `threads_read_replies`, `threads_manage_replies`.
- Usa app e credenciais próprias do Threads, troca para token de longa duração e usa refresh oficial.

### Pinterest

- Scopes: `user_accounts:read`, `boards:read`, `pins:read`, `pins:write`.
- API v5: conta, boards, pins e token refresh.
- O parâmetro legado `continuous_refresh` não é enviado; aplicativos novos usam o comportamento de refresh atual do Pinterest.

### X

- Scopes padrão: `tweet.read tweet.write users.read offline.access`. `media.write` só deve ser adicionado quando o pipeline oficial de upload de mídia estiver implementado e habilitado.
- OAuth 2.0 Authorization Code com PKCE S256.
- Perfil e métricas públicas usam API v2. Publicação de mídia exige IDs de mídia já enviados pelo pipeline oficial e depende do plano contratado.

## Endpoints Clicko

- `GET /api/integrations/providers`
- `GET /api/integrations/connections`
- `GET /api/integrations/connections/:connectionId/analytics?from=AAAA-MM-DD&to=AAAA-MM-DD`
- `POST /api/integrations/:provider/authorize`
- `GET /api/integrations/oauth/callback`
- `GET /api/integrations/oauth/selections/:selectionToken`
- `POST /api/integrations/oauth/selections/:selectionToken`
- `GET /api/integrations/:provider/status`
- `GET /api/integrations/:provider/resources`
- `POST /api/integrations/:provider/test`
- `POST /api/integrations/:provider/refresh`
- `POST /api/integrations/:provider/sync`
- `POST /api/integrations/:provider/disconnect`
- `POST /api/integrations/connections/:connectionId/publish` com `Idempotency-Key`

## Agendamento, mídia e webhooks

Não existe executor durável de agendamento social. O backend rejeita datas futuras com erro explícito; não depende da interface aberta nem finge execução.

Os providers consomem URLs HTTPS ou IDs de assets já produzidos. Eles não alteram Imagem, Vídeo ou Creation Studio. Upload resumível YouTube, upload de assets LinkedIn e upload de mídia X permanecem etapas futuras de backend.

`integrations/webhooks.ts` valida HMAC do corpo bruto e challenge em tempo constante. Uma rota de webhook só pode ser montada com `express.raw()` **antes** do parser JSON, com secret e algoritmo oficiais, validação de timestamp/event ID e persistência anti-replay. O helper não expõe endpoint genérico nem aceita JSON reconstruído como evento confiável.

## Roteiro de teste real por provider

1. Criar/configurar aplicativo no portal oficial e cadastrar o callback exato.
2. Guardar ID e secret no secret manager ou `.env` local ignorado.
3. Iniciar o servidor e confirmar provider `ready`.
4. Conectar e autorizar a conta de teste.
5. Confirmar retorno, persistência cifrada e ausência de tokens na resposta/log.
6. Reiniciar o servidor e confirmar a persistência.
7. Listar páginas/canais/boards/organizações e validar capabilities concedidas.
8. Testar somente formatos oficialmente aprovados, com conteúdo de teste e idempotency key.
9. Validar Analytics disponível e ausência explícita do que não é coletado.
10. Desconectar, confirmar revogação quando suportada e reconectar.
11. Simular token expirado, permissão insuficiente, 429 e erro 5xx.

## Checklist exato de produção nos portais

Comum a todos: publicar Política de Privacidade e Termos da Clicko em HTTPS; verificar o domínio; cadastrar exatamente `https://DOMINIO-CLICKO/api/integrations/oauth/callback`; guardar ID/secret no Secret Manager; habilitar somente os produtos/scopes usados; preparar conta de revisão e vídeo do fluxo; configurar contatos de segurança; concluir revisão antes de remover o modo de teste.

- **Meta / Facebook / Instagram:** criar app Business oficial Clicko; associar e verificar o negócio/domínio; adicionar Facebook Login e os produtos Instagram necessários; cadastrar callback; solicitar `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_engagement`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights` e `instagram_manage_comments` somente conforme as funcionalidades demonstradas; concluir App Review, Data Use Checkup e verificações solicitadas; validar Páginas e contas profissionais, não perfis pessoais incompatíveis.
- **Threads:** criar/configurar o app Threads oficial (credenciais separadas no projeto); cadastrar callback e política; solicitar os scopes configurados e passar a revisão aplicável; validar token longo/refresh e recursos de publicação/insights realmente aprovados.
- **Google / YouTube:** configurar OAuth consent screen externo no projeto oficial; domínio, homepage, política e callbacks autorizados; ativar YouTube Data API v3; manter `youtube.readonly` enquanto upload resumível não existir; publicar o app e concluir verificação Google caso o escopo/tela exija; configurar quota e alertas.
- **TikTok:** registrar app e Login Kit; cadastrar redirect HTTPS estático; solicitar aprovação de dados adicionais e Content Posting API; verificar domínio/prefixo de mídia exigido para `PULL_FROM_URL`; concluir auditoria de Direct Post antes de liberar publicação pública.
- **LinkedIn:** criar app ligado à Página oficial e verificar a organização; adicionar Sign In/OIDC; solicitar Community Management Development Tier e, para produção sem restrições, Standard Tier; preparar e enviar screencast e credenciais de revisão; solicitar apenas permissões member/organization efetivamente usadas e manter versão de API suportada.
- **Pinterest:** administrar o app com conta Business verificada; solicitar Trial access; cadastrar callback exato; demonstrar OAuth e ação real em vídeo; solicitar Standard access antes de oferecer a integração amplamente; configurar scopes mínimos e ciclo de refresh contínuo.
- **X:** configurar app Web confidencial, callback e website/políticas; habilitar OAuth 2.0 Authorization Code + PKCE, permissões read/write e scopes mínimos; contratar/confirmar plano e limites compatíveis; testar refresh/revogação e publicação com a API oficial.

## Rotação e incidentes

1. Gerar nova chave de token e torná-la `SOCIAL_TOKEN_ENCRYPTION_KEY`.
2. Manter a chave anterior em `SOCIAL_TOKEN_ENCRYPTION_PREVIOUS_KEYS` durante a janela de migração; nunca registrar os valores.
3. Recriptografar conexões por job controlado ou solicitar reconexão, confirmar métricas/auditoria e então remover a chave antiga.
4. Para client secret de provider: gerar novo secret no portal, atualizar o Secret Manager, reiniciar gradualmente, validar OAuth/refresh e só então revogar o anterior.
5. Em suspeita de vazamento de token de usuário: marcar a conexão como revogada, chamar revogação oficial quando disponível, registrar o evento e exigir reconexão.

## Troubleshooting

- `SOCIAL_CONFIGURATION_REQUIRED`: verifique ID, secret, redirect URI e chave de criptografia no backend.
- `redirect_uri_mismatch`: copie exatamente o callback da variável do provider para o console oficial.
- `SOCIAL_PERMISSION_INSUFFICIENT`: a conta não concedeu scope, o aplicativo ainda não foi aprovado ou o provider não encontrou recurso compatível (por exemplo, uma Conta Google sem canal do YouTube).
- `SOCIAL_AUTHORIZATION_REVOKED`: reconecte a conta; não tente reutilizar token revogado.
- `SOCIAL_PROVIDER_RATE_LIMIT`: aguarde o limite oficial; não aumente retries de escrita.
- TikTok recusa `PULL_FROM_URL`: valide domínio/prefixo HTTPS no portal e a acessibilidade pública temporária da mídia.
- Pinterest não permite criar app: use conta Business verificada e aceite os termos de desenvolvedor.
- YouTube não conecta: confirme Google Auth Platform, cliente OAuth Web, usuário de teste, callback e se a Conta Google autorizada possui um canal do YouTube.

## Referências oficiais

- Meta: https://developers.facebook.com/docs/
- Threads: https://developers.facebook.com/docs/threads/
- TikTok Login Kit: https://developers.tiktok.com/docs/en/login-kit-overview
- TikTok Direct Post: https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post
- YouTube OAuth: https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
- YouTube Data API: https://developers.google.com/youtube/v3/docs/
- LinkedIn OAuth: https://learn.microsoft.com/linkedin/shared/authentication/authentication
- LinkedIn Posts: https://learn.microsoft.com/linkedin/marketing/community-management/shares/posts-api
- Pinterest OAuth v5: https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
- Pinterest access tiers: https://developers.pinterest.com/docs/key-concepts/access-tiers/
- X OAuth 2.0 PKCE: https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code
