# Produção da Clicko — Conexões Sociais

## Estado esperado

O processo deve executar com `NODE_ENV=production`, `SOCIAL_STORAGE_DRIVER=postgres`, uma origem HTTPS canônica em `PUBLIC_APP_URL` e todos os secrets injetados pelo mecanismo secreto do ambiente. O servidor recusa inicialização se a origem for local, o armazenamento social não for PostgreSQL, o TLS do banco estiver desativado, a chave de tokens for inválida ou um provider parcialmente configurado apontar para callback divergente.

O callback canônico é sempre:

```text
${PUBLIC_APP_URL}/api/integrations/oauth/callback
```

Não inclua barra adicional, query string ou fragmento em `PUBLIC_APP_URL`.

## Fluxo de implantação

1. Criar banco PostgreSQL com backup automático, criptografia em repouso e conexão TLS verificável.
2. Injetar as variáveis documentadas em `.env.example` pelo Secret Manager da plataforma.
3. Executar `npm run validate:production`.
4. Executar `npm run migrate:social` com a mesma identidade do banco da aplicação.
5. Executar `npm run build` e iniciar com `npm start`, ou construir o `Dockerfile` multi-stage.
6. Configurar balanceador/reverse proxy para encaminhar HTTPS à porta interna `3000` e preservar `X-Forwarded-Proto`.
7. Usar `/api/health` para liveness e `/api/ready` para readiness. Readiness só responde `200` depois que o repositório social inicializou e o PostgreSQL respondeu.
8. Cadastrar o callback exato nos portais oficiais e validar cada provider com conta de teste pertencente ao owner correspondente.

## Operação e rollback

- A migration `001_social_integrations.sql` é idempotente e transacional.
- Faça snapshot/backup do banco antes de migrations posteriores. Teste restore regularmente no ambiente de staging.
- Deploys devem aguardar readiness antes de receber tráfego e encerrar por `SIGTERM`; o servidor fecha conexões HTTP e o pool PostgreSQL antes de sair.
- Em rollback de código, não reverta automaticamente tabelas ou apague dados. Migrations destrutivas exigem procedimento próprio e backup confirmado.
- O rate limiting global/distribuído deve ser configurado no gateway da hospedagem. Os controles locais de login e de provider continuam como defesa adicional, mas não substituem uma política compartilhada entre réplicas.

## Limitações ainda relevantes

A governança/autenticação geral da aplicação utiliza atualmente o armazenamento local atômico existente. Isso é adequado ao desenvolvimento e a uma única instância com volume persistente, mas precisa de migração para uma sessão/governança transacional compartilhada antes de escalar horizontalmente. Não habilite múltiplas réplicas de autenticação até essa migração ou uma sessão centralizada ser concluída.

O repositório não contém domínio, conta de hospedagem, banco de produção ou Secret Manager configurados. Esses recursos devem ser selecionados na infraestrutura oficial da Clicko; o projeto não inventa domínio nem inicia serviço pago.
